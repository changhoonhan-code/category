"""
Filter category_analysis.json for agent-specific profiles — category_analysis.json의
무거운 quote 본문과 불필요 필드를 제거하여 에이전트별 토큰 최적화 축소본을 생성.

Usage:
    python tools/filter_category.py --profile blueprint
    python tools/filter_category.py --profile tone_editor
    python tools/filter_category.py --profile tone_editor --output data/category_tone_editor.json
    python tools/filter_category.py --profile structure_engineer
    python tools/filter_category.py --profile structure_engineer --blueprint data/comparison_blueprint.json
    python tools/filter_category.py --profile writer
    python tools/filter_category.py --profile writer --outline data/comparison_outline.json
    python tools/filter_category.py --profile validator

Profiles: blueprint, tone_editor, structure_engineer, writer, validator
"""
import argparse
import json
import os
import sys


# ── 기본 경로 설정 ──────────────────────────────────────────────────────────
# cross_product_analyzer.py와 동일한 경로 패턴 사용
DEFAULT_INPUT = os.path.join("data", "category_analysis.json")


# ── Profile Definitions ─────────────────────────────────────────────────────
# 각 프로파일은 category_analysis.json에서 어떤 필드를 유지/제거할지 정의.
# 필터 함수(filter_for_*)가 프로파일별 축소 로직을 구현.

PROFILES = {
    "blueprint": {
        "description": "Blueprint Designer 전략 결정용 축소본 — quote 메타 필드 제거, 핵심 데이터 보존",
        "filter_fn": "filter_for_blueprint",
        "output_suffix": "blueprint",
    },
    "tone_editor": {
        "description": "BGM 전략, 유머 배분, 패턴 타입 판별용 축소본",
        "filter_fn": "filter_for_tone_editor",
        "output_suffix": "tone_editor",
    },
    "structure_engineer": {
        "description": "Structure Engineer 구조 설계용 축소본 — selected_themes만 필터링, quote 최소화",
        "filter_fn": "filter_for_structure_engineer",
        "output_suffix": "structure_engineer",
    },
    "writer": {
        "description": "Writer Agent 초안 작성용 축소본 — assigned_themes만 필터링, quote text 보존",
        "filter_fn": "filter_for_writer",
        "output_suffix": "writer",
    },
    "validator": {
        "description": "Data Validator 검증용 축소본 — 모든 테마 유지, 수치와 필수 메타데이터 전부 보존, 불필요 본문 제거",
        "filter_fn": "filter_for_validator",
        "output_suffix": "validator",
    },
}


# ── Blueprint Designer Profile ──────────────────────────────────────────────

def filter_quote_for_blueprint(quote: dict) -> dict:
    """
    Blueprint Designer용 quote 축소.
    보존: text (Hook/narrative_directive 판단용), star_rating, helpful_count,
          is_humorous, product_id, review_id
    제거: sentiment, review_date, selection_reason, has_media, media_info
    → quote 1개당 약 40-50% 토큰 절감
    """
    if quote is None:
        return None
    return {
        "text": quote.get("text"),
        "star_rating": quote.get("star_rating"),
        "review_id": quote.get("review_id"),
        "helpful_count": quote.get("helpful_count", 0),
        "is_humorous": quote.get("is_humorous", False),
        "product_id": quote.get("product_id"),
    }


def filter_contradiction_pair_for_blueprint(pair: dict) -> dict:
    """
    Blueprint Designer용 contradiction_pair 축소.
    보존: type, product_id/product_ids, positive_quote/negative_quote (축소됨),
          resolution_hypothesis
    """
    result = {
        "type": pair.get("type"),
    }

    # within_product이면 product_id, cross_product이면 product_ids
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")

    # quote에서 핵심 필드만 추출
    result["positive_quote"] = filter_quote_for_blueprint(pair.get("positive_quote"))
    result["negative_quote"] = filter_quote_for_blueprint(pair.get("negative_quote"))
    result["resolution_hypothesis"] = pair.get("resolution_hypothesis")

    return result


def filter_best_evidence_for_blueprint(evidence: dict) -> dict:
    """
    Blueprint Designer용 best_evidence 축소.
    first_place/last_place 각각의 quote에서 핵심 필드만 유지.
    """
    if evidence is None:
        return None
    result = {}
    for key in ("first_place", "last_place"):
        entry = evidence.get(key)
        if entry is None:
            result[key] = None
            continue
        result[key] = {
            "product_id": entry.get("product_id"),
            "quote": filter_quote_for_blueprint(entry.get("quote")),
        }
    return result


def filter_for_blueprint(data: dict) -> dict:
    """
    category_analysis.json → category_blueprint.json 축소본 생성.

    포함 필드:
    - product_count (동적 블록 캡 결정)
    - products[]: product_id, product_name, sold_last_month, all_time_rating_avg,
      all_time_rating_count, recent_review_rating_avg, recent_review_count,
      population_gap, reviews_analyzed_count, trap_candidate
    - common_themes[]: theme_name, category_pattern, category_pattern_type,
      rankings (전체 수치), contradiction_pairs (축소된 quote),
      best_evidence (축소된 quote)
    - unique_strengths[]: 전체 (Standout 매핑에 필요)
    - category_intelligence: 전체 (Verdict 전략에 필요)

    제거 필드:
    - category_name (video_question에서 사용 금지이므로 유혹 제거)
    - dataset_snapshot, previous_snapshot, delta (스냅샷 메타)
    - products[].product_category, summary_path, recent_period_text, recent_days
    - contradiction_pairs 내 quote의 sentiment, review_date, selection_reason,
      has_media, media_info
    - best_evidence 내 quote의 동일한 불필요 메타 필드
    - unique_strengths[].best_quote의 불필요 메타 필드
    """
    result = {}

    # ── product_count (동적 블록 캡 결정에 필수) ──
    result["product_count"] = data.get("product_count")

    # ── products 축소: 핵심 메타만 유지 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": p.get("trap_candidate"),  # 전체 유지 (is_trap 판단)
        })

    # ── common_themes 축소 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern": theme.get("category_pattern"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: 전체 수치 유지 (positive_ratio, mention_count 등 전략 판단에 필수)
        filtered_theme["rankings"] = [
            {
                "rank": r.get("rank"),
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
                "insight_level": r.get("insight_level"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: quote 메타 축소
        filtered_theme["contradiction_pairs"] = [
            filter_contradiction_pair_for_blueprint(pair)
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: quote 메타 축소
        filtered_theme["best_evidence"] = filter_best_evidence_for_blueprint(
            theme.get("best_evidence")
        )

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: best_quote만 축소, 나머지 전체 유지 ──
    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        filtered_us = {
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "recommended_use_case": us.get("recommended_use_case"),
            "best_quote": filter_quote_for_blueprint(us.get("best_quote")),
        }
        result["unique_strengths"].append(filtered_us)

    # ── category_intelligence: 전체 유지 (Verdict 전략에 필수) ──
    result["category_intelligence"] = data.get("category_intelligence")

    return result


# ── Tone Editor Profile ─────────────────────────────────────────────────────

def filter_quote_for_tone(quote: dict) -> dict:
    """
    contradiction_pairs 내부의 quote 객체에서 Tone Editor에 필요한 필드만 추출.
    - is_humorous: 유머 후보 검색 (CHECK 4)
    - product_id: 유머 제품별 배분 확인 (CHECK 4)
    - 나머지 (text, star_rating, review_date, helpful_count, media_info 등): 제거
    """
    if quote is None:
        return None
    return {
        "is_humorous": quote.get("is_humorous", False),
        "product_id": quote.get("product_id"),
    }


def filter_contradiction_pair_for_tone(pair: dict) -> dict:
    """
    contradiction_pairs 항목에서 Tone Editor에 필요한 필드만 추출.
    - type: 모순 유형 (within_product / cross_product) — BGM Contrast 전략용
    - product_id / product_ids: 제품 식별
    - positive_quote / negative_quote: is_humorous + product_id만 유지
    - resolution_hypothesis: 제거 (Writer/DV 영역)
    """
    result = {
        "type": pair.get("type"),
    }

    # within_product이면 product_id, cross_product이면 product_ids 사용
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")

    # quote에서 is_humorous + product_id만 추출
    result["positive_quote"] = filter_quote_for_tone(pair.get("positive_quote"))
    result["negative_quote"] = filter_quote_for_tone(pair.get("negative_quote"))

    return result


def filter_for_tone_editor(data: dict) -> dict:
    """
    category_analysis.json → category_tone_editor.json 축소본 생성.

    포함 필드:
    - common_themes[]: theme_name, category_pattern_type, rankings(product_id만),
      contradiction_pairs(type, product_id, is_humorous만)
    - unique_strengths[]: product_id, theme_name만
    - category_intelligence: maturity_assessment, universal_weaknesses만

    제거 필드:
    - category_name, product_count, dataset_snapshot, previous_snapshot, delta, products[]
    - common_themes[].category_pattern (자연어 설명)
    - common_themes[].rankings[]의 mention_count, positive_count 등 수치 필드
    - common_themes[].best_evidence 전체
    - contradiction_pairs 내 quote의 text, star_rating, review_date 등
    - unique_strengths[]의 positive_ratio, mention_count, why_unique 등
    - category_intelligence의 universal_strengths, buy_in_category, avoid_category
    """
    result = {}

    # ── common_themes 축소 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: product_id만 유지
        filtered_theme["rankings"] = [
            {"product_id": r.get("product_id")}
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: type, product_id, is_humorous만 유지
        filtered_theme["contradiction_pairs"] = [
            filter_contradiction_pair_for_tone(pair)
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: 완전 제거 (Tone Editor 불필요)

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths 축소 ──
    result["unique_strengths"] = [
        {
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
        }
        for us in data.get("unique_strengths", [])
    ]

    # ── category_intelligence 축소 ──
    ci = data.get("category_intelligence", {})
    result["category_intelligence"] = {
        "maturity_assessment": ci.get("maturity_assessment"),
        "universal_weaknesses": ci.get("universal_weaknesses", []),
    }

    return result


# ── Structure Engineer Profile ───────────────────────────────────────────────
# comparison_blueprint.json의 selected_themes를 기준으로 필요한 테마만 추출.
# Blueprint가 이미 제공한 정보(best_evidence, unique_strengths, narrative_directive)는 제거.

DEFAULT_BLUEPRINT = os.path.join("data", "comparison_blueprint.json")


def _load_selected_theme_names(blueprint_path: str) -> list[str]:
    """
    comparison_blueprint.json에서 selected_themes[].theme_name 목록 추출.
    Structure Engineer가 참조해야 할 테마만 필터링하는 기준.
    """
    if not os.path.exists(blueprint_path):
        print(json.dumps({"error": f"Blueprint not found: {blueprint_path}"}),
              file=sys.stderr)
        sys.exit(1)

    with open(blueprint_path, "r", encoding="utf-8") as f:
        bp = json.load(f)

    return [t["theme_name"] for t in bp.get("selected_themes", [])]


def filter_quote_for_structure(quote: dict) -> dict:
    """
    Structure Engineer용 quote 극소화.
    보존: text (notes에 quote reference 작성용), review_id, product_id
    제거: sentiment, star_rating, review_date, helpful_count,
          is_humorous, selection_reason, has_media, media_info
    → quote 1개당 약 60-70% 토큰 절감
    """
    if quote is None:
        return None
    return {
        "text": quote.get("text"),
        "review_id": quote.get("review_id"),
        "product_id": quote.get("product_id"),
    }


def filter_contradiction_pair_for_structure(pair: dict) -> dict:
    """
    Structure Engineer용 contradiction_pair 축소.
    보존: type, product_id/product_ids, quote(text+review_id+product_id만),
          resolution_hypothesis
    제거: quote 메타데이터 전체
    """
    result = {
        "type": pair.get("type"),
    }
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")

    result["positive_quote"] = filter_quote_for_structure(pair.get("positive_quote"))
    result["negative_quote"] = filter_quote_for_structure(pair.get("negative_quote"))
    result["resolution_hypothesis"] = pair.get("resolution_hypothesis")

    return result


def filter_for_structure_engineer(data: dict, blueprint_path: str = None) -> dict:
    """
    category_analysis.json → category_structure_engineer.json 축소본 생성.

    핵심 전략: comparison_blueprint.json의 selected_themes 목록을 기준으로
    해당 테마만 필터링하여 불필요한 excluded 테마 데이터를 완전 제거.

    포함 필드:
    - product_count (블록 캡 검증)
    - products[]: product_id, product_name, sold_last_month,
      all_time_rating_avg, recent_review_rating_avg, population_gap,
      trap_candidate (Overview/Verdict notes 작성에 필요)
    - common_themes[] (selected_themes만): theme_name, category_pattern_type,
      rankings (positive_ratio 기반 leader/laggard 식별),
      contradiction_pairs (축소된 quote)
    - category_intelligence: 전체 (Verdict notes에 필요)

    제거 필드:
    - excluded 테마의 전체 데이터
    - category_name, dataset_snapshot, previous_snapshot, delta
    - products[].product_category, summary_path, recent_period_text, recent_days,
      all_time_rating_count, recent_review_count, reviews_analyzed_count
    - common_themes[].category_pattern (자연어 설명 — Structure에 불필요)
    - common_themes[].best_evidence 전체 (Blueprint narrative_directive에 이미 포함)
    - contradiction_pairs 내 quote 메타 대부분
    - unique_strengths 전체 (Blueprint standout_mapping에 이미 포함)
    """
    # Blueprint에서 선택된 테마명 로드
    bp_path = blueprint_path or DEFAULT_BLUEPRINT
    selected_names = _load_selected_theme_names(bp_path)
    selected_set = set(selected_names)

    result = {}

    # ── product_count ──
    result["product_count"] = data.get("product_count")

    # ── products 축소: Structure Engineer에 필요한 필드만 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "population_gap": p.get("population_gap"),
            "trap_candidate": p.get("trap_candidate"),
        })

    # ── common_themes: selected_themes에 해당하는 것만 필터링 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        if theme.get("theme_name") not in selected_set:
            continue  # excluded 테마 완전 스킵

        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: 수치 필드만 유지 (leader/laggard 식별 + notes 작성)
        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_ratio": r.get("positive_ratio"),
                "insight_level": r.get("insight_level"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: quote 극소화 (text + review_id + product_id)
        filtered_theme["contradiction_pairs"] = [
            filter_contradiction_pair_for_structure(pair)
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: 완전 제거 (Blueprint narrative_directive에 이미 포함)

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: 완전 제거 (Blueprint standout_mapping에 이미 포함) ──

    # ── category_intelligence: 전체 유지 (Verdict notes에 필수) ──
    result["category_intelligence"] = data.get("category_intelligence")

    return result


# ── Writer Agent Profile ────────────────────────────────────────────────────
# comparison_outline.json의 assigned_themes를 기준으로 필요한 테마만 추출.
# Writer는 quote text가 highlight_phrase 추출에 필수이므로 text는 반드시 보존.

DEFAULT_OUTLINE = os.path.join("data", "comparison_outline.json")


def _load_assigned_theme_names(outline_path: str) -> list[str]:
    """
    comparison_outline.json에서 scenes[].assigned_themes 목록을 수집.
    Writer가 실제로 narration을 작성해야 할 테마만 필터링하는 기준.
    """
    if not os.path.exists(outline_path):
        print(json.dumps({"error": f"Outline not found: {outline_path}"}),
              file=sys.stderr)
        sys.exit(1)

    with open(outline_path, "r", encoding="utf-8") as f:
        outline = json.load(f)

    themes = set()
    for scene in outline.get("scenes", []):
        for t in scene.get("assigned_themes", []):
            themes.add(t)
    return list(themes)


def filter_quote_for_writer(quote: dict) -> dict:
    """
    Writer Agent용 quote 축소.
    보존: text (highlight_phrase 추출 필수), review_id, product_id,
          star_rating, is_humorous, selection_reason, sentiment
    제거: review_date, helpful_count, has_media, media_info
    -> quote 1개당 약 30-35% 토큰 절감
    """
    if quote is None:
        return None
    return {
        "text": quote.get("text"),
        "review_id": quote.get("review_id"),
        "product_id": quote.get("product_id"),
        "star_rating": quote.get("star_rating"),
        "sentiment": quote.get("sentiment"),
        "is_humorous": quote.get("is_humorous", False),
        "selection_reason": quote.get("selection_reason"),
    }


def filter_contradiction_pair_for_writer(pair: dict) -> dict:
    """
    Writer Agent용 contradiction_pair 축소.
    보존: type, product_id/product_ids, quote(text+핵심 메타), resolution_hypothesis
    """
    result = {
        "type": pair.get("type"),
    }
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")

    result["positive_quote"] = filter_quote_for_writer(pair.get("positive_quote"))
    result["negative_quote"] = filter_quote_for_writer(pair.get("negative_quote"))
    result["resolution_hypothesis"] = pair.get("resolution_hypothesis")

    return result


def filter_for_writer(data: dict, outline_path: str = None) -> dict:
    """
    category_analysis.json -> category_writer.json 축소본 생성.

    핵심 전략: comparison_outline.json의 assigned_themes 목록을 기준으로
    해당 테마만 필터링하여 excluded 테마 데이터를 완전 제거.
    Writer는 quote text가 highlight_phrase 추출에 필수이므로 text는 반드시 보존.

    포함 필드:
    - category_name (output 복사에 필요)
    - products[]: product_id, product_name, sold_last_month, all_time_rating_avg,
      all_time_rating_count, recent_review_rating_avg, recent_review_count,
      population_gap, reviews_analyzed_count, trap_candidate (is_trap + reason만)
    - common_themes[] (assigned_themes만): theme_name, category_pattern,
      category_pattern_type, rankings (rank/insight_level 제외),
      contradiction_pairs (quote text 보존, 메타 축소),
      best_evidence (quote text 보존, 메타 축소)
    - unique_strengths[]: 전체 (Standout scene에 필요)
    - category_intelligence: 전체 (Verdict scene에 필수)

    제거 필드:
    - dataset_snapshot, previous_snapshot, delta, product_count
    - products[].product_category, summary_path, recent_period_text, recent_days
    - products[].trap_candidate.signals
    - excluded 테마의 전체 데이터
    - rankings[].rank, insight_level (순위 노출 금지 원칙)
    - quote별: review_date, helpful_count, has_media, media_info (sentiment는 보존)
    """
    # Outline에서 할당된 테마명 로드
    ol_path = outline_path or DEFAULT_OUTLINE
    assigned_names = _load_assigned_theme_names(ol_path)
    assigned_set = set(assigned_names)

    result = {}

    # ── category_name (output에 복사 필요) ──
    result["category_name"] = data.get("category_name")

    # ── products 축소: Writer가 Category Rating Overview에서 필요한 핵심 필드만 ──
    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": {
                "is_trap": p.get("trap_candidate", {}).get("is_trap"),
                "reason": p.get("trap_candidate", {}).get("reason"),
            },
        })

    # ── common_themes: assigned_themes에 해당하는 것만 필터링 ──
    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        if theme.get("theme_name") not in assigned_set:
            continue  # excluded 테마 완전 스킵

        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            "category_pattern": theme.get("category_pattern"),
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        # rankings: rank와 insight_level 제거 (순위 노출 금지)
        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        # contradiction_pairs: quote text 보존, 불필요 메타 제거
        filtered_theme["contradiction_pairs"] = [
            filter_contradiction_pair_for_writer(pair)
            for pair in theme.get("contradiction_pairs", [])
        ]

        # best_evidence: quote text 보존, 메타 축소
        be = theme.get("best_evidence")
        if be:
            filtered_be = {}
            for key in ("first_place", "last_place"):
                entry = be.get(key)
                if entry:
                    filtered_be[key] = {
                        "product_id": entry.get("product_id"),
                        "quote": filter_quote_for_writer(entry.get("quote")),
                    }
            filtered_theme["best_evidence"] = filtered_be

        result["common_themes"].append(filtered_theme)

    # ── unique_strengths: best_quote의 text 보존, 불필요 메타 축소 ──
    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        result["unique_strengths"].append({
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "recommended_use_case": us.get("recommended_use_case"),
            "best_quote": filter_quote_for_writer(us.get("best_quote")),
        })

    # ── category_intelligence: 전체 유지 (Verdict에 필수) ──
    result["category_intelligence"] = data.get("category_intelligence")

    return result


# ── Validator Profile ───────────────────────────────────────────────────────

def filter_quote_for_validator(quote: dict) -> dict:
    """
    Data Validator용 quote 축소.
    보존: text (highlight_phrase 검증용), review_id, product_id,
          star_rating, review_date, helpful_count, selection_reason, is_humorous
    제거: sentiment, has_media, media_info
    """
    if quote is None:
        return None
    return {
        "text": quote.get("text"),
        "review_id": quote.get("review_id"),
        "product_id": quote.get("product_id"),
        "star_rating": quote.get("star_rating"),
        "review_date": quote.get("review_date"),
        "helpful_count": quote.get("helpful_count"),
        "selection_reason": quote.get("selection_reason"),
        "is_humorous": quote.get("is_humorous", False),
    }


def filter_contradiction_pair_for_validator(pair: dict) -> dict:
    """
    Data Validator용 contradiction_pair 축소.
    """
    result = {
        "type": pair.get("type"),
    }
    if pair.get("type") == "within_product":
        result["product_id"] = pair.get("product_id")
    else:
        result["product_ids"] = pair.get("product_ids")

    result["positive_quote"] = filter_quote_for_validator(pair.get("positive_quote"))
    result["negative_quote"] = filter_quote_for_validator(pair.get("negative_quote"))
    result["resolution_hypothesis"] = pair.get("resolution_hypothesis")

    return result


def filter_for_validator(data: dict) -> dict:
    """
    category_analysis.json -> category_validator.json 축소본 생성.
    Data Validator는 리뷰의 모든 수치와 메타를 검증하므로 데이터는 유지하되
    최소한으로 불필요한 필드만 제거한다.
    """
    result = {}

    result["category_name"] = data.get("category_name")
    result["product_count"] = data.get("product_count")

    result["products"] = []
    for p in data.get("products", []):
        result["products"].append({
            "product_id": p.get("product_id"),
            "product_name": p.get("product_name"),
            "sold_last_month": p.get("sold_last_month"),
            "all_time_rating_avg": p.get("all_time_rating_avg"),
            "all_time_rating_count": p.get("all_time_rating_count"),
            "recent_review_rating_avg": p.get("recent_review_rating_avg"),
            "recent_review_count": p.get("recent_review_count"),
            "population_gap": p.get("population_gap"),
            "reviews_analyzed_count": p.get("reviews_analyzed_count"),
            "trap_candidate": p.get("trap_candidate"),
        })

    result["common_themes"] = []
    for theme in data.get("common_themes", []):
        filtered_theme = {
            "theme_name": theme.get("theme_name"),
            # category_pattern(자연어 긴 본문)는 Validator 검증에 불필요하여 제거, 
            # 단 수치 검증에 필요한 필드는 전부 유지
            "category_pattern_type": theme.get("category_pattern_type"),
        }

        filtered_theme["rankings"] = [
            {
                "product_id": r.get("product_id"),
                "product_name": r.get("product_name"),
                "mention_count": r.get("mention_count"),
                "positive_count": r.get("positive_count"),
                "negative_count": r.get("negative_count"),
                "positive_ratio": r.get("positive_ratio"),
            }
            for r in theme.get("rankings", [])
        ]

        filtered_theme["contradiction_pairs"] = [
            filter_contradiction_pair_for_validator(pair)
            for pair in theme.get("contradiction_pairs", [])
        ]

        be = theme.get("best_evidence")
        if be:
            filtered_be = {}
            for key in ("first_place", "last_place"):
                entry = be.get(key)
                if entry:
                    filtered_be[key] = {
                        "product_id": entry.get("product_id"),
                        "quote": filter_quote_for_validator(entry.get("quote")),
                    }
            filtered_theme["best_evidence"] = filtered_be

        result["common_themes"].append(filtered_theme)

    result["unique_strengths"] = []
    for us in data.get("unique_strengths", []):
        result["unique_strengths"].append({
            "product_id": us.get("product_id"),
            "theme_name": us.get("theme_name"),
            "positive_ratio": us.get("positive_ratio"),
            "mention_count": us.get("mention_count"),
            "why_unique": us.get("why_unique"),
            "best_quote": filter_quote_for_validator(us.get("best_quote")),
        })

    # category_intelligence 전체 유지 (문맥 파악 및 수치 존재 가능성)
    result["category_intelligence"] = data.get("category_intelligence")

    return result


# ── 프로파일 -> 필터 함수 매핑 ───────────────────────────────────────────────
FILTER_FUNCTIONS = {
    "blueprint": filter_for_blueprint,
    "tone_editor": filter_for_tone_editor,
    "structure_engineer": filter_for_structure_engineer,
    "writer": filter_for_writer,
    "validator": filter_for_validator,
}


def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Filter category_analysis.json for agent-specific profiles"
    )
    parser.add_argument(
        "--profile", required=True, choices=list(PROFILES.keys()),
        help="에이전트 프로파일명"
    )
    parser.add_argument(
        "--input", default=DEFAULT_INPUT,
        help=f"입력 category_analysis.json 경로 (기본: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", default=None,
        help="출력 경로 (기본: data/category_{profile}.json)"
    )
    parser.add_argument(
        "--blueprint", default=DEFAULT_BLUEPRINT,
        help=f"comparison_blueprint.json 경로 (structure_engineer 프로파일 전용, "
             f"기본: {DEFAULT_BLUEPRINT})"
    )
    parser.add_argument(
        "--outline", default=DEFAULT_OUTLINE,
        help=f"comparison_outline.json 경로 (writer 프로파일 전용, "
             f"기본: {DEFAULT_OUTLINE})"
    )
    args = parser.parse_args()

    # 기본 출력 경로: data/category_{profile}.json
    if args.output is None:
        suffix = PROFILES[args.profile]["output_suffix"]
        args.output = os.path.join("data", f"category_{suffix}.json")

    # 입력 파일 확인
    if not os.path.exists(args.input):
        print(json.dumps({"error": f"File not found: {args.input}"}))
        sys.exit(1)

    # 데이터 로드
    with open(args.input, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 프로파일별 필터 적용
    filter_fn = FILTER_FUNCTIONS[args.profile]
    # structure_engineer 프로파일은 blueprint_path 인자가 필요
    if args.profile == "structure_engineer":
        filtered = filter_fn(data, blueprint_path=args.blueprint)
    # writer 프로파일은 outline_path 인자가 필요
    elif args.profile == "writer":
        filtered = filter_fn(data, outline_path=args.outline)
    else:
        filtered = filter_fn(data)

    # 출력 디렉토리 생성 (없으면)
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    # 저장
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)

    # ── 실행 결과 요약 (machine-parseable) ──
    original_size = os.path.getsize(args.input)
    filtered_json = json.dumps(filtered, ensure_ascii=False, indent=2)
    filtered_size = len(filtered_json.encode("utf-8"))
    reduction = round(100 * (1 - filtered_size / original_size), 1)

    print(json.dumps({
        "profile": args.profile,
        "input": args.input,
        "output": args.output,
        "original_bytes": original_size,
        "filtered_bytes": filtered_size,
        "reduction_pct": reduction,
    }), file=sys.stdout)

    print(
        f"[filter_category] {args.profile}: "
        f"{original_size:,} -> {filtered_size:,} bytes "
        f"({reduction}% reduction)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
