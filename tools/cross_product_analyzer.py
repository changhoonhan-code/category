"""
Cross-Product Analyzer — 다중 제품 summary.json을 비교 분석하여 category_analysis.json을 생성.

사용법:
    python tools/cross_product_analyzer.py
    python tools/cross_product_analyzer.py --data-dir data/products --output data/category_analysis.json

단계별 구현:
    Step 1: LOAD   — 데이터 수집 + 카테고리 검증 ✅
    Step 2: MATCH  — LLM 테마 클러스터링 ✅
    Step 3: RANK   — 감성 비율 순위 + 패턴 분류 ✅
    Step 4: DETECT — 모순 탐지 ✅
    Step 5: ISOLATE — 고유 분화점 추출 ✅
    Step 6: ASSESS — 카테고리 인텔리전스 (Category Analyst Agent 담당 — 이 스크립트 범위 밖)
    Step 7: EMIT   — 최종 조립 + 저장 ✅
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import MODELS

# ── 로깅 설정 ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic 스키마 — Step 2: MATCH (LLM 구조적 출력 강제용)
# ══════════════════════════════════════════════════════════════════════════════

class ThemeClusterMember(BaseModel):
    """한 클러스터에 속한 개별 테마. product_id + 원본 테마명으로 출처 추적."""
    product_id: str = Field(description="제품 식별자 (예: product_a)")
    original_theme_name: str = Field(description="해당 제품 summary.json의 원본 테마 이름")


class ThemeCluster(BaseModel):
    """의미적으로 동일한 사용자 경험을 다루는 테마들의 그룹."""
    canonical_name: str = Field(
        description="클러스터를 대표하는 가장 일반적이고 직관적인 영어 이름"
    )
    members: List[ThemeClusterMember] = Field(
        description="이 클러스터에 속한 모든 원본 테마 목록"
    )
    coverage: int = Field(
        description="몇 개 제품에 이 테마가 존재하는지 (1=unique, 2+=common)"
    )


class ThemeClusteringResult(BaseModel):
    """LLM 테마 클러스터링 전체 결과. 모든 입력 테마가 정확히 하나의 클러스터에 매핑되어야 함."""
    reasoning: str = Field(
        description="클러스터링을 수행하기 전, 과클러스터링 방지 규칙(Rule 3) 및 모호성 해소 기준에 따라 스스로의 판단 논리를 서술하는 필드"
    )
    clusters: List[ThemeCluster] = Field(
        description="시맨틱 클러스터 목록. 모든 입력 테마를 빠짐없이 포함해야 한다."
    )


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: LOAD — 데이터 수집 + 카테고리 검증
# ══════════════════════════════════════════════════════════════════════════════

def load_product_summaries(
    data_products_dir: Path,
    raw_products_dir: Path,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    data/products/*/summary.json를 전부 로드하고 카테고리 일관성을 검증.
    
    summary.json에 product_category가 없는 경우,
    원본 products/*/product.json에서 fallback으로 보충한다.
    
    Args:
        data_products_dir: summary.json이 있는 디렉토리 (예: data/products)
        raw_products_dir: 원본 product.json이 있는 디렉토리 (예: products)
    
    반환:
        category_name: 전 제품 공통 product_category 값
        products: [{
            "product_id": "product_a",
            "product_name": "Sony WF-1000XM5",
            "product_category": "earbuds over $200",
            "product_data": { ... },       # summary.json의 product_data 전체
            "themes": [ ... ],             # summary.json의 themes 전체
            "theme_names": ["ANC", ...],   # 테마 이름만 추출한 리스트
            "summary_path": "data/products/product_a/summary.json"
        }]
    
    예외:
        SystemExit: summary.json이 하나도 없거나, 카테고리가 불일치할 때
    """
    # ── 제품 디렉토리 탐색 ──────────────────────────────────────────────────
    if not data_products_dir.exists():
        logger.error(f"데이터 디렉토리가 존재하지 않음: {data_products_dir}")
        sys.exit(1)

    # summary.json이 존재하는 제품 디렉토리만 수집
    product_dirs = sorted([
        d for d in data_products_dir.iterdir()
        if d.is_dir() and (d / "summary.json").exists()
    ])

    if not product_dirs:
        logger.error(f"{data_products_dir}에 summary.json이 있는 제품 디렉토리가 없음")
        sys.exit(1)

    # ── 각 제품의 summary.json 로드 ─────────────────────────────────────────
    products: List[Dict[str, Any]] = []
    categories_found: Dict[str, str] = {}  # product_id → product_category

    for p_dir in product_dirs:
        product_id = p_dir.name
        summary_path = p_dir / "summary.json"

        try:
            with summary_path.open("r", encoding="utf-8") as f:
                summary = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"{product_id}: summary.json 로드 실패 — {e}")
            continue

        # 필수 필드 존재 확인
        product_data = summary.get("product_data")
        themes = summary.get("themes")

        if not product_data:
            logger.error(f"{product_id}: summary.json에 'product_data' 필드가 없음")
            continue
        if themes is None:
            logger.error(f"{product_id}: summary.json에 'themes' 필드가 없음")
            continue

        # ── 카테고리명 추출 (summary.json → product.json fallback) ──────────
        category = product_data.get("product_category", "")
        if not category:
            # summary.json에 없으면 원본 product.json에서 보충 시도
            raw_product_json = raw_products_dir / product_id / "product.json"
            if raw_product_json.exists():
                try:
                    with raw_product_json.open("r", encoding="utf-8") as f:
                        raw_prod = json.load(f)
                    category = raw_prod.get("product_category", "")
                    if category:
                        logger.info(f"  ↩ {product_id}: product.json에서 카테고리 보충 — \"{category}\"")
                except Exception:
                    pass

        if not category:
            logger.warning(f"{product_id}: product_category를 어디서도 찾을 수 없음")
        else:
            category = category.strip().lower()

        categories_found[product_id] = category

        # 테마 이름 리스트 추출
        theme_names = [
            t.get("theme_name", "")
            for t in themes
            if t.get("theme_name")
        ]

        products.append({
            "product_id": product_id,
            "product_name": product_data.get("product_name", "Unknown"),
            "product_category": category,
            "product_data": product_data,
            "themes": themes,
            "theme_names": theme_names,
            "summary_path": str(summary_path),
        })

        logger.info(
            f"  ✅ {product_id}: {product_data.get('product_name', '?')} "
            f"({len(themes)} themes, "
            f"{product_data.get('reviews_analyzed_count', '?')} reviews)"
        )

    if not products:
        logger.error("유효한 제품 데이터가 하나도 없음. 종료.")
        sys.exit(1)

    # ── 카테고리 일관성 검증 ────────────────────────────────────────────────
    unique_categories = set(categories_found.values()) - {""}

    if len(unique_categories) == 0:
        logger.error("어떤 제품에서도 product_category를 찾을 수 없음.")
        logger.error("각 products/*/product.json에 product_category 필드가 있는지 확인하세요.")
        sys.exit(1)
    elif len(unique_categories) > 1:
        logger.error(f"제품 간 카테고리 불일치 감지:")
        for pid, cat in categories_found.items():
            logger.error(f"  {pid}: \"{cat}\"")
        logger.error("모든 제품의 product_category가 동일해야 합니다.")
        sys.exit(1)

    category_name = unique_categories.pop()
    logger.info(f"  📦 카테고리 확인: \"{category_name}\"")

    return category_name, products




# ══════════════════════════════════════════════════════════════════════════════
# Step 2: MATCH — LLM 시맨틱 테마 클러스터링
# ══════════════════════════════════════════════════════════════════════════════

# ── 클러스터링 프롬프트 ─────────────────────────────────────────────────────
# LLM에게 제품별 테마 목록을 주고, 의미적으로 동일한 사용자 경험을 하나의
# canonical name으로 그룹핑하도록 지시한다.
# 과클러스터링 방지를 "원칙 기반" 분리 규칙으로 제공하여 도메인 재사용성을 확보.
_THEME_CLUSTERING_PROMPT = """\
You are a consumer electronics review analyst specializing in the "{category}" category.
Your task is to determine which review theme names from {product_count} different products
describe the same underlying user experience, and group them into semantic clusters.

## INPUT — Theme names per product
{theme_listings}

## CLUSTERING RULES

1. **Same user experience = same cluster.**
   If a consumer complaining about Theme A would also be describing the experience
   captured by Theme B, they belong in the same cluster — regardless of wording.
   Hypothetical examples (NOT from the input above):
   - "Screen Brightness" + "Display Brightness Level" -> "Display Brightness"
   - "Keyboard Noise" + "Typing Sound Level" -> "Keyboard Noise"

2. **Multiple themes from the SAME product CAN map to the same cluster**
   if they genuinely describe the same experience from different angles.
   For example, a product may have both "X Reliability" and "X Reliability Issues"
   — these likely describe the same dimension and should be merged.

3. **DO NOT over-cluster.** Apply these separation principles:
   (Example of what NOT to merge: DO NOT merge 'Microphone Quality' and 'Call Quality' into a single cluster.)

   a) **Hardware vs Experience**: The physical component is distinct from the
      end-to-end experience it enables.
      (e.g., microphone hardware quality != phone call experience)

   b) **Comfort vs Physical Hold**: Subjective comfort (pain, pressure, fatigue)
      is distinct from physical security (staying in place, falling out).

   c) **One-time Process vs Ongoing State**: A setup/pairing process
      is distinct from continuous connection reliability.

   d) **Active vs Passive**: Electronically-powered features
      are distinct from passive physical properties achieving a similar goal.

   e) **Aesthetics vs Longevity**: Perceived build quality / premium feel
      is distinct from long-term durability / survival.

   When in doubt between distinct consumer pains (like physical pain vs falling out), **keep them separate**.
   However, for sub-features that serve the SAME ultimate macro-experience (e.g., merging "Charging Speed", "Charging Reliability", "Charging Compatibility" into "Charging Experience"), **MERGE them** to preserve statistical weight.

4. **DISAMBIGUATION HEURISTIC (Complex Names)**:
   For complex or compound theme names, determine the CORE consumer experience being evaluated.
   - "Microphone Call Quality" -> Core is Call experience, not just hardware.
   - "Bass Audio Performance" -> Core is Audio/Sound quality.

5. **Every input theme must appear in exactly one cluster.**
   No theme may be omitted or duplicated.

6. **canonical_name** should be the most widely understood English term
   for that experience dimension. Keep it concise (1-3 words).
   Prefer general over brand-specific phrasing.

7. **coverage** = number of distinct products with at least one member in this cluster.

## OUTPUT
Return a JSON object matching the schema.
CRITICAL: You MUST write a brief "reasoning" BEFORE outputting the "clusters" array.
In your reasoning, explain how you applied Rule 3 (Separation Principles) and Rule 4 (Disambiguation) to the tricky cases.
"""


def _build_theme_listings(products: List[Dict[str, Any]]) -> str:
    """
    LLM 프롬프트에 삽입할 제품별 테마 이름 목록을 생성한다.
    클러스터링은 순수 이름 기반 시맨틱 매칭이므로,
    mention_count/sentiment 등 통계는 포함하지 않는다.
    (통계를 넣으면 이름 유사성이 아닌 수치 유사성으로 잘못 판단할 위험)
    """
    lines: List[str] = []
    for p in products:
        # 제품 헤더
        lines.append(f"### {p['product_id']} ({p['product_name']}) — {len(p['theme_names'])} themes")
        for tn in p["theme_names"]:
            lines.append(f"- {tn}")
        lines.append("")  # 제품 간 빈 줄
    return "\n".join(lines)


def cluster_themes_via_llm(
    products: List[Dict[str, Any]],
    output_path: Path,
    category: str = "",
) -> ThemeClusteringResult:
    """
    LLM 1회 호출로 모든 제품의 테마를 시맨틱 클러스터로 그룹핑한다.
    
    동작 흐름:
        1. 제품별 테마 이름 목록을 프롬프트에 구성 (통계 제외 — 순수 시맨틱 매칭)
        2. Gemini API 호출 (response_schema=ThemeClusteringResult로 구조적 출력 강제)
        3. 응답 검증: 입력 테마 전수 매핑 확인 + coverage 재계산
        4. data/intermediate/theme_clusters.json에 중간 결과 저장
    
    Args:
        products: Step 1에서 반환된 제품 리스트
        output_path: 클러스터링 결과 저장 경로 (예: data/intermediate/theme_clusters.json)
        category: 제품 카테고리명 (예: "earbuds over $200") — LLM에 도메인 맥락 제공
    
    반환:
        ThemeClusteringResult — Pydantic 모델 인스턴스
    
    예외:
        SystemExit: LLM 호출 3회 연속 실패 시
    """
    # ── 입력 테마 전수 목록 구축 (검증용) ─────────────────────────────────────
    # (product_id, theme_name) 튜플 셋으로 누락/중복 체크에 사용
    expected_members: set = set()
    for p in products:
        for tn in p["theme_names"]:
            expected_members.add((p["product_id"], tn))
    
    total_input_themes = len(expected_members)
    logger.info(f"  📊 클러스터링 대상: {total_input_themes}개 테마 ({len(products)}개 제품)")

    # ── 프롬프트 조립 ────────────────────────────────────────────────────────
    theme_listings = _build_theme_listings(products)
    prompt = _THEME_CLUSTERING_PROMPT.format(
        category=category or "consumer electronics",
        product_count=len(products),
        theme_listings=theme_listings,
    )

    # ── Gemini API 호출 (최대 3회 재시도) ─────────────────────────────────────
    client = genai.Client()
    model_id = MODELS.get("analysis_pro", "gemini-pro-latest")
    logger.info(f"  🤖 LLM 모델: {model_id}")

    result: ThemeClusteringResult | None = None

    for attempt in range(1, 4):
        try:
            logger.info(f"  → LLM 호출 시도 {attempt}/3...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ThemeClusteringResult,
                    temperature=0.1,  # 재현성을 위해 낮은 temperature
                ),
            )

            # Pydantic parsed 응답 우선, fallback으로 텍스트 파싱
            parsed = getattr(response, "parsed", None)
            if parsed and isinstance(parsed, ThemeClusteringResult):
                result = parsed
            else:
                # response_schema가 적용되었으므로 텍스트가 JSON이어야 함
                raw_text = response.text.replace("```json", "").replace("```", "").strip()
                raw_dict = json.loads(raw_text)
                result = ThemeClusteringResult(**raw_dict)

            logger.info(f"  ✅ LLM 응답 수신: {len(result.clusters)}개 클러스터")
            break

        except Exception as e:
            logger.warning(f"  ⚠️ 시도 {attempt} 실패: {e}")
            if attempt < 3:
                import time
                time.sleep(attempt * 3)  # 점진적 백오프
            else:
                logger.error("  ❌ LLM 호출 3회 연속 실패. 종료.")
                sys.exit(1)

    # ── 응답 검증: 입력 테마 전수 매핑 확인 ────────────────────────────────────
    # LLM이 테마를 빠뜨리거나 존재하지 않는 테마를 추가했는지 체크
    actual_members: set = set()
    for cluster in result.clusters:
        for member in cluster.members:
            actual_members.add((member.product_id, member.original_theme_name))

    # 누락된 테마 확인
    missing = expected_members - actual_members
    if missing:
        logger.warning(f"  ⚠️ LLM이 누락한 테마 {len(missing)}개:")
        for pid, tn in sorted(missing):
            logger.warning(f"    - {pid}: {tn}")

    # 환각 테마 확인 (입력에 없는 테마가 결과에 포함된 경우)
    hallucinated = actual_members - expected_members
    if hallucinated:
        logger.warning(f"  ⚠️ LLM이 환각한 테마 {len(hallucinated)}개 (입력에 없음):")
        for pid, tn in sorted(hallucinated):
            logger.warning(f"    - {pid}: {tn}")

    # coverage 값 재계산 및 교정
    # LLM이 잘못된 coverage를 반환할 수 있으므로, 실제 member의 product_id 기준으로 재계산
    for cluster in result.clusters:
        actual_coverage = len(set(m.product_id for m in cluster.members))
        if cluster.coverage != actual_coverage:
            logger.info(
                f"  🔧 coverage 교정: \"{cluster.canonical_name}\" "
                f"{cluster.coverage} → {actual_coverage}"
            )
            cluster.coverage = actual_coverage

    # ── 결과 저장 ────────────────────────────────────────────────────────────
    # data/intermediate/ 디렉토리 자동 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Pydantic 모델을 dict로 변환 후 JSON 저장 (indent=2로 사람이 읽기 쉽게)
    result_dict = result.model_dump()
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)
    
    logger.info(f"  💾 클러스터링 결과 저장: {output_path}")

    return result




# ══════════════════════════════════════════════════════════════════════════════
# Step 3, 4, 5: RANK, DETECT, ISOLATE 
# ══════════════════════════════════════════════════════════════════════════════

def process_quantitative_data(products: List[Dict[str, Any]], clustering_result: ThemeClusteringResult) -> Tuple[List[Dict], List[Dict]]:
    common_themes_data = []
    unique_strengths_data = []

    product_map = {p["product_id"]: p for p in products}

    # Helper to find theme data
    def get_theme_data(pid: str, original_name: str):
        for t in product_map[pid]["themes"]:
            if t.get("theme_name") == original_name:
                return t
        return None

    for cluster in clustering_result.clusters:
        grouped_members = {}
        for m in cluster.members:
            if m.product_id not in product_map:
                continue
            tj = get_theme_data(m.product_id, m.original_theme_name)
            if not tj:
                continue
            
            sd = tj.get("sentiment_distribution", {})
            pos = sd.get("positive", 0)
            neg = sd.get("negative", 0)
            neu = sd.get("neutral", 0)
            
            if m.product_id in grouped_members:
                grouped_members[m.product_id]["mention_count"] += tj.get("mention_count", 0)
                grouped_members[m.product_id]["positive_count"] += pos
                grouped_members[m.product_id]["negative_count"] += neg
                grouped_members[m.product_id]["neutral_count"] += neu
                grouped_members[m.product_id]["evidence_quotes"].extend(tj.get("evidence_quotes", []))
                grouped_members[m.product_id]["original_theme_name"] += f", {m.original_theme_name}"
            else:
                grouped_members[m.product_id] = {
                    "product_id": m.product_id,
                    "product_name": product_map[m.product_id]["product_name"],
                    "original_theme_name": m.original_theme_name,
                    "mention_count": tj.get("mention_count", 0),
                    "positive_count": pos,
                    "negative_count": neg,
                    "neutral_count": neu,
                    "evidence_quotes": tj.get("evidence_quotes", [])
                }
                
        members_data = []
        for g in grouped_members.values():
            total = g["positive_count"] + g["negative_count"] + g["neutral_count"]
            g["positive_ratio"] = g["positive_count"] / total if total > 0 else 0
            members_data.append(g)
        
        if not members_data:
            continue

        coverage = len(set(x["product_id"] for x in members_data))

        # STEP 5: ISOLATE (Unique Strengths: Coverage=1)
        if coverage == 1:
            member = members_data[0]
            quotes = member.get("evidence_quotes", [])
            pos_quotes = [q for q in quotes if q.get("star_rating", 0) >= 4 and q.get("sentiment") == "Positive"]
            pos_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            best_quote = dict(pos_quotes[0]) if pos_quotes else None
            if best_quote:
                best_quote["product_id"] = member["product_id"]

            unique_strengths_data.append({
                "product_id": member["product_id"],
                "theme_name": cluster.canonical_name,
                "original_theme_name": member["original_theme_name"],
                "positive_ratio": round(member["positive_ratio"], 3),
                "mention_count": member["mention_count"],
                "ratio_gap": round(member["positive_ratio"], 3),
                "is_exclusive_feature": True,  # coverage==1: 이 제품만 보유한 독점 기능
                "why_unique": "",
                "recommended_use_case": "",
                "best_quote": best_quote
            })
            continue

        # STEP 3: RANK (Common Themes)
        members_data.sort(key=lambda x: x["positive_ratio"], reverse=True)
        rankings = []
        for i, md in enumerate(members_data):
            rank = i + 1
            insight_level = "full" if rank == 1 or rank == len(members_data) else "rank_only"
            rankings.append({
                "rank": rank,
                "product_id": md["product_id"],
                "product_name": md["product_name"],
                "mention_count": md["mention_count"],
                "positive_count": md["positive_count"],
                "negative_count": md["negative_count"],
                "positive_ratio": round(md["positive_ratio"], 3),
                "insight_level": insight_level
            })

        pos_ratios = [md["positive_ratio"] for md in members_data]
        max_ratio = max(pos_ratios)
        min_ratio = min(pos_ratios)

        cat_pattern_type = "mixed"
        if all(r >= 0.6 for r in pos_ratios):
            cat_pattern_type = "universal_strength"
        elif all(r <= 0.4 for r in pos_ratios):
            cat_pattern_type = "universal_weakness"
        elif (max_ratio - min_ratio) > 0.3:
            cat_pattern_type = "differentiator"

        # STEP 5: ISOLATE (독보적 긍정 테마 in Common Theme)
        # 정합성 수정: LLM이 반환한 객체의 속성 대신 실제 계산된 정확한 로컬 coverage 변수를 사용
        if coverage >= 2:
            target_md = members_data[0]
            second_md = members_data[1]
            ratio_gap = target_md["positive_ratio"] - second_md["positive_ratio"]
            
            quotes = target_md.get("evidence_quotes", [])
            pos_quotes = [q for q in quotes if q.get("star_rating", 0) >= 4 and q.get("sentiment") == "Positive"]
            pos_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            best_quote = dict(pos_quotes[0]) if pos_quotes else None
            if best_quote:
                best_quote["product_id"] = target_md["product_id"]

            unique_strengths_data.append({
                "product_id": target_md["product_id"],
                "theme_name": cluster.canonical_name,
                "original_theme_name": target_md["original_theme_name"],
                "positive_ratio": round(target_md["positive_ratio"], 3),
                "mention_count": target_md["mention_count"],
                "ratio_gap": round(ratio_gap, 3),
                "is_exclusive_feature": False,  # coverage>=2: common theme의 leader
                "why_unique": "",
                "recommended_use_case": "",
                "best_quote": best_quote
            })

        # STEP 4: DETECT (Contradiction pairs)
        contradiction_pairs = []
        
        # 4-A. Within-product
        for md in members_data:
            quotes = md.get("evidence_quotes", [])
            pos_quotes = [q for q in quotes if q.get("star_rating", 0) >= 4 and q.get("sentiment") == "Positive"]
            neg_quotes = [q for q in quotes if q.get("star_rating", 0) <= 2 and q.get("sentiment") == "Negative"]
            
            if pos_quotes and neg_quotes:
                pos_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
                neg_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
                
                pos_q = dict(pos_quotes[0])
                pos_q["product_id"] = md["product_id"]
                neg_q = dict(neg_quotes[0])
                neg_q["product_id"] = md["product_id"]
                
                contradiction_pairs.append({
                    "type": "within_product",
                    "product_id": md["product_id"],
                    "product_ids": None,
                    "positive_quote": pos_q,
                    "negative_quote": neg_q,
                    "resolution_hypothesis": ""
                })

        # 4-B. Cross-product (편차가 큰 differentiator 테마일 경우)
        # 정합성 수정: max_ratio - min_ratio > 0 은 모든 테마를 포함하므로, 'differentiator'의 의미에 맞게 유의미한 편차(예: 20% 이상 격차)가 있을 때만 크로스 모순으로 탐지
        if (max_ratio - min_ratio) >= 0.2 and len(members_data) >= 2:
            first = members_data[0]
            last = members_data[-1]
            ratio_gap = first["positive_ratio"] - last["positive_ratio"]
            first_quotes = [q for q in first.get("evidence_quotes", []) if q.get("star_rating", 0) >= 4 and q.get("sentiment") == "Positive"]
            last_quotes = [q for q in last.get("evidence_quotes", []) if q.get("star_rating", 0) <= 2 and q.get("sentiment") == "Negative"]
            
            first_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            last_quotes.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            
            if first_quotes and last_quotes:
                pos_q = dict(first_quotes[0])
                pos_q["product_id"] = first["product_id"]
                neg_q = dict(last_quotes[0])
                neg_q["product_id"] = last["product_id"]
                
                contradiction_pairs.append({
                    "type": "cross_product",
                    "product_id": None,
                    "product_ids": [first["product_id"], last["product_id"]],
                    "ratio_gap": round(ratio_gap, 3),
                    "positive_quote": pos_q,
                    "negative_quote": neg_q,
                    "resolution_hypothesis": ""
                })

        # Best evidence 추출 (1위와 최하위의 대표 리뷰)
        best_evidence = None
        if len(members_data) > 1:
            best_first = [q for q in members_data[0].get("evidence_quotes", []) if q.get("star_rating", 0) >= 4 and q.get("sentiment") == "Positive"]
            best_first.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            first_quote = best_first[0] if best_first else (members_data[0].get("evidence_quotes", [{}])[0] if members_data[0].get("evidence_quotes") else {})

            best_last = [q for q in members_data[-1].get("evidence_quotes", []) if q.get("star_rating", 0) <= 2 and q.get("sentiment") == "Negative"]
            best_last.sort(key=lambda x: x.get("helpful_count", 0), reverse=True)
            last_quote = best_last[0] if best_last else (members_data[-1].get("evidence_quotes", [{}])[0] if members_data[-1].get("evidence_quotes") else {})

            if first_quote and last_quote:
                first_q_copy = dict(first_quote)
                first_q_copy["product_id"] = members_data[0]["product_id"]
                last_q_copy = dict(last_quote)
                last_q_copy["product_id"] = members_data[-1]["product_id"]

                best_evidence = {
                    "first_place": {
                        "product_id": members_data[0]["product_id"],
                        "quote": first_q_copy
                    },
                    "last_place": {
                        "product_id": members_data[-1]["product_id"],
                        "quote": last_q_copy
                    }
                }

        common_themes_data.append({
            "theme_name": cluster.canonical_name,
            "category_pattern": "",
            "category_pattern_type": cat_pattern_type,
            "rankings": rankings,
            "contradiction_pairs": contradiction_pairs,
            "best_evidence": best_evidence
        })

    return common_themes_data, unique_strengths_data

# ══════════════════════════════════════════════════════════════════════════════
# Step 7: EMIT — 최종 결과물 구조화 및 저장
# ══════════════════════════════════════════════════════════════════════════════

def enhance_products_and_snapshot(products: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    import datetime
    total_reviews = sum(p["product_data"].get("reviews_analyzed_count", 0) for p in products)
    snapshot = {
        "collected_through": datetime.datetime.now().strftime("%Y-%m-%d"),
        "total_reviews_analyzed": total_reviews,
        "product_count": len(products)
    }

    out_products = []
    for p in products:
        pd_data = p["product_data"]
        themes = p.get("themes", [])
        
        total_neg_ratio = 0.0
        neg_majority_count = 0
        for t in themes:
            sd = t.get("sentiment_distribution", {})
            pos = sd.get("positive", 0)
            neg = sd.get("negative", 0)
            neu = sd.get("neutral", 0)
            tot = pos + neg + neu
            if tot > 0:
                nratio = neg / tot
                total_neg_ratio += nratio
                if nratio > 0.5:
                    neg_majority_count += 1
        avg_neg_ratio = total_neg_ratio / len(themes) if themes else 0.0
        pop_gap = round(pd_data.get("population_gap", 0.0), 2)
        
        sold_str = str(pd_data.get("sold_last_month", "0")).upper().replace("K+", "000").replace("M+", "000000").replace(",", "")
        sold_val = 0
        try: sold_val = int("".join(filter(str.isdigit, sold_str)) or "0")
        except: pass
        
        is_trap = (sold_val >= 1000) and (avg_neg_ratio >= 0.5 or pop_gap >= 0.5 or neg_majority_count >= 3)

        out_p = {
            "product_id": p["product_id"],
            "product_name": p["product_name"],
            "product_category": p["product_category"],
            "sold_last_month": pd_data.get("sold_last_month", ""),
            "all_time_rating_avg": pd_data.get("all_time_rating_avg", 0.0),
            "all_time_rating_count": pd_data.get("all_time_rating_count", 0),
            "recent_review_rating_avg": pd_data.get("recent_review_rating_avg", 0.0),
            "recent_review_count": pd_data.get("recent_review_count", 0),
            "population_gap": pop_gap,
            "reviews_analyzed_count": pd_data.get("reviews_analyzed_count", 0),
            "summary_path": p["summary_path"],
            "recent_period_text": pd_data.get("recent_period_text", ""),
            "recent_days": pd_data.get("recent_days", 0),
            "trap_candidate": {
                "is_trap": is_trap,
                "reason": "High sales masking negative recent metrics or themes." if is_trap else None,
                "signals": {
                    "sold_last_month": pd_data.get("sold_last_month", ""),
                    "avg_negative_ratio_across_themes": round(avg_neg_ratio, 3),
                    "population_gap": pop_gap,
                    "themes_with_majority_negative": neg_majority_count
                }
            }
        }
        out_products.append(out_p)

    return out_products, snapshot

def emit_final_result(
    category_name: str,
    products: List[Dict],
    common_themes: List[Dict],
    unique_strengths: List[Dict],
    output_path: Path
):
    out_products, snapshot = enhance_products_and_snapshot(products)

    final_json = {
        "category_name": category_name,
        "product_count": len(out_products),
        "dataset_snapshot": snapshot,
        "previous_snapshot": None,
        "delta": None,
        "products": out_products,
        "common_themes": common_themes,
        "unique_strengths": unique_strengths,
        "category_intelligence": None
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    logger.info(f"  💾 카테고리 후보 저장 완료: {output_path}")

# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Cross-Product Analyzer — N개 제품 비교 분석"
    )
    parser.add_argument(
        "--data-dir", type=str, default="data/products",
        help="제품별 summary.json이 있는 디렉토리 (기본: data/products)"
    )
    parser.add_argument(
        "--products-dir", type=str, default="products",
        help="원본 product.json이 있는 디렉토리 (기본: products)"
    )
    parser.add_argument(
        "--output", type=str, default="data/category_candidates.json",
        help="최종 출력 경로 (기본: data/category_candidates.json)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    products_dir = Path(args.products_dir)
    output_path = Path(args.output)

    logger.info(f"=== Cross-Product Analyzer ===")
    logger.info(f"Data dir: {data_dir}")
    logger.info(f"Products dir: {products_dir}")
    logger.info(f"Output: {output_path}")

    # ── Step 1: LOAD ───────────────────────────────────────────────────────
    logger.info("Step 1: LOAD — 제품 데이터 수집 + 카테고리 검증")
    category_name, products = load_product_summaries(data_dir, products_dir)
    # Step 1 요약 로그
    total_themes = sum(len(p["theme_names"]) for p in products)
    total_reviews = sum(p["product_data"].get("reviews_analyzed_count", 0) for p in products)
    logger.info(
        f"  LOAD 완료: {len(products)}개 제품, "
        f"{total_reviews:,} reviews, {total_themes} themes (pre-clustering)"
    )

    # ── Step 2: MATCH — 테마 클러스터링 ────────────────────────────────────
    logger.info("Step 2: MATCH — LLM 시맨틱 테마 클러스터링")
    cluster_output_path = Path("data/intermediate/theme_clusters.json")
    if cluster_output_path.exists():
        logger.info(f"  💡 기존 클러스터 결과 로드: {cluster_output_path}")
        with cluster_output_path.open("r", encoding="utf-8") as f:
            clustering_result = ThemeClusteringResult(**json.load(f))
    else:
        clustering_result = cluster_themes_via_llm(products, cluster_output_path, category=category_name)
    # Step 2 요약 로그
    common_count = sum(1 for c in clustering_result.clusters if c.coverage >= 2)
    unique_count = sum(1 for c in clustering_result.clusters if c.coverage == 1)
    logger.info(
        f"  MATCH 완료: {len(clustering_result.clusters)}개 클러스터 "
        f"(common: {common_count}, unique: {unique_count})"
    )

    # ── Step 3~5: RANK, DETECT, ISOLATE ────────────────────────────────────
    logger.info("Step 3~5: RANK, DETECT, ISOLATE — 정량 평가 및 모순 탐지")
    common_themes, unique_strengths = process_quantitative_data(products, clustering_result)
    logger.info(f"  📊 발견된 공통 테마: {len(common_themes)}개")
    logger.info(f"  ⭐ 발견된 고유 강점: {len(unique_strengths)}개")

    # ── Step 7: EMIT ───────────────────────────────────────────────────────
    logger.info("Step 7: EMIT — 최종 카테고리 분석 데이터 조립 및 저장")
    emit_final_result(category_name, products, common_themes, unique_strengths, output_path)

if __name__ == "__main__":
    main()


