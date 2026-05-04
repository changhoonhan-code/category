import json

draft_path = "d:/GEMINI/data/draft_script.json"
writer_path = "d:/GEMINI/data/category_writer.json"
output_path = "d:/GEMINI/data/curate_patch.json"

with open(draft_path, "r", encoding="utf-8") as f:
    draft = json.load(f)

# Quotes from category_writer.json
# Active Noise Cancellation:
q_anc_a_pos = {
    "text": "apple made huge improvements with the noise cancelation on these earbuds. I go to a large gym with a lot of powerlifters, and I can’t even hear the clanking of barbells when I’m listening to music.",
    "review_id": "R3DUQ7DK7KVDZJ",
    "product_id": "product_a",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "anchor",
    "highlight_phrase": "can’t even hear the clanking"
}
q_anc_a_neg = {
    "text": "On airline flights at altitude this version of the AirPods generates piercing feedback that is loud enough to cause permanent hearing damage.",
    "review_id": "R1OTZK2NBJD5K",
    "product_id": "product_a",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "generates piercing feedback"
}
q_anc_c_pos = {
    "text": "It does an excellent job of blocking out background noise without making the audio feel compressed or artificial.",
    "review_id": "R3FGQWYX2CXDQL",
    "product_id": "product_c",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "without making the audio feel compressed"
}
q_anc_c_neg = {
    "text": "Noise cancelling is very uncomfortable as they do not fit as snugly on my ears as the old Powerbeats generation despite all their ear tips and Apple claiming I have a “good seal” It simply isn’t maintained causing audio leakage and a disorienting feeling.",
    "review_id": "RCZ75P2NLW9AW",
    "product_id": "product_c",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "anchor",
    "highlight_phrase": "causing audio leakage"
}

# Battery Life:
q_bat_a_pos = {
    "text": "I’m able to get literal hours of use without the case falling below 50%. I was on the phone last night for almost 2 hours, then watched some YouTube another 1.5 hrs. AirPods were barely at 57%.",
    "review_id": "R2D7MJKEVE2J6J",
    "product_id": "product_a",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "without the case falling below 50%"
}
q_bat_a_neg = {
    "text": "They die in the sauna most days within 5 mins, no matter the charge.",
    "review_id": "RCYFY6LO2SJRA",
    "product_id": "product_a",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "hook",
    "highlight_phrase": "die in the sauna"
}
q_bat_c_pos = {
    "text": "I charge my case 1 time a week and my head phones will last me until Wednesday of the next week over and I actually use my headphones for almost all 8hrs of my shift.",
    "review_id": "R1VFB6UJZIHLV9",
    "product_id": "product_c",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "supplementary",
    "highlight_phrase": "last me until Wednesday"
}
q_bat_c_neg = {
    "text": "The buds would connect to my phone even when the case was closed. This would kill the battery life.",
    "review_id": "R3BCS0A4WJILW",
    "product_id": "product_c",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "supplementary",
    "highlight_phrase": "even when the case was closed"
}
q_bat_b_neg = {
    "text": "You get at least 2 1/2 hours with the buds and the charging case sucks too. I only get 3 complete charges when the case and the buds are fully charged",
    "review_id": "R2BJG4AU4S9VOV",
    "product_id": "product_b",
    "star_rating": 2,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "get at least 2 1/2 hours"
}

# Charging Case Design:
q_case_c_pos = {
    "text": "Case is much smaller than the previous generation and can almost just be thrown in your pocket.",
    "review_id": "RP6A6O6R76B83",
    "product_id": "product_c",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "almost just be thrown in your pocket"
}
q_case_c_neg = {
    "text": "can you make a case that you can open with one hand! What is up with these super smooth cases?",
    "review_id": "RZ17P87DU8FM3",
    "product_id": "product_c",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "hook",
    "highlight_phrase": "open with one hand"
}
q_case_b_pos = {
    "text": "I had recently had the beats studio buds plus. And the noise canceling and sound quality and case is worse everything is better on these the case of these galaxy earbuds is fantastic it doenst feel cheap has a nice snap shut.",
    "review_id": "R1HZT2ZRGGXWPT",
    "product_id": "product_b",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "has a nice snap shut"
}
q_case_b_neg = {
    "text": "It randomly stops charging the earbuds and triggers a message on the phone saying to “clean dust or moisture,” even when the device is clean and dry.",
    "review_id": "RFBX6AVEHLAKR",
    "product_id": "product_b",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "supplementary",
    "highlight_phrase": "randomly stops charging"
}
q_case_a_pos = {
    "text": "They've also improved the case so if you happen to drop it on the floor, your airpods don't explode out of the case like a damn grenade and fly across the room.",
    "review_id": "R2JO7SILWKCMDU",
    "product_id": "product_a",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "don't explode out of the case"
}
q_case_a_neg = {
    "text": "the hinge on them was bad causing the AirPods to always think they were open in turn sending frequent notifications to my phone and draining my battery.",
    "review_id": "RQJO4PGZGKEDV",
    "product_id": "product_a",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "anchor",
    "highlight_phrase": "think they were open"
}

# Ear Comfort:
q_ear_a_pos = {
    "text": "I also really appreciate that they include smaller-sized ear tips. That made a noticeable difference in comfort and fit for longer listening sessions",
    "review_id": "R3I8D3LUKUWWE7",
    "product_id": "product_a",
    "star_rating": 4,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "include smaller-sized ear tips"
}
q_ear_a_neg = {
    "text": "After some time, they start to hurt my ears—especially when wearing a beanie in cold weather.",
    "review_id": "R1BFDEG7QXHOJM",
    "product_id": "product_a",
    "star_rating": 1,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "supplementary",
    "highlight_phrase": "wearing a beanie in cold weather"
}
q_ear_c_pos = {
    "text": "They do fit a little differently in my ears, but in a good way— they’re much more comfortable to my ears compared to the OGs.",
    "review_id": "RRDDSPQQ4C0ZE",
    "product_id": "product_c",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "much more comfortable"
}
q_ear_c_neg = {
    "text": "any sort of smiling or facial use - will drive these to hurt in your ears",
    "review_id": "R1TTI0SENLREW6",
    "product_id": "product_c",
    "star_rating": 2,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "hook",
    "highlight_phrase": "drive these to hurt"
}
q_ear_b_pos = {
    "text": "I also have smaller ears that are sensitive to long term ear buds use, at least the use of prior ear buds. These stay in and are comfortable for hours at a time.",
    "review_id": "R2QDK5XP7CRQ8P",
    "product_id": "product_b",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "contrast",
    "highlight_phrase": "comfortable for hours"
}
q_ear_b_neg = {
    "text": "It took about one week of typical usage before I started experiencing first itching and then burning. ... my ears were \"leaking\"",
    "review_id": "R2YZ1PH85GRP8A",
    "product_id": "product_b",
    "star_rating": 2,
    "sentiment": "Negative",
    "is_humorous": False,
    "selection_reason": "supplementary",
    "highlight_phrase": "itching and then burning"
}

# Unique Strengths (Landmine for A)
q_landmine_a = {
    "text": "The results were nearly identical to the hospital’s findings. What truly amazed us was how the iPhone calibrated the sound based on her hearing profile.",
    "review_id": "RPID1E6SZBQMA",
    "product_id": "product_a",
    "star_rating": 5,
    "sentiment": "Positive",
    "is_humorous": False,
    "selection_reason": "anchor",
    "highlight_phrase": "identical to the hospital’s findings"
}


# Let's map scenes
scenes_out = []

for scene in draft['scenes']:
    scene_out = {
        "scene_id": scene['scene_id'],
        "blocks": []
    }
    
    if scene['scene_id'] == 'intro_credibility':
        scene_out['headline'] = "Introduction"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'intro_lineup':
                b_out['title'] = "Over 14,000 Reviews"
            elif block['block_id'] == 'intro_gap':
                b_out['title'] = "The Reality Gap"
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'metric_active':
        scene_out['headline'] = "Active Noise Cancellation"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'active_showdown':
                b_out['title'] = "Apple Leads ANC"
                b_out['evidence_quotes'] = [q_anc_a_pos]
            elif block['block_id'] == 'active_fallout':
                b_out['title'] = "The Altitude Flaw"
                b_out['evidence_quotes'] = [q_anc_a_neg]
            elif block['block_id'] == 'active_context':
                b_out['title'] = "Beats: A Broken Seal"
                b_out['evidence_quotes'] = [q_anc_c_neg, q_anc_c_pos]
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'metric_battery':
        scene_out['headline'] = "Battery Life"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'battery_showdown':
                b_out['title'] = "Samsung Struggles"
                b_out['evidence_quotes'] = [q_bat_b_neg]
            elif block['block_id'] == 'battery_fallout':
                b_out['title'] = "Unexpected Failures"
                b_out['evidence_quotes'] = [q_bat_c_neg, q_bat_c_pos, q_bat_a_pos, q_bat_a_neg]
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'metric_charging':
        scene_out['headline'] = "Charging Case Design"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'charging_diagnosis':
                b_out['title'] = "A Universal Flaw"
                b_out['evidence_quotes'] = [q_case_c_pos, q_case_b_pos, q_case_a_pos]
            elif block['block_id'] == 'charging_spectrum':
                b_out['title'] = "Unseen Problems"
                b_out['evidence_quotes'] = [q_case_b_neg, q_case_a_neg, q_case_c_neg]
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'metric_ear':
        scene_out['headline'] = "Ear Comfort"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'ear_diagnosis':
                b_out['title'] = "Material Flaws"
                b_out['evidence_quotes'] = [q_ear_b_neg, q_ear_b_pos]
            elif block['block_id'] == 'ear_spectrum':
                b_out['title'] = "Pain on Movement"
                b_out['evidence_quotes'] = [q_ear_c_neg, q_ear_c_pos, q_ear_a_neg, q_ear_a_pos]
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'landmine':
        scene_out['headline'] = "The Landmine"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'landmine_product_a':
                b_out['title'] = "Apple's Medical Edge"
                b_out['evidence_quotes'] = [q_landmine_a]
            elif block['block_id'] == 'landmine_product_b':
                b_out['title'] = "The Feature Gap"
            elif block['block_id'] == 'landmine_product_c':
                b_out['title'] = "The Reality Drop"
            scene_out['blocks'].append(b_out)

    elif scene['scene_id'] == 'final_recommendation':
        scene_out['headline'] = "Final Recommendation"
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "evidence_quotes": []
            }
            if block['block_id'] == 'recommendation_category_judgment':
                b_out['title'] = "The Clear Choice"
            elif block['block_id'] == 'recommendation_use_case_picks':
                b_out['title'] = "Conditional Tradeoffs"
            elif block['block_id'] == 'recommendation_notebook':
                b_out['title'] = "The Hardest Sell"
            elif block['block_id'] == 'recommendation_outro':
                b_out['title'] = "" # Excluded title
            scene_out['blocks'].append(b_out)

    else:
        # hook
        for block in scene['blocks']:
            b_out = {
                "block_id": block['block_id'],
                "title": "",
                "evidence_quotes": []
            }
            scene_out['blocks'].append(b_out)

    scenes_out.append(scene_out)

out_json = {
    "critique_log": [
        {
            "fix_type": "[Coverage Warning]",
            "reason": "Some blocks do not meet the 5-quote minimum due to a lack of unique quotes in the available category pool. All unique quotes have been assigned without duplication or hallucination."
        }
    ],
    "scenes": scenes_out
}

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(out_json, f, indent=2)

print("Created curate_patch.json")
