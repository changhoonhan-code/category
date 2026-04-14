"""
Data bridge CLI Tool — data aggregation and preparation.
Migrated from pipeline/skills/data_bridge.py.
"""
import argparse
import glob
import json
import logging
import math
import os
import shutil
import sys
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from config import MODELS, PROJ_ROOT
from filter_summary import filter_summary as apply_filter, PROFILES as FILTER_PROFILES

# ── Pydantic Models ────────────────────────────────────────────────────────────
class EvidenceQuoteSchema(BaseModel):
    review_id: str
    text: str
    is_humorous: bool
    selection_reason: str

class ThemeInsightsSchema(BaseModel):
    root_cause: str
    affected_user_profile: str
    temporal_pattern: str
    purchase_guidance: str
    evidence_quotes: List[EvidenceQuoteSchema] = Field(default_factory=list)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
 
# 트렌딩 테마 판별 기준
TRENDING_RATIO_THRESHOLD = 2.0
MIN_RECENT_MENTIONS = 3


# ── Media Index ────────────────────────────────────────────────────────────────

def build_media_index(
    movies_meta_glob: str,
    photos_meta_glob: str,
    input_dir: str = "one_product",
    output_dir: str = "datas"
) -> Dict[str, List[Dict[str, Any]]]:
    """_meta.json 사이드카 파일을 읽어 review_id → [media_info] 매핑을 구축.
    이 과정에서 매칭된 미디어 파일을 output_dir/media/로 복사함.
    """
    media_index: Dict[str, List[Dict]] = {}
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    dest_media_dir = output_path / "media"
    dest_media_dir.mkdir(parents=True, exist_ok=True)

    # 비디오 메타데이터 처리
    for path_str in glob.glob(movies_meta_glob):
        path = Path(path_str)
        try:
            with path.open("r", encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, list):
                m = m[0] if m else {}
            
            rid = m.get("review_id")
            if rid:
                filename = str(m.get("video_filename", ""))
                src_path = input_path / "movies" / filename
                dest_path = dest_media_dir / filename
                
                if src_path.exists():
                    shutil.copy2(src_path, dest_path)
                    
                    media_index.setdefault(rid, []).append({
                        "path": f"{output_dir}/media/{filename}",
                        "broll_description": m.get("broll_description", ""),
                        "visual_evidence": m.get("visual_evidence", ""),
                        "shot_type": m.get("shot_type", ""),
                        "is_funny": m.get("is_funny", False),
                        "text_in_image": m.get("text_in_image", ""),
                    })
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")

    # 사진 메타데이터 처리
    for path_str in glob.glob(photos_meta_glob):
        path = Path(path_str)
        try:
            with path.open("r", encoding="utf-8") as f:
                m = json.load(f)
            if isinstance(m, list):
                m = m[0] if m else {}
            
            rid = m.get("review_id")
            if rid:
                filename = str(m.get("image_filename", ""))
                src_path = input_path / "photos" / filename
                dest_path = dest_media_dir / filename
                
                if src_path.exists():
                    shutil.copy2(src_path, dest_path)
                    
                    media_index.setdefault(rid, []).append({
                        "path": f"{output_dir}/media/{filename}",
                        "broll_description": m.get("broll_description", ""),
                        "visual_evidence": m.get("visual_evidence", ""),
                        "shot_type": m.get("shot_type", ""),
                        "is_funny": m.get("is_funny", False),
                        "text_in_image": m.get("text_in_image", ""),
                    })
        except Exception as e:
            logger.error(f"Error loading {path}: {e}")

    return media_index


def build_review_lookup(original_csv_path: str) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[int]], Dict[str, int]]:
    """원본 CSV에서 review_id → 날짜, 평점, 도움주기(helpful) 횟수 조회 테이블을 구축."""
    date_map: Dict[str, Optional[str]] = {}
    rating_map: Dict[str, Optional[int]] = {}
    helpful_map: Dict[str, int] = {}

    csv_path = Path(original_csv_path)
    if not csv_path.exists():
        logger.warning(f"Original reviews CSV not found at {csv_path}. Dates/ratings will be null.")
        return date_map, rating_map, helpful_map

    orig_df = pd.read_csv(csv_path)
    for _, row in orig_df.iterrows():
        rid = str(row.get("review_id", ""))
        if rid:
            date_val = row.get("date")
            date_map[rid] = str(date_val) if pd.notna(date_val) else None
            rating_val = row.get("rating")
            rating_map[rid] = int(rating_val) if pd.notna(rating_val) else None
            helpful_val = row.get("helpful", 0)
            helpful_map[rid] = int(helpful_val) if pd.notna(helpful_val) else 0

    logger.info(f"Loaded metadata for {len(date_map)} reviews from {csv_path.name}.")
    return date_map, rating_map, helpful_map

# ── LLM Theme Insights ─────────────────────────────────────────────────────────

_THEME_SUMMARIZER_PROMPT = """You are the Lead Data Analyst for ReviewLens, a data-driven product review video series.
Our mission is to uncover the absolute truth for consumers by looking past marketing hype and focusing on concrete evidence, specific failure modes, and real-world performance.
Analyze ALL the reviews below for the theme "{theme}" and return ONLY a valid JSON object.
Theme trending status: {is_trending}
Recent mentions in recent period: {recent_mention_count} ({recent_period_text})

INSTRUCTIONS:
1. First, analyze the patterns to form your insights (root_cause, affected_user_profile, temporal_pattern, purchase_guidance).
   - If is_trending is True, your temporal_pattern MUST explicitly state whether this is a NEW emerging issue or an ESCALATION of a pre-existing problem. This distinction is critical for the narrator.
2. Then, select between 2 and 5 evidence_quotes using the SEQUENTIAL GREEDY method below.
   Fewer is better — only include a quote if it adds a perspective not already covered.
   - Written in English only.

   SEQUENTIAL GREEDY SELECTION (follow this exact order):
   a) ANCHOR (1st pick): Select the single most impactful core evidence based on this strict hierarchy:
      1. Theme Relevance: Must be highly focused on the specific "{theme}".
      2. Specificity & Readability: Contains vivid, concrete details of real-world use, written in a punchy, highly articulate way that is easy for a narrator to read.
      3. Recency: Favor more recent reviews reflecting current conditions.
      4. Balanced Perspective (Rating Contrast): Favor reviews with balanced insights (e.g., highly rated but points out a specific flaw).
      5. Helpful Count (Tie-breaker): Use ONLY if multiple reviews tie on the above metrics.
      → selection_reason: "anchor"
   b) CONTRAST (2nd pick): From the remaining reviews, pick the one with the OPPOSITE sentiment to the anchor AND the most specific/vivid detail. If the anchor is positive, this must be negative (or vice versa). Avoid echoing the anchor's points.
      → selection_reason: "contrast"
   c) HOOK (3rd pick, optional): From the remaining reviews, pick the most humorous, ironic, or memorably witty quote. If no genuinely funny quote exists, SKIP this — do not force it.
      → selection_reason: "hook"
   d) SUPPLEMENTARY (4th-5th picks, optional): Only if the theme has high review volume AND a remaining quote adds a genuinely new user context (e.g., different use environment, different failure mode). Do NOT repeat points already made by previous picks (No Echo-chamber).
      → selection_reason: "supplementary"

3. For each selected quote, copy the text EXACTLY as written — do not paraphrase.
4. For each quote, set is_humorous to true if the quote contains genuinely funny, ironic, or memorably witty phrasing that would make a viewer smile. Examples:
   - A product's headline feature being its biggest flaw (e.g., "disable the AI to save battery")
   - Unintentionally comedic reviewer phrasing or absurd situations
   - Dark humor about product failures
   Do NOT force humor — only tag quotes that are naturally amusing.

OUTPUT JSON STRUCTURE (strictly follow schema):
Your response will be parsed via strict generic JSON schema (ThemeInsightsSchema).
For each evidence_quote, specify: review_id, text, is_humorous, selection_reason

Reviews for theme "{theme}" (sorted by priority, highest first):
{reviews}
"""

async def get_theme_insights_from_llm(
    theme: str,
    group: pd.DataFrame,
    helpful_map: Dict[str, int],
    rating_map: Dict[str, Optional[int]],
    media_index: Dict[str, List[Dict[str, Any]]],
    client: genai.Client,
    model_id: str,
    semaphore: asyncio.Semaphore,
    is_trending: bool = False,
    recent_mention_count: int = 0,
    recent_period_text: str = "",
) -> Dict:
    """전체 리뷰를 텍스트 디테일 순으로 정렬해 LLM에 전달, Pydantic 기반 인사이트 추출."""

    # 우선순위: 텍스트 길이(구체성 척도) -> helpful_count -> 미디어 포함 여부(가장 후순위)
    group_sorted = group.copy()
    group_sorted["helpful_count"] = group_sorted["review_id"].map(
        lambda rid: helpful_map.get(str(rid), 0)
    )
    group_sorted["has_media"] = group_sorted["review_id"].map(
        lambda rid: str(rid) in media_index
    )
    group_sorted["text_length"] = group_sorted["evidence_quote"].astype(str).apply(len)
    
    group_sorted = group_sorted.sort_values(
        by=["text_length", "helpful_count", "has_media"],
        ascending=[False, False, False],
    )

    # 리뷰 텍스트 포맷 구성
    docs = []
    for _, r in group_sorted.iterrows():
        quote = str(r.get("evidence_quote", "") or "").strip()
        if not quote:
            continue
        rid = str(r.get("review_id", ""))
        stars = rating_map.get(rid)
        star_str = str(stars) if stars is not None else "N/A"
        helpful = helpful_map.get(rid, 0)
        has_images = rid in media_index
        docs.append(
            f'- [ID: {rid}] | Stars: {star_str} | Helpful: {helpful} | Has_Images: {has_images} | Text: "{quote}"'
        )

    if not docs:
        return {
            "root_cause": "No data", "affected_user_profile": "No data",
            "temporal_pattern": "No data", "purchase_guidance": "No data",
            "evidence_quotes": [],
        }

    prompt = _THEME_SUMMARIZER_PROMPT.format(
        theme=theme, reviews="\n".join(docs),
        is_trending=is_trending,
        recent_mention_count=recent_mention_count,
        recent_period_text=recent_period_text,
    )
    
    async with semaphore:
        for attempt in range(1, 4):
            try:
                response = await client.aio.models.generate_content(
                    model=model_id, 
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ThemeInsightsSchema,
                        temperature=0.1,
                    )
                )
                
                parsed = getattr(response, "parsed", None)
                if parsed:
                    return parsed.model_dump()
                else:
                    text = response.text.replace("```json", "").replace("```", "").strip()
                    result = json.loads(text)
                    if "evidence_quotes" not in result:
                        result["evidence_quotes"] = []
                    return result
            except Exception as e:
                logger.warning(f"  -> Attempt {attempt} Error getting LLM insight for '{theme}': {e}")
                await asyncio.sleep(attempt * 3)

        logger.error(f"  -> Final failure getting LLM insight for '{theme}'")
        return {
            "root_cause": "",
            "affected_user_profile": "",
            "temporal_pattern": "",
            "purchase_guidance": "",
            "evidence_quotes": [],
        }


# ── Product Data ───────────────────────────────────────────────────────────────

def _convert_rating_dist(dist_dict: dict) -> dict:
    return {k[0]: v.get("count", 0) for k, v in dist_dict.items() if k.endswith("star")}


def generate_product_data_dict(
    df: pd.DataFrame,
    top_themes: List[str],
    product_json_path: str,
) -> Dict[str, Any]:
    """script_agent를 위한 product_data 딕셔너리를 생성."""
    prod: Dict[str, Any] = {}
    json_path = Path(product_json_path)
    if json_path.exists():
        with json_path.open("r", encoding="utf-8") as f:
            prod = json.load(f)

    return {
        "product_name": prod.get("product_title", "Unknown Product"),
        # 카테고리명 — cross_product_analyzer.py가 summary.json만으로 카테고리를 식별할 수 있도록 전달
        "product_category": prod.get("product_category", ""),
        "all_time_rating_count": int(prod.get("all_time_rating_count", 0)),
        "all_time_rating_avg": prod.get("all_time_rating_avg", 0.0),
        "all_time_rating_distribution": _convert_rating_dist(prod.get("all_time_rating_distribution", {})),
        "recent_review_count": int(prod.get("recent_review_count", 0)),
        "recent_review_rating_avg": prod.get("recent_review_rating_avg", 0.0),
        "recent_review_rating_distribution": _convert_rating_dist(prod.get("recent_rating_distribution", {})),
        "recent_period_text": prod.get("recent_period_text", ""),
        "recent_days": int(prod.get("recent_days", 0)),
        "population_gap": prod.get("rating_drop", 0.0),
        "population_gap_percent": prod.get("rating_drop_percent", 0),
        "reviews_analyzed_count": prod.get("reviews_analyzed_count", len(df)),
        "sold_last_month": prod.get("sold_last_month_text", ""),
        "top_praised_themes": top_themes,
    }


def compute_top_themes(df: pd.DataFrame, n: int = 3) -> List[str]:
    """Return the top N most positively-mentioned canonical themes.
    Uses a Positive Density score: (pos_count^2 / total_count) to prevent volume bias
    and guarantee at least 1 theme if any positive reviews exist.
    """
    if "canonical_theme" not in df.columns:
        return []
    stats = []
    for theme_name, group in df.groupby("canonical_theme"):
        if not isinstance(theme_name, str) or not theme_name.strip():
            continue
            
        total_count = len(group)
        pos_count = len(group[group["sentiment"] == "Positive"])
        
        if total_count == 0 or pos_count == 0:
            continue
            
        # 밀도 점수 계산: (긍정 개수 제곱 / 전체 개수)
        density_score = (pos_count ** 2) / total_count
        stats.append((theme_name, density_score))
            
    # 밀도 점수 내림차순 정렬
    stats.sort(key=lambda x: x[1], reverse=True)
    return [t[0] for t in stats[:n]]


# ── Theme Analysis ─────────────────────────────────────────────────────────────

async def generate_theme_analysis_list(
    df: pd.DataFrame,
    media_index: Dict[str, List[Dict]],
    date_map: Dict[str, Optional[str]],
    rating_map: Dict[str, Optional[int]],
    helpful_map: Dict[str, int],
    client: genai.Client,
    model_id: str,
    recent_start_date: Optional[str] = None,
    recent_period_text: str = "",
) -> List[Dict[str, Any]]:
    """테마별 비동기 LLM 통합 호출로 인사이트와 evidence_quotes 3개를 생성한다.
    최근 리뷰 비중이 급상승한 테마를 감지하여 is_trending 플래그를 부여한다."""
    total_reviews = len(df)
    if "canonical_theme" not in df.columns:
        logger.error("'canonical_theme' column not found. Did review_analyzer finish?")
        return []

    themes_df = df[df["canonical_theme"].notna() & (df["canonical_theme"] != "")]
    # LLM 환각 방지: 실제 존재하는 review_id 셋
    valid_rids = set(df["review_id"].astype(str).tolist())

    # ── 최근 리뷰 필터링 ──────────────────────────────────────────────────────
    recent_rids: set = set()
    if recent_start_date:
        for rid, d in date_map.items():
            if d and d >= recent_start_date:
                recent_rids.add(rid)
        print(f" -> 최근 기간({recent_start_date}~) 리뷰 수: {len(recent_rids)}")
    total_recent = len(recent_rids) if recent_rids else 0

    # ── 테마별 서사적 중요도 점수 계산 (Narrative Score) ─────────────────────
    theme_scores = []
    for theme_name, group in themes_df.groupby("canonical_theme"):
        unique_rids = group["review_id"].unique()
        
        # 1. Base Impact Score (기본 언급량 + 추천수)
        impact_score = sum(math.log(1 + helpful_map.get(str(rid), 0)) for rid in unique_rids)
        base_score = len(group) + impact_score

        # 2. Polarization Weight (양극단화 가중치)
        # 평점 정보가 있으면 평균 계산, 없으면 긍정/부정 비율로 추정
        ratings = [rating_map.get(str(rid)) for rid in unique_rids if rating_map.get(str(rid)) is not None]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
        else:
            pos_cnt = len(group[group["sentiment"] == "Positive"])
            neg_cnt = len(group[group["sentiment"] == "Negative"])
            neu_cnt = len(group[group["sentiment"] == "Neutral"])
            total_sent = max(1, len(group))
            avg_rating = ((pos_cnt * 5) + (neu_cnt * 3) + (neg_cnt * 1)) / total_sent

        # 3.0(무난함)에서 멀어질수록 최대 2.0배 증폭
        distance_from_neutral = abs(avg_rating - 3.0) 
        
        # [Fix] 소규모 표본 극단화(노이즈) 방지 패널티
        if len(group) < MIN_RECENT_MENTIONS:
            distance_from_neutral *= 0.5
            
        polarization_multiplier = 1.0 + (distance_from_neutral / 2.0)

        # 3. Trending Velocity (최근 가속도)
        recent_count = 0
        if recent_rids:
            recent_count = int(group[group["review_id"].astype(str).isin(recent_rids)].shape[0])

        is_trending = False
        velocity_bonus = 0.0
        if total_recent > 0 and total_reviews > 0 and recent_count > 0:
            recent_ratio = recent_count / total_recent
            alltime_ratio = len(group) / total_reviews
            if alltime_ratio > 0:
                velocity = recent_ratio / alltime_ratio
                if velocity >= TRENDING_RATIO_THRESHOLD and recent_count >= MIN_RECENT_MENTIONS:
                    is_trending = True
                    velocity_bonus = velocity

        # 4. Final Narrative Score
        final_score = (base_score * polarization_multiplier) + (velocity_bonus * 5)

        theme_scores.append({
            "theme_name": theme_name,
            "group": group,
            "alltime_score": final_score,
            "recent_mention_count": recent_count,
            "is_trending": is_trending,
            "avg_rating": avg_rating,
        })

    # ── 동적 컷오프(Dynamic Elbow) 기반 상위 테마 선정 ───────────────────────
    theme_scores.sort(key=lambda x: x["alltime_score"], reverse=True)
    
    MIN_THEMES = 5
    MAX_THEMES = 12
    DROP_RATIO_THRESHOLD = 0.6  # 점수가 직전 등수 대비 40% 이상 폭락하면 자름
    
    cutoff_index = len(theme_scores)
    for i in range(MIN_THEMES, min(len(theme_scores), MAX_THEMES)):
        current_score = theme_scores[i]["alltime_score"]
        prev_score = theme_scores[i-1]["alltime_score"]
        if prev_score > 0 and (current_score / prev_score) < DROP_RATIO_THRESHOLD:
            logger.info(f"🔪 Dynamic Cut-off 발동: {i}위부터 낙폭({current_score/prev_score:.2f}) 컷오프")
            cutoff_index = i
            break
            
    cutoff_index = min(max(cutoff_index, MIN_THEMES), MAX_THEMES)
    top_themes = theme_scores[:cutoff_index]
    top_names = {t["theme_name"] for t in top_themes}

    # 5. 트렌딩 테마 강제 삽입
    for t in theme_scores[cutoff_index:]:
        if t["is_trending"] and t["theme_name"] not in top_names:
            top_themes.append(t)
            top_names.add(t["theme_name"])
            logger.info(f"📈 트렌딩 테마 강제 포함: {t['theme_name']} (최근 {t['recent_mention_count']}건)")

    # 6. Positive Anchor 보장 (평균 평점 4.0 이상 테마 최소 2개 확보)
    positive_themes_in_top = sum(1 for t in top_themes if t["avg_rating"] >= 4.0)
    needed_positive = max(0, 2 - positive_themes_in_top)
    
    if needed_positive > 0:
        unused_positives = [t for t in theme_scores[cutoff_index:] if t["avg_rating"] >= 4.0 and t["theme_name"] not in top_names]
        unused_positives.sort(key=lambda x: x["alltime_score"], reverse=True)
        for t in unused_positives[:needed_positive]:
            top_themes.append(t)
            top_names.add(t["theme_name"])
            logger.info(f"✨ 긍정 앵커 강제 포함: {t['theme_name']} (평점: {t['avg_rating']:.2f})")

    top_themes_list = top_themes
    
    # ── 테마별 인사이트 비동기 병렬 처리 ──────────────────────────────────────────
    logger.info(f"Generating insights for {len(top_themes_list)} themes (async parallel)...")
    
    semaphore = asyncio.Semaphore(10)
    
    async def process_item(item):
        theme_name = item["theme_name"]
        group = item["group"]
        is_trending = item["is_trending"]
        recent_mention_count = item["recent_mention_count"]

        # LLM 호출
        result = await get_theme_insights_from_llm(
            theme_name, group, helpful_map, rating_map, media_index,
            client, model_id, semaphore,
            is_trending=is_trending,
            recent_mention_count=recent_mention_count,
            recent_period_text=recent_period_text,
        )

        mention_count = len(group)
        mention_percent = round((mention_count / total_reviews) * 100, 1) if total_reviews else 0
        sc = group["sentiment"].value_counts()
        sent_dist = {
            "positive": int(sc.get("Positive", 0)),
            "negative": int(sc.get("Negative", 0)),
            "neutral": int(sc.get("Neutral", 0)),
        }

        # evidence_quotes 가공
        llm_quotes = result.get("evidence_quotes", [])
        evidence_quotes = []
        seen_rids: set = set()
        for eq in llm_quotes:
            rid = str(eq.get("review_id", "")).strip()
            text = str(eq.get("text", "")).strip()

            if not rid or rid not in valid_rids or rid in seen_rids:
                continue
            seen_rids.add(rid)

            has_media = rid in media_index
            media_info = []
            if has_media:
                for m in media_index[rid]:
                    media_info.append({
                        "path": m["path"],
                        "broll_description": m["broll_description"],
                        "visual_evidence": m["visual_evidence"],
                        "shot_type": m["shot_type"],
                        "is_funny": m["is_funny"],
                        "text_in_image": m.get("text_in_image", ""),
                        "face_detected": False # Placeholder
                    })

            # 원본 데이터에서 텍스트와 감정/평점 정보를 정확히 가져옴 (Verbatim Enforcement)
            row_match = group[group["review_id"].astype(str) == rid]
            if row_match.empty:
                # valid_rids 체크를 거치므로 여기 올 가능성은 희박함
                actual_text = text
                sentiment = "Neutral"
            else:
                actual_text = str(row_match["evidence_quote"].iloc[0]).strip()
                sentiment = str(row_match["sentiment"].iloc[0])
            
            star_rating = rating_map.get(rid)
            if star_rating is None:
                star_rating = 5 if sentiment == "Positive" else (1 if sentiment == "Negative" else 3)

            evidence_quotes.append({
                "text": actual_text,
                "sentiment": sentiment,
                "star_rating": int(star_rating),
                "review_id": rid,
                "review_date": date_map.get(rid),
                "helpful_count": helpful_map.get(rid, 0),
                "is_humorous": bool(eq.get("is_humorous", False)),
                "selection_reason": str(eq.get("selection_reason", "anchor")),
                "has_media": has_media,
                "media_info": media_info,
            })

        return {
            "theme_name": str(theme_name),
            "mention_count": int(mention_count),
            "mention_percent": float(mention_percent),
            "sentiment_distribution": sent_dist,
            "is_trending": is_trending,
            "recent_mention_count": int(recent_mention_count),
            "root_cause": result.get("root_cause", ""),
            "affected_user_profile": result.get("affected_user_profile", ""),
            "temporal_pattern": result.get("temporal_pattern", ""),
            "purchase_guidance": result.get("purchase_guidance", ""),
            "evidence_quotes": evidence_quotes,
        }

    tasks = [process_item(item) for item in top_themes_list]
    results = await asyncio.gather(*tasks)

    return results

async def main():
    parser = argparse.ArgumentParser(description="ReviewLens: Generate Hierarchical Summary JSON")
    parser.add_argument("--input-dir", type=str, default="one_product")
    parser.add_argument("--output-dir", type=str, default="datas")
    args = parser.parse_args()

    client = genai.Client()
    model_id = MODELS.get("analysis_pro", "gemini-3.1-pro-preview")

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    extracted_csv = output_dir / "buying_guide_extracted.csv"
    cleaned_csv = input_dir / "cleaned_reviews.csv"
    product_json = input_dir / "product.json"

    if not extracted_csv.exists():
        logger.error(f"{extracted_csv} not found. Please run absa.py first.")
        sys.exit(1)

    df = pd.read_csv(extracted_csv)

    media_index = build_media_index(
        str(output_dir / "movies_meta" / "*_meta.json"),
        str(output_dir / "photos_meta" / "*_meta.json"),
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )

    date_map, rating_map, helpful_map = build_review_lookup(str(cleaned_csv))

    logger.info("Computing top themes...")
    top_themes = compute_top_themes(df, n=3)
    
    logger.info("Generating product data dict...")
    product_data = generate_product_data_dict(df, top_themes, str(product_json))

    # product.json에서 최근 기간 정보 로드
    prod_meta: Dict[str, Any] = {}
    if product_json.exists():
        with product_json.open("r", encoding="utf-8") as f:
            prod_meta = json.load(f)
    
    recent_start_date = prod_meta.get("recent_start_date")
    recent_period_text = prod_meta.get("recent_period_text", "")

    logger.info("Generating theme analysis list (LLM 통합 호출 — 비동기 병렬 처리)...")
    theme_analysis = await generate_theme_analysis_list(
        df=df,
        media_index=media_index,
        date_map=date_map,
        rating_map=rating_map,
        helpful_map=helpful_map,
        client=client,
        model_id=model_id,
        recent_start_date=recent_start_date,
        recent_period_text=recent_period_text,
    )

    final_output = {
        "product_data": product_data,
        "themes": theme_analysis
    }

    out_path = output_dir / "summary.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Hierarchical summary saved to {out_path}")

    # Agent별 필터링된 summary 파일 생성
    original_size = out_path.stat().st_size
    logger.info(f"Generating agent-filtered summary files (source: {original_size:,} bytes)...")
    for profile_name, profile_def in FILTER_PROFILES.items():
        filtered = apply_filter(final_output, profile_def)
        filter_path = output_dir / f"summary_{profile_name}.json"
        with filter_path.open("w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        filtered_size = filter_path.stat().st_size
        reduction = round(100 * (1 - filtered_size / original_size), 1)
        logger.info(f"  ✅ {filter_path.name}: {filtered_size:,} bytes ({reduction}% reduction)")

if __name__ == "__main__":
    asyncio.run(main())
