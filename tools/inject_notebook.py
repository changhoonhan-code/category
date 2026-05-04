import json

with open("data/category_analysis.json", "r", encoding="utf-8") as f:
    data = json.load(f)

notebook = [
  {
    "insight_id": "insight_001",
    "title": "Pro Designation vs Core Functionality",
    "observation": "Despite carrying the 'Pro' moniker, the entire category fails uniformly on basic fundamentals like charging and comfort, suggesting the premium price tag covers software features (like ANC) rather than hardware reliability.",
    "data_points": [
      "Charging Experience: 8.4% max positive ratio",
      "Ear Comfort: 21.1% max positive ratio"
    ],
    "narration_hint": "Use this early to level the playing field and strip away brand prestige. It sets up the core theme: you aren't paying for perfection, you're paying for specific trade-offs."
  },
  {
    "insight_id": "insight_002",
    "title": "The Expectation Collapse of Product B",
    "observation": "Samsung Galaxy Buds 3 Pro shows a massive 0.8 population gap, dropping from a 4.2 all-time average to 3.4 in recent reviews, alongside high sales volume.",
    "data_points": [
      "population_gap: 0.8",
      "sold_last_month: 10000+"
    ],
    "narration_hint": "Frame this not just as a bad product, but as a mass-market disappointment. This is perfect for illustrating how broad sales figures obscure recent quality drops."
  },
  {
    "insight_id": "insight_003",
    "title": "Fit as the Ultimate Gatekeeper",
    "observation": "Beats Powerbeats Pro 2 has a very strong fit rating (69.2%) but terrible audio quality (16.7%). Apple AirPods Pro 3 has moderate fit (39.6%) but the best ANC (63.6%).",
    "data_points": [
      "Earbud Fit: product_c 69.2% vs product_a 39.6%",
      "Audio Quality: product_c 16.7%"
    ],
    "narration_hint": "Use this to explain why there is no 'best' earbud. The one that fits the best sounds the worst, and the one that cancels noise the best struggles to stay in the ear."
  }
]

data["analyst_notebook"] = notebook

with open("data/category_analysis.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Injected analyst_notebook successfully.")
