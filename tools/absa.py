"""
Review Analysis CLI Tool — ABSA extraction + hybrid clustering.
Migrated from pipeline/agents/review_analysis.py and pipeline/skills/absa.py.
"""
import argparse
import asyncio
import json
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from typing import Dict, List, Literal, Optional

import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

from config import MODELS, MAX_CONCURRENT, MAX_RETRIES


# ── Pydantic Models ────────────────────────────────────────────────────────────

# 원본 스키마 (내부 저장/후속 파이프라인용)
class ReviewFeature(BaseModel):
    review_id: str = Field(..., description="The exact ID from input data.")
    is_helpful_for_guide: bool = Field(
        ..., description="True if the review contains specific, actionable facts."
    )
    core_aspect: Optional[str] = Field(None)
    sentiment: Optional[Literal["Positive", "Negative", "Neutral"]] = Field(None)
    time_context: Optional[str] = Field(None)
    user_profile: Optional[str] = Field(None)
    compared_to: Optional[str] = Field(None)
    evidence_quote: Optional[str] = Field(None)


# 압축 스키마 (API 응답 토큰 절약용 — 키 이름을 1~2글자로 압축)
# 오브젝트당 ~84자(~21토큰) 절약 × 30~40개 = 630~840 토큰 절감
class CompactReviewFeature(BaseModel):
    rid: str = Field(..., description="review_id")
    h: bool = Field(..., description="is_helpful_for_guide")
    a: Optional[str] = Field(None, description="core_aspect")
    s: Optional[Literal["Positive", "Negative", "Neutral"]] = Field(None, description="sentiment")
    tc: Optional[str] = Field(None, description="time_context")
    up: Optional[str] = Field(None, description="user_profile")
    ct: Optional[str] = Field(None, description="compared_to")
    eq: Optional[str] = Field(None, description="evidence_quote")


class CompactMapResponse(BaseModel):
    r: List[CompactReviewFeature]


def _compact_to_full(c: CompactReviewFeature) -> ReviewFeature:
    """압축 스키마 → 원본 스키마 변환 (API 응답 후처리)."""
    return ReviewFeature(
        review_id=c.rid,
        is_helpful_for_guide=c.h,
        core_aspect=c.a,
        sentiment=c.s,
        time_context=c.tc,
        user_profile=c.up,
        compared_to=c.ct,
        evidence_quote=c.eq,
    )


def _compact_dict_to_full(d: dict) -> dict:
    """압축 키 딕셔너리 → 원본 키 딕셔너리 변환 (JSON repair 후처리용)."""
    KEY_MAP = {"rid": "review_id", "h": "is_helpful_for_guide", "a": "core_aspect",
               "s": "sentiment", "tc": "time_context", "up": "user_profile",
               "ct": "compared_to", "eq": "evidence_quote"}
    return {KEY_MAP.get(k, k): v for k, v in d.items()}


# 이전 MapResponse 호환 (기존 캐시 로딩 등에서 사용)
class MapResponse(BaseModel):
    results: List[ReviewFeature]


class ClusterNamingItem(BaseModel):
    cluster_id: int
    canonical_name: str


class ClusterNamingResponse(BaseModel):
    names: List[ClusterNamingItem]


# ── Map Prompt ─────────────────────────────────────────────────────────────────
# 프롬프트에서 압축 키 이름(rid, h, a, s, tc, up, ct, eq)을 사용하여
# 모델 출력 토큰을 절약하고, 파싱 후 원래 키명으로 복원한다.

_MAP_PROMPT_TEMPLATE = """You are an expert Aspect-Based Sentiment Analysis (ABSA) data extraction algorithm analyzing reviews for: [{product_name}].
Your task is to analyze a batch of Amazon product reviews and deconstruct them into granular, actionable data points. 
# CORE RULES (ABSOLUTE)
1. **Multi-Aspect Extraction**: A single review often discusses multiple features. You MUST create a separate JSON object for EACH distinct aspect mentioned.
2. **Strict Noise Filtering & Negative Insight**: Set `h: false` unless the review contains a SPECIFIC, VERIFIABLE claim.
   - **Filter Noise**: Pure sentiment without detail (e.g., "terrible", "don't buy", "regret this", "love it", "works great") MUST be filtered ❌.
   - **Extract Evidence**: Prioritize specific failure modes, design flaws, or performance limitations (e.g., "the plastic clip snapped under light pressure", "gets uncomfortably hot after 20 mins of use") ✅.
   - A review is ONLY guide-worthy if it describes a specific feature behavior, a concrete failure mode, a measurable outcome, or a direct comparison.
3. **English Only (Verbatim)**: All extractions MUST be in the exact original English. Do not translate or summarize.
4. **Zero Omission**: Process and return every single `review_id`. Return noise reviews with `h: false`.
5. **JSON Only (Strict)**: Return ONLY a valid JSON object matching the schema. No markdown code blocks, no preamble.
# OUTPUT KEYS (compact — use these exact short names to save tokens)
- **rid**: review_id (copy exactly from input)
- **h**: is_helpful_for_guide (true/false)
- **a**: core_aspect — noun phrase, lowercase, 2-4 words. (e.g., "battery longevity", "noise cancellation")
- **s**: sentiment — Positive | Negative | Neutral
- **tc**: time_context — ONLY temporal/duration info. "after 3 months" ✅ | "during a workout" ❌ (that is up)
- **up**: user_profile — ONLY user traits or usage environment. "frequent traveler" ✅ | "after two weeks" ❌ (that is tc)
- **ct**: compared_to — ONLY a specific brand/model name. "Logitech MX Master 3" ✅ | "the older model" ❌
- **eq**: evidence_quote — verbatim sentence(s) from the review.
   - For negative reviews, focus on the "WHY" (objective cause) not the "WHAT" (feeling).
   - Extract "The power button requires multiple presses" ✅ not "The button is annoying" ❌.
   - Copy exact original text. null if no such sentence exists.
# INPUT
{reviews_json}
"""


# ── JSON 잘림 복구 (Truncated JSON Repair) ─────────────────────────────────────

def _repair_truncated_json(raw: str) -> list:
    """max_output_tokens에 의해 잘린 JSON 응답에서 완전한 항목만 추출하는 복구 함수.
    
    전략:
    1. 먼저 원본 그대로 파싱 시도 (정상 응답이면 바로 반환)
    2. 실패 시 마지막 완전한 '}' 블록까지 잘라내고 배열/객체를 닫아서 재파싱
    3. 그래도 실패하면 빈 리스트 반환 (상위 로직이 청크 분할 처리)
    """
    raw = raw.strip()
    
    # 1차: 원본 그대로 파싱 시도
    try:
        parsed = json.loads(raw)
        # 압축 키("r") 또는 원본 키("results") 모두 대응
        if isinstance(parsed, dict):
            if "r" in parsed:
                return parsed["r"]
            if "results" in parsed:
                return parsed["results"]
        elif isinstance(parsed, list):
            return parsed
        return [parsed]
    except json.JSONDecodeError:
        pass
    
    # 2차: 잘린 JSON에서 마지막 완전한 객체('}')까지만 살리기
    last_complete = raw.rfind("}")
    if last_complete == -1:
        return []
    
    truncated = raw[:last_complete + 1]
    
    # 열린 대괄호/중괄호 카운트로 닫기
    open_braces = truncated.count("{") - truncated.count("}")
    open_brackets = truncated.count("[") - truncated.count("]")
    
    # 잘린 부분 뒤에 남은 쉼표/공백 제거 후 닫기
    repaired = truncated.rstrip(", \t\n\r")
    repaired += "]" * max(0, open_brackets)
    repaired += "}" * max(0, open_braces)
    
    try:
        parsed = json.loads(repaired)
        # 압축 키("r") 또는 원본 키("results") 모두 대응
        if isinstance(parsed, dict):
            if "r" in parsed:
                items = parsed["r"]
            elif "results" in parsed:
                items = parsed["results"]
            else:
                return []
        elif isinstance(parsed, list):
            items = parsed
        else:
            return []
        
        # 복구 성공 시 로그 출력
        print(f"     🔧 [JSON 복구] 잘린 응답에서 {len(items)}개 항목 구출 성공", flush=True)
        return items
    except json.JSONDecodeError:
        return []


# ── Map ────────────────────────────────────────────────────────────────────────

async def map_reviews_with_retry(
    chunk_df: pd.DataFrame,
    product_name: str,
    client: genai.Client,
    config: dict,
) -> List[ReviewFeature]:
    """Map stage: extract ABSA features from a review batch. Auto-retries with adaptive chunk halving on failure."""
    model_id = config.get("model_id", "gemini-3.1-flash-lite-preview")
    temperature = config.get("temperature", 0.1)
    max_retries = config.get("max_retries", 3)  # 분할 리트라이가 있으므로 최대 시도는 3으로 조정
    max_output_tokens = config.get("max_output_tokens", 65536)

    all_extracted: List[ReviewFeature] = []
    
    # 큐 방식을 이용하여 실패 시 청크를 쪼개서 재시도
    queue = [chunk_df.copy()]
    
    while queue:
        current_chunk = queue.pop(0)
        if current_chunk.empty:
            continue
            
        target_ids = set(current_chunk["review_id"].tolist())
        success = False

        for attempt in range(1, max_retries + 1):
            print(f"   ↳ [시도 {attempt}] {len(target_ids)}개 리뷰 분석 요청 중...", flush=True)

            reviews_json = json.dumps(
                [{"review_id": str(r["review_id"]), "review": str(r["comment"])}
                 for _, r in current_chunk.iterrows()],
                ensure_ascii=False,
            )
            prompt = _MAP_PROMPT_TEMPLATE.format(product_name=product_name, reviews_json=reviews_json)

            try:
                print("     [API] Gemini 모델 호출 시도 중...", flush=True)
                # 압축 스키마(CompactMapResponse)로 API 호출 → 출력 토큰 절약
                response = await client.aio.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=CompactMapResponse,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                )
                print("     [API] 모델 응답 수신 완료.", flush=True)

                parsed = getattr(response, "parsed", None)
                if parsed and hasattr(parsed, "r"):
                    # SDK가 압축 스키마로 안전하게 파싱한 경우 → 원본으로 변환
                    results = [_compact_to_full(c) for c in parsed.r]
                elif parsed and hasattr(parsed, "results"):
                    # 혹시 원본 스키마로 파싱된 경우 (기존 호환)
                    results = parsed.results
                else:
                    # SDK 파싱 실패 시 → 잘림 복구 포함 텍스트 폴백
                    raw = getattr(response, "text", "")
                    if not raw:
                        raise ValueError("Empty response text")
                    
                    # _repair_truncated_json가 정상/잘린 JSON 모두 처리
                    items = _repair_truncated_json(raw)
                    if not items:
                        raise ValueError("JSON repair failed — no salvageable items")

                    # 압축 키 → 원본 키 변환 후 ReviewFeature 생성
                    results = [ReviewFeature(**_compact_dict_to_full(x)) for x in items]

                all_extracted.extend(results)
                success = True
                await asyncio.sleep(1)
                break

            except Exception as e:
                print(f"❌ [Map 에러] API 호출 실패: {e}", flush=True)
                await asyncio.sleep(3 * attempt)

        if not success:
            if len(current_chunk) > 1:
                mid = len(current_chunk) // 2
                print(f"   ✂️ [청크 분할] {len(current_chunk)}개 리뷰 집합 처리에 실패하여 {mid}개와 {len(current_chunk)-mid}개로 나누어 재시도합니다.", flush=True)
                # 앞부분과 뒷부분으로 쪼개서 큐의 맨 앞에 삽입 (DFS처럼 처리)
                queue.insert(0, current_chunk.iloc[mid:])
                queue.insert(0, current_chunk.iloc[:mid])
            else:
                failed_id = current_chunk["review_id"].iloc[0]
                print(f"🚨 [치명적 경고] 단일 리뷰 처리(ID: {failed_id}) 최종 실패. 제외하고 무시합니다.", flush=True)

    return all_extracted


# ── Reduce ─────────────────────────────────────────────────────────────────────

async def reduce_keywords_hybrid(
    unique_keywords: List[str],
    product_name: str,
    client: genai.Client,
    config: dict,
) -> Dict[str, str]:
    """Hybrid Reduce: embedding clustering (Step 1) + LLM naming (Step 2)."""
    if not unique_keywords:
        return {}
    if len(unique_keywords) == 1:
        names = await _name_clusters_with_llm({0: unique_keywords}, product_name, client, config)
        return {unique_keywords[0]: names.get(0, unique_keywords[0])}

    print("   📐 [Reduce Step 1] 임베딩 클러스터링 시작...", flush=True)
    embed_model = SentenceTransformer(config.get("embedding_model", "all-MiniLM-L6-v2"))
    embeddings = embed_model.encode(unique_keywords, normalize_embeddings=True)

    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=config.get("cluster_distance_threshold", 0.35), # 0.7 보다 더 촘촘하게 하는것이 다음단계 LLM이 더 잘 분류함
        metric="cosine",
        linkage="average",
    )
    labels = clustering.fit_predict(embeddings)

    clusters: Dict[int, List[str]] = {}
    for kw, label in zip(unique_keywords, labels):
        clusters.setdefault(int(label), []).append(kw)

    print(f"   ✅ {len(unique_keywords)}개 키워드 → {len(clusters)}개 클러스터로 그룹핑 완료.", flush=True)
    for cid, members in sorted(clusters.items()):
        print(f"      Cluster {cid}: {members}", flush=True)

    cluster_names = await _name_clusters_with_llm(clusters, product_name, client, config)

    theme_map: Dict[str, str] = {}
    for label, members in clusters.items():
        canonical = cluster_names.get(label, members[0])
        for kw in members:
            theme_map[kw] = canonical

    return theme_map


async def _name_clusters_with_llm(
    clusters: Dict[int, List[str]],
    product_name: str,
    client: genai.Client,
    config: dict,
) -> Dict[int, str]:
    """Assign professional canonical names to clusters via LLM. Includes retry logic."""
    model_id = config.get("model_id", "gemini-3.1-flash-lite-preview")
    temperature = config.get("temperature", 0.1)
    max_retries = config.get("max_retries", 5)

    desc = "\n".join(
        f"Cluster {cid}: [{', '.join(members)}]"
        for cid, members in sorted(clusters.items())
    )
    prompt = f"""You are the Lead Editor of the Buying Guide for [{product_name}].
Below are clusters of related keywords extracted from Amazon reviews.
For each cluster, provide ONE clean, professional specification category name in English.

The name should be:
- Specific to the product domain (not generic like "Quality" or "Performance")
- A real buying criterion that consumers would recognize
- Concise (2-4 words)

{desc}
"""

    for attempt in range(1, max_retries + 1):
        try:
            print(f"   🏷️ [Reduce Step 2] 클러스터 네이밍 LLM 호출 (시도 {attempt})...", flush=True)
            response = await client.aio.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClusterNamingResponse,
                    temperature=temperature,
                ),
            )
            print("   ✅ 클러스터 네이밍 응답 수신 완료.", flush=True)
            if getattr(response, "parsed", None) is None or not hasattr(response.parsed, "names"):
                await asyncio.sleep(2 * attempt)
                continue
            return {item.cluster_id: item.canonical_name for item in response.parsed.names}
        except Exception as e:
            print(f"   ❌ [Reduce 에러] 네이밍 API 호출 실패: {e}", flush=True)
            await asyncio.sleep(3 * attempt)

    print("   🚨 클러스터 네이밍 실패. 폴백: 첫 번째 키워드를 대표명으로 사용합니다.", flush=True)
    return {}


# ── Helpfulness Validation ─────────────────────────────────────────────────────

def validate_helpfulness_filter(
    mapped_df: pd.DataFrame,
    guide_df: pd.DataFrame,
    config: dict,
) -> None:
    """Statistical guard: detects abnormal is_helpful_for_guide ratios."""
    total = len(mapped_df)
    helpful = len(guide_df)
    ratio = helpful / total if total > 0 else 0

    print(f"\n📊 [is_helpful_for_guide 검증]", flush=True)
    print(f"   전체 추출 속성: {total}개 | 유용: {helpful}개 ({ratio:.1%}) | 노이즈: {total - helpful}개", flush=True)

    warn_low = config.get("helpfulness_warn_low", 0.10)
    warn_high = config.get("helpfulness_warn_high", 0.95)

    if ratio < warn_low:
        print(f"   ⚠️ [경고] 유용 비율 {ratio:.1%} — 비정상적으로 낮음 (LLM 과필터링 의심)", flush=True)
    elif ratio > warn_high:
        print(f"   ⚠️ [경고] 유용 비율 {ratio:.1%} — 비정상적으로 높음 (노이즈 필터링 미작동 의심)", flush=True)
    else:
        print(f"   ✅ 유용 비율 {ratio:.1%} — 정상 범위입니다.", flush=True)

    noise_df = mapped_df[mapped_df["is_helpful_for_guide"] == False]
    if not noise_df.empty:
        sample = noise_df.sample(n=min(3, len(noise_df)), random_state=42)
        print(f"\n   🔍 [노이즈 샘플 {len(sample)}개] (수동 검증용):", flush=True)
        for _, row in sample.iterrows():
            print(f"      - ID: {row.get('review_id', 'N/A')} | Quote: {str(row.get('evidence_quote', ''))[:80]}", flush=True)


# ── CLI Orchestration (from ReviewAnalysisAgent) ────────────────────────────────

async def _process_chunk(
    idx: int,
    chunk: pd.DataFrame,
    product_name: str,
    client: genai.Client,
    semaphore: asyncio.Semaphore,
    intermediate_dir: str,
    total: int,
    config: dict
) -> List[ReviewFeature]:
    inter_path = os.path.join(intermediate_dir, f"chunk_{idx:04d}.json")

    if os.path.exists(inter_path):
        print(f"   ♻️ Chunk {idx + 1}/{total} — 캐시 발견, 스킵", flush=True)
        with open(inter_path, "r", encoding="utf-8") as f:
            return [ReviewFeature(**x) for x in json.load(f)]

    async with semaphore:
        print(f"▶️ Chunk {idx + 1}/{total} 시작...", flush=True)
        result = await map_reviews_with_retry(chunk, product_name, client, config)
        print(f"✅ Chunk {idx + 1}/{total} 완료 — {len(result)}개 피처", flush=True)

    os.makedirs(intermediate_dir, exist_ok=True)
    with open(inter_path, "w", encoding="utf-8") as f:
        json.dump([x.model_dump() for x in result], f, ensure_ascii=False, indent=2)
    return result


async def run_analysis(input_dir: str, config: dict):
    """Orchestrates Map -> Filter -> Reduce -> Save pipeline."""
    app_logger = lambda msg: print(f"[Review Analysis] {msg}", flush=True)
    client = genai.Client()

    product_json_path = os.path.join(input_dir, "product.json")
    csv_path = os.path.join(input_dir, "cleaned_reviews.csv")
    output_dir = config.get("output_dir", "datas")
    intermediate_dir = config.get("intermediate_dir", os.path.join(output_dir, "intermediate"))

    try:
        with open(product_json_path, "r", encoding="utf-8") as f:
            product_name = json.load(f)["product_title"]
        app_logger(f"Product: [{product_name}]")
    except Exception as e:
        app_logger(f"ERROR: Cannot read product.json — {e}")
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=["comment"])
        app_logger(f"Loaded {len(df)} reviews from CSV.")
    except Exception as e:
        app_logger(f"ERROR: Cannot read {csv_path} — {e}")
        sys.exit(1)

    if not {"review_id", "comment"}.issubset(df.columns):
        app_logger("ERROR: CSV missing required columns: review_id, comment")
        sys.exit(1)

    chunk_size = config.get("chunk_size", 30)
    chunks = [df[i : i + chunk_size] for i in range(0, len(df), chunk_size)]
    app_logger(f"{len(df)} reviews → {len(chunks)} chunks (size={chunk_size})")

    app_logger("Starting Map stage (concurrent ABSA)...")
    semaphore = asyncio.Semaphore(config.get("max_concurrent_chunks", 5))
    tasks = [
        _process_chunk(idx, chunk, product_name, client, semaphore, intermediate_dir, len(chunks), config)
        for idx, chunk in enumerate(chunks)
    ]
    chunk_results = await asyncio.gather(*tasks)

    # Merge
    mapped_data = [item.model_dump() for sublist in chunk_results for item in sublist]
    os.makedirs(output_dir, exist_ok=True)
    mapped_path = os.path.join(output_dir, "mapped_data.json")
    with open(mapped_path, "w", encoding="utf-8") as f:
        json.dump(mapped_data, f, ensure_ascii=False, indent=2)
    mapped_df = pd.DataFrame(mapped_data)

    if mapped_df.empty:
        app_logger("WARNING: No data extracted. Check API responses.")
        sys.exit(1)

    # Filter
    guide_df = mapped_df[mapped_df["is_helpful_for_guide"] == True].copy()
    app_logger(f"Filter: {len(mapped_df)} aspects → {len(guide_df)} guide-worthy")
    validate_helpfulness_filter(mapped_df, guide_df, config)

    if guide_df.empty:
        app_logger("WARNING: No guide-worthy reviews found.")
        sys.exit(1)

    # Reduce (hybrid clustering)
    app_logger("Starting Reduce stage (embedding cluster + LLM naming)...")
    unique_kws = [
        kw for kw in guide_df["core_aspect"].unique()
        if kw and str(kw).lower() not in ("none", "null")
    ]
    theme_map = await reduce_keywords_hybrid(unique_kws, product_name, client, config)

    unmapped = [kw for kw in unique_kws if kw not in theme_map]
    if unmapped:
        app_logger(f"WARNING: {len(unmapped)} unmapped keywords: {unmapped[:5]}")

    # Save final CSV
    guide_df["canonical_theme"] = guide_df["core_aspect"].map(theme_map).fillna("Other (Unmapped)")
    final_df = guide_df[
        ["review_id", "canonical_theme", "core_aspect", "sentiment",
         "time_context", "user_profile", "compared_to", "evidence_quote"]
    ].sort_values(by=["canonical_theme", "review_id"])

    out_path = os.path.join(output_dir, "buying_guide_extracted.csv")
    final_df.to_csv(out_path, index=False, encoding="utf-8-sig")
    app_logger(f"Saved → {out_path} ({len(final_df)} rows)")

    # theme_analysis.json 생성 (Phase 3 broll_mapper 등에서 사용)
    theme_summary = []
    for theme, group in guide_df.groupby("canonical_theme"):
        quotes = group.replace({pd.NA: None, float('nan'): None}).to_dict(orient="records")
        theme_summary.append({
            "theme": theme,
            "count": len(group),
            "evidence_quotes": quotes
        })
    
    theme_analysis_path = os.path.join(output_dir, "theme_analysis.json")
    with open(theme_analysis_path, "w", encoding="utf-8") as f:
        json.dump({"themes": theme_summary}, f, ensure_ascii=False, indent=2)
    app_logger(f"Saved → {theme_analysis_path} ({len(theme_summary)} themes)")


def main():
    parser = argparse.ArgumentParser(description="ReviewLens: Run ABSA Extraction Pipeline")
    parser.add_argument("--input-dir", type=str, default="one_product", help="Input directory containing product.json and cleaned_reviews.csv")
    parser.add_argument("--output-dir", type=str, default="datas", help="Output directory for generated files")
    
    args = parser.parse_args()
    
    config = {
        "model_id": MODELS.get("analysis", "gemini-3-flash-preview"),
        "temperature": 0.1,
        "chunk_size": 15,  # 20→15: 압축 키 적용으로 토큰 절약되어 12에서 상향 조정
        "max_retries": MAX_RETRIES,
        "max_concurrent_chunks": MAX_CONCURRENT,
        "max_output_tokens": 65536,
        "embedding_model": "all-MiniLM-L6-v2",
        "cluster_distance_threshold": 0.35,
        "helpfulness_warn_low": 0.10,
        "helpfulness_warn_high": 0.95,
        "output_dir": args.output_dir,
    }
    
    asyncio.run(run_analysis(args.input_dir, config))

if __name__ == "__main__":
    main()
