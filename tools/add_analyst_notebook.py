import json

with open("data/category_analysis.json", "r", encoding="utf-8") as f:
    data = json.load(f)

data["analyst_notebook"] = [
    {
        "insight_id": "vol_asymmetry_1",
        "title": "High Sales, Low Satisfaction",
        "observation": "All three products report massive sales volume (10k+ and 7k+) but exhibit extreme trap characteristics, particularly with population gaps up to 0.8.",
        "data_points": [
            "Product B: 0.8 population gap",
            "Product A: 0.629 avg negative ratio across themes",
            "Product C: 11 themes with majority negative"
        ],
        "narration_hint": "Frame the category as fundamentally broken despite its premium status; the top sellers are riding on ecosystem momentum rather than hardware reliability."
    },
    {
        "insight_id": "unique_strength_vacuum",
        "title": "The Compromise Triangle",
        "observation": "None of the products possess a true category-dominating unique strength; buyers are forced to choose which critical flaw they can tolerate.",
        "data_points": [
            "Zero unique strengths across all three products",
            "Product A fails on Charging Experience",
            "Product B fails on Earbud Fit and Pairing",
            "Product C fails on Ear Comfort and Audio Quality"
        ],
        "narration_hint": "Avoid framing any product as 'the winner.' Present the buying decision as a trade-off matrix where the user must sacrifice one core feature (comfort, charging, or fit) to gain another."
    },
    {
        "insight_id": "hardware_regression",
        "title": "Generational Hardware Regression",
        "observation": "Recent review rating averages have plummeted (e.g., 3.4 for B and C) due to physical design choices that regress from previous generations.",
        "data_points": [
            "Product B: Wingtip removal leading to 7.2% positive fit",
            "Product C: Smooth case design causing 30.6% positive case design",
            "Product A: Hat pressure causing 21.1% positive comfort"
        ],
        "narration_hint": "Emphasize that newer isn't always better; point out that design iterations aimed at aesthetics or cost-cutting have actively ruined the core user experience."
    }
]

with open("data/category_analysis.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Added analyst_notebook to data/category_analysis.json")
