import argparse
import asyncio
import io
import json
import os
import time
from typing import List, Literal, Optional

import pandas as pd
from google import genai
from google.genai import types
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
import re

from config import MODELS, MAX_RETRIES

# ── Pydantic Models ────────────────────────────────────────────────────────────
class VideoFeature(BaseModel):
    video_filename: str = Field(..., description="Name of the video file")
    review_id: str = Field(..., description="The ID of the review this video belongs to")
    is_helpful_for_guide: bool = Field(...)
    video_quality: Literal["Clear", "Shaky", "Blurry", "Too Dark"] = Field(description="Assess the visual quality of the recording")
    shows_action: bool = Field(description="True if the video actively demonstrates an action, False if static product shot")
    core_aspect: Optional[str] = Field(None)
    sentiment: Optional[Literal["Positive", "Negative", "Neutral", "Mixed"]] = Field(None)
    visual_evidence: Optional[str] = Field(None)
    user_profile: Optional[str] = Field(None)
    broll_start_time: Optional[str] = Field(None)
    broll_end_time: Optional[str] = Field(None)
    broll_description: Optional[str] = Field(None)
    search_keywords: List[str] = Field(default_factory=list)
    related_themes: List[str] = Field(default_factory=list, description="Theme names this media relates to from the product theme list (empty array if none match)")
    shot_type: Optional[Literal["Close-up", "Medium shot", "Wide shot", "First-person POV", "Screen recording", "Other"]] = Field(None)
    is_funny: bool = Field(False)
    matching_block_ids: List[str] = Field(default_factory=list, description="Block IDs from script narration this video matches (narration context)")

class VideoAnalysisResponse(BaseModel):
    results: List[VideoFeature]

class ImageFeature(BaseModel):
    image_filename: str = Field(..., description="Name of the image file")
    review_id: str = Field(..., description="The ID of the review this image belongs to")
    is_helpful_for_guide: bool = Field(...)
    image_quality: Literal["Clear", "Blurry", "Too Dark", "Obscured"] = Field(description="Assess the visual quality of the image")
    image_type: Literal["product_in_use", "defect_closeup", "packaging", "screenshot_ui", "accessory", "other"] = Field(...)
    core_aspect: Optional[str] = Field(None)
    sentiment: Optional[Literal["Positive", "Negative", "Neutral", "Mixed"]] = Field(None)
    visual_evidence: Optional[str] = Field(None)
    search_keywords: List[str] = Field(default_factory=list)
    related_themes: List[str] = Field(default_factory=list, description="Theme names this media relates to from the product theme list (empty array if none match)")
    text_in_image: Optional[str] = Field(None)
    matching_block_ids: List[str] = Field(default_factory=list, description="Block IDs from script narration this image matches (narration context)")

class ImageAnalysisResponse(BaseModel):
    results: List[ImageFeature]

# ── Shared Helper ──────────────────────────────────────────────────────────────
def _build_claims_text(review_id: str, context_rows: pd.DataFrame) -> str:
    if context_rows.empty:
        return "NO TEXT CLAIMS FOUND FOR THIS REVIEW. Analyze purely on visual merits."
    lines = [f"REVIEWER'S EXTRACTED CLAIMS (from text for Review {review_id}):"]
    for _, row in context_rows.iterrows():
        lines.append(
            f'- Claim: [Aspect: {row.get("core_aspect", "")}] '
            f'[Sentiment: {row.get("sentiment", "")}] '
            f'-> Quote: "{row.get("evidence_quote", "")}"'
        )
    return "\n".join(lines)

# ── Video Analysis ─────────────────────────────────────────────────────────────
async def analyze_video(client: genai.Client, video_path: str, review_id: str, context_rows: pd.DataFrame, product_name: str, semaphore: asyncio.Semaphore, config: dict, theme_names: List[str] = None, narration_context: List[dict] = None) -> Optional[List[VideoFeature]]:
    filename = os.path.basename(video_path)
    model_id = config.get("model_id", "gemini-3-flash-preview")
    temperature = config.get("temperature", 0.1)
    max_retries = config.get("max_retries", 3)
    polling_timeout = config.get("polling_timeout_sec", 300)

    claims_text = _build_claims_text(review_id, context_rows)

    async with semaphore:
        print(f"\n🎬 [Analysis Start] {filename} (Review ID: {review_id})")

        print("   ↳ Uploading file...")
        try:
            myfile = await asyncio.to_thread(client.files.upload, file=video_path)
            print(f"   ↳ Upload complete (URI: {myfile.uri})")
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            return None

        print("   ↳ Waiting for video indexing", end="", flush=True)
        start = time.time()
        try:
            while True:
                if time.time() - start > polling_timeout:
                    print("\n   ❌ Timeout (exceeded 5 minutes)")
                    return None
                check = await asyncio.to_thread(client.files.get, name=myfile.name)
                if check.state.name == "ACTIVE":
                    print("\n   ↳ Ready for analysis!")
                    break
                elif check.state.name == "FAILED":
                    print("\n   ❌ Video processing failed")
                    return None
                else:
                    print(".", end="", flush=True)
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"\n   ❌ Status check error: {e}")
            return None

        # 테마 목록 프롬프트 블록 (있으면 주입)
        themes_block = ""
        if theme_names:
            themes_list = ", ".join(f'"{t}"' for t in theme_names)
            themes_block = f"""
# KNOWN PRODUCT THEMES (from review analysis)
These are the confirmed themes for this product: [{themes_list}]
- `related_themes`: From the list above, select ALL themes that this video's content is relevant to.
- If the video does not relate to any theme, set `related_themes` to an empty array [].
- Match by SEMANTIC RELEVANCE, not just keyword overlap.
"""

        # 나레이션 컨텍스트 프롬프트 블록 (있으면 주입)
        narration_block = ""
        if narration_context:
            lines = "\n".join(f'  - {b["block_id"]}: "{b["narration"]}"' for b in narration_context)
            narration_block = f"""
# SCRIPT NARRATION CONTEXT
These are the narration lines from the video script. Each line is block_id: "narration text".
{lines}

- `matching_block_ids`: From the block IDs above, list ALL blocks whose narration this video could visually support as B-roll.
  - Base your selection on whether this video's visual content directly illustrates or reinforces the narration.
  - If no block matches, set to [].
"""

        prompt = f"""You are an expert product reviewer, B-roll finder, and Visual Evidence Validator AI.
This video was attached to an Amazon review by a customer for the product: [{product_name}].

Your task is to act as a VALIDATOR: Does this video visually or acoustically PROVE or SHOW what the reviewer complained/praised?

{claims_text}
{themes_block}{narration_block}
# B-ROLL QUALITY CONTROL (STRICT CHECKLIST)
1. Match the video contents to the "REVIEWER'S EXTRACTED CLAIMS". Set `core_aspect` exactly as written.
2. Quality Evaluate (`video_quality`): If the recording is "Shaky", "Blurry", or "Too Dark", you MUST set `is_helpful_for_guide` to False.
3. Action Evaluate (`shows_action`): Does the video actively demonstrate an action (e.g. typing, breaking, assembling) or is it a static shot? Set True/False.
4. Visual Evidence (`visual_evidence`): Describe strictly what is seen or heard.
5. Timestamping (`broll_start_time` / `broll_end_time`): Find the single most visually captivating 2 to 5-second window. Skip shaky camera pick-ups at the beginning.
6. Humor Check (`is_funny`): Only True if it shows a funny accident, obvious sarcasm, or humorous failure.
7. Semantic Narration Match (`matching_block_ids`): ONLY select a block ID if the video PERFECTLY illustrates the words being spoken. Do not guess.

# FIELD DEFINITIONS
- video_filename: Exactly "{filename}"
- review_id: Exactly "{review_id}"
- search_keywords: 3-5 nouns based on literal visual elements.
- related_themes: Match by deep semantic relevance.
"""
        features = None
        try:
            for attempt in range(1, max_retries + 1):
                try:
                    print(f"   ↳ Extracting validator (attempt {attempt})...")
                    response = await client.aio.models.generate_content(
                        model=model_id,
                        contents=[myfile, prompt],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=VideoAnalysisResponse,
                            temperature=temperature,
                        ),
                    )
                    parsed_obj = getattr(response, "parsed", None)
                    if parsed_obj and hasattr(parsed_obj, "results"):
                        features = parsed_obj.results
                    else:
                        raw = getattr(response, "text", "")
                        if raw.startswith("```json"):
                            raw = raw.split("```json", 1)[1]
                        if raw.endswith("```"):
                            raw = raw.rsplit("```", 1)[0]
                        parsed = json.loads(raw.strip())
                        features = [VideoFeature(**x) for x in parsed.get("results", [])]
                    print(f"   ↳ Extraction success ({len(features)} features)")
                    break
                except Exception as e:
                    print(f"   ⚠️ API call failed (attempt {attempt}): {e}")
                    wait = 2 ** attempt if ("429" in str(e) or "503" in str(e)) else 2 * attempt
                    await asyncio.sleep(wait)
        finally:
            try:
                await asyncio.to_thread(client.files.delete, name=myfile.name)
                print("   ↳ Server file cleanup complete")
            except Exception as e:
                print(f"   ⚠️ File deletion error: {e}")

        return features

# ── Image Analysis ─────────────────────────────────────────────────────────────
def _resize_image_sync(image_path: str, max_size: int = 1024) -> bytes:
    with Image.open(image_path) as img:
        # EXIF 회전 정보 보정
        img = ImageOps.exif_transpose(img)
        
        img.thumbnail((max_size, max_size))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

async def analyze_image(client: genai.Client, image_path: str, review_id: str, context_rows: pd.DataFrame, product_name: str, semaphore: asyncio.Semaphore, config: dict, theme_names: List[str] = None, narration_context: List[dict] = None) -> Optional[List[ImageFeature]]:
    filename = os.path.basename(image_path)
    model_id = config.get("model_id", "gemini-3.1-flash-lite-preview")
    temperature = config.get("temperature", 0.1)
    max_retries = config.get("max_retries", 3)

    claims_text = _build_claims_text(review_id, context_rows)

    async with semaphore:
        print(f"\n📸 [Analysis Start] {filename} (Review: {review_id})")

        try:
            image_data = await asyncio.to_thread(_resize_image_sync, image_path)
        except Exception as e:
            print(f"   ❌ Image conversion error: {e}")
            return None

        # 테마 목록 프롬프트 블록 (있으면 주입)
        themes_block = ""
        if theme_names:
            themes_list = ", ".join(f'"{t}"' for t in theme_names)
            themes_block = f"""
# KNOWN PRODUCT THEMES (from review analysis)
These are the confirmed themes for this product: [{themes_list}]
- `related_themes`: From the list above, select ALL themes that this image's content is relevant to.
- If the image does not relate to any theme, set `related_themes` to an empty array [].
- Match by SEMANTIC RELEVANCE, not just keyword overlap.
"""

        # 나레이션 컨텍스트 프롬프트 블록 (있으면 주입)
        narration_block = ""
        if narration_context:
            lines = "\n".join(f'  - {b["block_id"]}: "{b["narration"]}"' for b in narration_context)
            narration_block = f"""
# SCRIPT NARRATION CONTEXT
These are the narration lines from the video script. Each line is block_id: "narration text".
{lines}

- `matching_block_ids`: From the block IDs above, list ALL blocks whose narration this image could visually support as B-roll.
  - Base your selection on whether this image's visual content directly illustrates or reinforces the narration.
  - If no block matches, set to [].
"""

        prompt = f"""You are an expert product reviewer and Visual Evidence Validation AI.
This image was attached to an Amazon review by a customer (Review ID: {review_id}) for the product: [{product_name}].

Your task is to act as a VALIDATOR: Does this image visually PROVE or SHOW what the reviewer complained/praised?

{claims_text}
{themes_block}{narration_block}
# VISUAL QUALITY CONTROL (STRICT CHECKLIST)
1. Match the image contents to the "REVIEWER'S EXTRACTED CLAIMS". Set `core_aspect` exactly as written.
2. Quality Evaluate (`image_quality`): If the recording is "Blurry", "Too Dark", or "Obscured", you MUST set `is_helpful_for_guide` to False.
3. Generic Filter: If the image is just a cardboard box, selfie, or irrelevant, set `is_helpful_for_guide` to False.
4. Visual Evidence (`visual_evidence`): Describe strictly what is seen.
5. Humor Check (`is_funny`): Only True if it shows a funny accident, obvious sarcasm, or humorous failure.
6. Semantic Narration Match (`matching_block_ids`): ONLY select a block ID if the image PERFECTLY illustrates the words being spoken. Do not guess.

# FIELD DEFINITIONS
- image_filename: Exactly "{filename}"
- review_id: Exactly "{review_id}"
- search_keywords: 3-5 nouns based on literal visual elements.
- related_themes: Match by deep semantic relevance.
"""
        features = None
        for attempt in range(1, max_retries + 1):
            try:
                response = await client.aio.models.generate_content(
                    model=model_id,
                    contents=[
                        prompt,
                        types.Part.from_bytes(data=image_data, mime_type="image/jpeg"),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ImageAnalysisResponse,
                        temperature=temperature,
                    ),
                )
                parsed_obj = getattr(response, "parsed", None)
                if parsed_obj and hasattr(parsed_obj, "results"):
                    features = parsed_obj.results
                else:
                    raw = getattr(response, "text", "")
                    if raw.startswith("```json"):
                        raw = raw.split("```json", 1)[1]
                    if raw.endswith("```"):
                        raw = raw.rsplit("```", 1)[0]
                    parsed = json.loads(raw.strip())
                    features = [ImageFeature(**x) for x in parsed.get("results", [])]
                print(f"   ↳ Complete: {len(features)} features mapped successfully")
                break
            except Exception as e:
                print(f"   ⚠️ API retry (attempt {attempt}): {e}")
                wait = 2 ** attempt if ("429" in str(e) or "503" in str(e)) else 2 * attempt
                await asyncio.sleep(wait)

        return features

# ── Main Indexer Logic ────────────────────────────────────────────────────────
class MediaIndexer:
    def __init__(self, input_dir: str, output_dir: str, themes_path: str = None, script_path: str = None):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.movies_dir = os.path.join(input_dir, "movies")
        self.images_dir = os.path.join(input_dir, "photos")
        self.movies_meta_dir = os.path.join(output_dir, "movies_meta")
        self.photos_meta_dir = os.path.join(output_dir, "photos_meta")
        self.csv_path = os.path.join(output_dir, "buying_guide_extracted.csv")
        self.themes_path = themes_path
        self.script_path = script_path
        self.theme_names: List[str] = []  # 테마명 리스트 (summary.json에서 추출)
        self.narration_blocks: List[dict] = []  # block_id + narration 리스트 (script JSON에서 추출)
        self.config = {
            "model_id": MODELS["analysis"],
            "temperature": 0.1,
            "max_retries": MAX_RETRIES,
            "max_concurrent_videos": 3,
            "max_concurrent_images": 5,
            "polling_timeout_sec": 300
        }
        self.client = genai.Client()

    def log(self, msg: str):
        print(f"[MediaIndexer] {msg}")

    def _load_product_name(self) -> Optional[str]:
        path = os.path.join(self.input_dir, "product.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)["product_title"]
        except Exception as e:
            self.log(f"ERROR: Cannot read product.json — {e}")
            return None

    def _load_guide_df(self) -> pd.DataFrame:
        if os.path.exists(self.csv_path):
            try:
                df = pd.read_csv(self.csv_path)
                self.log(f"Loaded buying guide CSV ({len(df)} rows) for context injection.")
                return df
            except Exception as e:
                self.log(f"WARNING: Could not load guide CSV — {e}")
        else:
            self.log(f"WARNING: {self.csv_path} not found. Running without text context.")
        return pd.DataFrame()

    async def _analyze_one_video(self, filename: str, guide_df: pd.DataFrame, product_name: str, semaphore: asyncio.Semaphore) -> Optional[List[VideoFeature]]:
        video_path = os.path.join(self.movies_dir, filename)
        
        # 파일명에서 Review ID 추출 (예: R12345_xxx.mp4 -> R12345)
        match = re.match(r'^([A-Z0-9]+)', filename)
        review_id = match.group(1) if match else (filename.split("_")[0] if "_" in filename else os.path.splitext(filename)[0])
        
        context_rows = guide_df[guide_df["review_id"] == review_id] if not guide_df.empty and "review_id" in guide_df.columns else pd.DataFrame()
        
        features = await analyze_video(self.client, video_path, review_id, context_rows, product_name, semaphore, self.config, self.theme_names, self.narration_blocks)

        if features:
            os.makedirs(self.movies_meta_dir, exist_ok=True)
            base = os.path.splitext(filename)[0]
            sidecar = os.path.join(self.movies_meta_dir, f"{base}_meta.json")
            with open(sidecar, "w", encoding="utf-8") as f:
                json.dump([x.model_dump() for x in features], f, ensure_ascii=False, indent=2)
        return features

    async def _analyze_one_image(self, filename: str, guide_df: pd.DataFrame, product_name: str, semaphore: asyncio.Semaphore) -> Optional[List[ImageFeature]]:
        image_path = os.path.join(self.images_dir, filename)
        
        # 파일명에서 Review ID 추출
        match = re.match(r'^([A-Z0-9]+)', filename)
        review_id = match.group(1) if match else (filename.split("_")[0] if "_" in filename else os.path.splitext(filename)[0])
        
        context_rows = guide_df[guide_df["review_id"] == review_id] if not guide_df.empty and "review_id" in guide_df.columns else pd.DataFrame()
        
        features = await analyze_image(self.client, image_path, review_id, context_rows, product_name, semaphore, self.config, self.theme_names, self.narration_blocks)

        if features:
            os.makedirs(self.photos_meta_dir, exist_ok=True)
            base = os.path.splitext(filename)[0]
            sidecar = os.path.join(self.photos_meta_dir, f"{base}_meta.json")
            with open(sidecar, "w", encoding="utf-8") as f:
                json.dump([x.model_dump() for x in features], f, ensure_ascii=False, indent=2)
        return features

    async def _run_video_analysis(self, product_name: str, guide_df: pd.DataFrame) -> bool:
        if not os.path.exists(self.movies_dir):
            self.log(f"Video dir not found: {self.movies_dir} — skipping video analysis.")
            return False

        video_files = [f for f in os.listdir(self.movies_dir) if f.lower().endswith((".mp4", ".mov"))]
        if not video_files:
            self.log(f"No video files found in {self.movies_dir} — skipping.")
            return False

        self.log(f"Analyzing {len(video_files)} videos (max {self.config['max_concurrent_videos']} concurrent)...")
        semaphore = asyncio.Semaphore(int(self.config["max_concurrent_videos"]))
        tasks = [self._analyze_one_video(f, guide_df, product_name, semaphore) for f in video_files]
        results = await asyncio.gather(*tasks)

        all_features = [f for r in results if r for f in r]
        if all_features:
            os.makedirs(self.movies_meta_dir, exist_ok=True)
            agg_path = os.path.join(self.movies_meta_dir, "movie_metadata_extracted.json")
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump([x.model_dump() for x in all_features], f, ensure_ascii=False, indent=2)
            self.log(f"Video analysis done — {len(all_features)} B-roll assets → {agg_path}")
        return bool(all_features)

    async def _run_image_analysis(self, product_name: str, guide_df: pd.DataFrame) -> bool:
        if not os.path.exists(self.images_dir):
            self.log(f"Image dir not found: {self.images_dir} — skipping image analysis.")
            return False

        image_files = [f for f in os.listdir(self.images_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        if not image_files:
            self.log(f"No image files found in {self.images_dir} — skipping.")
            return False

        self.log(f"Analyzing {len(image_files)} images (max {self.config['max_concurrent_images']} concurrent)...")
        semaphore = asyncio.Semaphore(int(self.config["max_concurrent_images"]))
        tasks = [self._analyze_one_image(f, guide_df, product_name, semaphore) for f in image_files]
        results = await asyncio.gather(*tasks)

        all_features = [f for r in results if r for f in r]
        if all_features:
            os.makedirs(self.photos_meta_dir, exist_ok=True)
            agg_path = os.path.join(self.photos_meta_dir, "photos_metadata_extracted.json")
            with open(agg_path, "w", encoding="utf-8") as f:
                json.dump([x.model_dump() for x in all_features], f, ensure_ascii=False, indent=2)
            self.log(f"Image analysis done — {len(all_features)} visual assets → {agg_path}")
        return bool(all_features)

    def _load_narration_context(self) -> List[dict]:
        """스크립트 JSON에서 block_id + narration 리스트를 추출."""
        if not self.script_path or not os.path.exists(self.script_path):
            if self.script_path:
                self.log(f"WARNING: Script file not found: {self.script_path}. Proceeding without narration context injection.")
            return []
        try:
            with open(self.script_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            blocks = []
            for scene in data.get("scenes", []):
                for block in scene.get("blocks", []):
                    bid = block.get("block_id", "")
                    narration = block.get("narration", "")
                    if bid and narration:
                        blocks.append({"block_id": bid, "narration": narration})
            self.log(f"Narration context loaded: {len(blocks)} blocks")
            return blocks
        except Exception as e:
            self.log(f"WARNING: Script file parsing failed: {e}")
            return []

    def _load_theme_names(self) -> List[str]:
        """테마명 리스트를 summary.json에서 추출."""
        if not self.themes_path or not os.path.exists(self.themes_path):
            if self.themes_path:
                self.log(f"WARNING: Theme file not found: {self.themes_path}. Proceeding without theme tagging.")
            return []
        try:
            with open(self.themes_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            themes = data.get("themes", [])
            names = [t.get("theme_name", "") for t in themes if t.get("theme_name")]
            self.log(f"Themes loaded: {len(names)} total - {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")
            return names
        except Exception as e:
            self.log(f"WARNING: Theme file parsing failed: {e}")
            return []

    async def run(self) -> bool:
        product_name = self._load_product_name()
        if not product_name:
            return False

        guide_df = self._load_guide_df()
        self.theme_names = self._load_theme_names()
        self.narration_blocks = self._load_narration_context()

        self.log("Launching video & image analysis in parallel...")
        video_ok, image_ok = await asyncio.gather(
            self._run_video_analysis(product_name, guide_df),
            self._run_image_analysis(product_name, guide_df),
        )

        if not video_ok:
            self.log("WARNING: Video analysis returned no results (may be OK if no videos).")
        if not image_ok:
            self.log("WARNING: Image analysis returned no results (may be OK if no images).")

        return True

async def main():
    parser = argparse.ArgumentParser(description="Media Indexer Tool: Analyzes videos and images concurrently.")
    parser.add_argument("--input-dir", type=str, required=True, help="Path to input directory (containing product.json, movies/, photos/)")
    parser.add_argument("--output-dir", type=str, required=True, help="Path to output directory (data/)")
    parser.add_argument("--themes", type=str, default=None, help="Path to summary.json. Reads theme list for related_themes tagging (optional)")
    parser.add_argument("--script", type=str, default=None, help="Path to script JSON (e.g., final_script_with_narration.json). Injects narration text into Vision prompts for matching_block_ids tagging (optional)")
    args = parser.parse_args()

    indexer = MediaIndexer(input_dir=args.input_dir, output_dir=args.output_dir, themes_path=args.themes, script_path=args.script)
    success = await indexer.run()
    if not success:
        print("[MediaIndexer] Finished with some errors or missing data.")

if __name__ == "__main__":
    asyncio.run(main())
