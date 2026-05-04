import json

with open("data/category_blueprint.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("--- Population Gaps ---")
for p in data["products"]:
    print(f"{p['product_id']} ({p['product_name']}): Gap {p['population_gap']}, Sold {p['sold_last_month']}")

print("\n--- Common Themes Contradictions ---")
for t in data["common_themes"]:
    print(f"Theme: {t['theme_name']}")
    for rank in t["rankings"]:
        print(f"  {rank['product_id']}: Gap {(rank['positive_ratio']*100):.1f}% pos, Mentions {rank['mention_count']}")
    
    for c in t["contradiction_pairs"]:
        print(f"  Type: {c['type']}, Products: {c.get('product_ids', c.get('product_id'))}")
        print(f"    Pos quote helpful: {c['positive_quote']['helpful_count']}, Neg quote helpful: {c['negative_quote']['helpful_count']}")
        
print("\n--- Unique Strengths ---")
for p in data["products"]:
    if "unique_strengths" in p:
        for u in p["unique_strengths"]:
            print(f"  {p['product_id']}: {u['theme_name']}, ratio: {u['positive_ratio']}, mentions: {u['mention_count']}")
