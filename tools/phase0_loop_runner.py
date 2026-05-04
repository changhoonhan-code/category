import os
import subprocess
import sys
from pathlib import Path

def run_command(command):
    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"Error executing command: {' '.join(command)}")
        # We don't exit here to allow other products to be processed, 
        # but in a real pipeline we might want to.
    return result.returncode

def main():
    proj_root = Path(__file__).parent.parent
    products_dir = proj_root / "products"
    data_dir = proj_root / "data" / "products"
    tools_dir = proj_root / "tools"

    if not products_dir.exists():
        print(f"Error: {products_dir} does not exist.")
        sys.exit(1)

    # Get all product directories
    product_dirs = [d for d in products_dir.iterdir() if d.is_dir()]
    print(f"Found {len(product_dirs)} products: {[d.name for d in product_dirs]}")

    for p_dir in product_dirs:
        product_id = p_dir.name
        output_path = data_dir / product_id
        output_path.mkdir(parents=True, exist_ok=True)

        summary_json = output_path / "summary.json"
        
        # Skip if already processed (optional, but let's re-run if asked)
        # if summary_json.exists():
        #     print(f"Skipping {product_id}, already processed.")
        #     continue

        print(f"\n=== Processing Product: {product_id} ===")

        # Step 1: ABSA
        absa_cmd = [
            sys.executable, str(tools_dir / "absa.py"),
            "--input-dir", str(p_dir),
            "--output-dir", str(output_path)
        ]
        if run_command(absa_cmd) != 0:
            continue

        # Step 2: Data Bridge
        bridge_cmd = [
            sys.executable, str(tools_dir / "data_bridge.py"),
            "--input-dir", str(p_dir),
            "--output-dir", str(output_path)
        ]
        if run_command(bridge_cmd) != 0:
            print(f"Error: Data Bridge failed for {product_id}")
            continue


    print("\n=== Phase 0 Loop Complete ===")

if __name__ == "__main__":
    main()
