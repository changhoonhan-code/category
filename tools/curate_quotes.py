"""
Curate Quotes — 자동화된 인용구 큐레이션 파이프라인.

Agent가 생성한 curation_brief.json을 기반으로:
  1. brief의 focal_products + theme으로 후보 인용구 검색 (결정론적)
  2. Gemini API로 최종 선택 + 하이라이트 추출 (LLM)
  3. brief의 headline/title을 보존하며 curate_patch.json 생성

사용법:
    python tools/curate_quotes.py
    python tools/curate_quotes.py --brief data/curation_brief.json --draft data/draft_script.json

curation_brief.json 스키마:
    {
      "scenes": [
        {
          "scene_id": "scene_04_active",
          "headline": "Active Noise Cancellation",
          "blocks": [
            {
              "block_id": "active_showdown",
              "title": "The 45-Point Gap",
              "focal_products": ["product_a", "product_c"],
              "theme": "Active Noise Cancellation"
            }
          ]
        }
      ]
    }
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from config import MODELS, DATAS_DIR
from search_quotes import search_quotes

# ── 로깅 설정 ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ── 기본 경로 ────────────────────────────────────────────────────────────────
DEFAULT_BRIEF = Path(DATAS_DIR) / "curation_brief.json"
DEFAULT_DRAFT = Path(DATAS_DIR) / "draft_script.json"
DEFAULT_OUTPUT = Path(DATAS_DIR) / "curate_patch.json"


# ══════════════════════════════════════════════════════════════════════════════
# Pydantic 스키마 — LLM 구조적 출력 (인용구 선택 + 하이라이트만)
# ══════════════════════════════════════════════════════════════════════════════

class SelectedQuote(BaseModel):
    """LLM이 선택한 인용구 1개."""
    review_id: str = Field(description="The review_id of the selected quote")
    product_id: str = Field(description="The product_id of the selected quote")
    star_rating: int = Field(description="The star rating of the review")
    selection_reason: str = Field(
        description="Why this quote was selected: 'anchor' (core evidence), "
                    "'contrast' (contradicts the dominant sentiment), "
                    "'hook' (attention-grabbing), or 'supplementary' (adds depth)"
    )
    highlight_phrase: str = Field(
        description="A verbatim 2-6 word substring from the quote text. "
                    "The video editor will display the full quote and use this "
                    "phrase to apply a highlighter effect. Must be an exact substring "
                    "of the original quote containing the strongest emotional punch."
    )


class QuoteSelection(BaseModel):
    """한 블록에 대한 LLM 인용구 선택 결과."""
    selected_quotes: List[SelectedQuote] = Field(
        description="3-7 quotes selected from the candidates. Prioritize: "
                    "vivid language, specific details, emotional weight, "
                    "and diversity of perspectives."
    )


# ══════════════════════════════════════════════════════════════════════════════
# LLM 프롬프트 — 인용구 선택 + 하이라이트 추출만 담당
# ══════════════════════════════════════════════════════════════════════════════

_SELECTION_PROMPT = """\
You are a video editor's assistant. Your job is to select the most impactful \
review quotes for on-screen display during a narration segment.

## BLOCK NARRATION
{narration}

## THEME: {theme}
## FOCAL PRODUCTS: {products}

## CANDIDATE QUOTES (from real buyer reviews)
{candidates_json}

## YOUR TASK

1. **Select 5-7 quotes** that best support or illustrate the narration above.
   - Prioritize quotes with vivid, specific language that would grab a viewer's eye.
   - Include a mix of sentiments if the narration discusses both positives and negatives.
   - Avoid generic or short quotes like "great product" — choose ones with memorable details.
   - Focus on quotes from the focal products listed above.

2. **For each selected quote**, extract a `highlight_phrase`:
   - Must be an EXACT VERBATIM substring of the original quote text (2-6 words).
   - The video editor will display the full quote on screen and use this phrase purely to apply a highlighter effect.
   - Pick the shortest, punchiest fragment containing the core emotion, shocking detail, or extreme descriptor.
   - Example: Instead of "the noise cancellation was garbage and didn't work", extract just "garbage" or "noise cancellation was garbage". Keep it extremely sharp.

3. **Assign a selection_reason** to each quote:
   - `anchor`: The primary piece of evidence for this block's claim.
   - `contrast`: Shows the opposite perspective.
   - `hook`: Attention-grabbing, dramatic, or surprising.
   - `supplementary`: Adds depth or a different angle.
"""


def select_quotes_for_block(
    block_id: str,
    narration: str,
    theme: str,
    focal_products: List[str],
    candidates: List[Dict[str, Any]],
    client: genai.Client,
    model_id: str,
) -> Optional[QuoteSelection]:
    """Gemini API 1회 호출로 한 블록의 인용구 선택을 수행한다."""
    if not candidates:
        logger.info(f"    ⏭ {block_id}: 후보 인용구 없음, 스킵")
        return None

    # 후보를 LLM에 전달할 컴팩트 형태로 변환
    compact = [{
        "review_id": c["review_id"],
        "product_id": c["product_id"],
        "text": c["text"],
        "sentiment": c["sentiment"],
        "star_rating": c["star_rating"],
        "helpful_count": c["helpful_count"],
        "impact_score": c["impact_score"],
    } for c in candidates]

    prompt = _SELECTION_PROMPT.format(
        narration=narration,
        theme=theme,
        products=", ".join(focal_products),
        candidates_json=json.dumps(compact, ensure_ascii=False, indent=2),
    )

    for attempt in range(1, 4):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=QuoteSelection,
                    temperature=0.1,
                ),
            )

            parsed = getattr(response, "parsed", None)
            if parsed and isinstance(parsed, QuoteSelection):
                return parsed

            raw_text = response.text.replace("```json", "").replace("```", "").strip()
            return QuoteSelection(**json.loads(raw_text))

        except Exception as e:
            logger.warning(f"    ⚠️ {block_id} 시도 {attempt}/3 실패: {e}")
            if attempt < 3:
                time.sleep(attempt * 2)

    logger.error(f"    ❌ {block_id}: LLM 호출 3회 실패")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# 메인 파이프라인
# ══════════════════════════════════════════════════════════════════════════════

def run_curation_pipeline(
    brief_path: Path,
    draft_path: Path,
    output_path: Path,
    candidates_per_block: int = 10,
):
    """
    큐레이션 파이프라인 실행.

    Agent가 생성한 brief를 읽고, draft에서 나레이션을 가져와
    인용구 검색 → LLM 선택 → patch 생성.
    """
    # ── 입력 로드 ─────────────────────────────────────────────────────────────
    for path, label in [(brief_path, "curation_brief"), (draft_path, "draft_script")]:
        if not path.exists():
            logger.error(f"❌ {label} 파일 없음: {path}")
            sys.exit(1)

    with brief_path.open("r", encoding="utf-8") as f:
        brief = json.load(f)
    with draft_path.open("r", encoding="utf-8") as f:
        draft = json.load(f)

    # draft를 block_id로 빠른 조회 가능하게 인덱싱
    draft_blocks: Dict[str, str] = {}
    for scene in draft.get("scenes", []):
        for block in scene.get("blocks", []):
            bid = block.get("block_id", "")
            draft_blocks[bid] = block.get("narration", "")

    # ── Gemini 클라이언트 ─────────────────────────────────────────────────────
    client = genai.Client()
    model_id = MODELS.get("analysis", "gemini-2.0-flash-lite")
    logger.info(f"🤖 LLM 모델: {model_id}")

    # ── 블록별 순회 ───────────────────────────────────────────────────────────
    used_review_ids: Set[str] = set()
    patch_scenes: List[Dict] = []
    total_quotes = 0
    total_blocks = 0

    for brief_scene in brief.get("scenes", []):
        scene_id = brief_scene.get("scene_id", "")
        headline = brief_scene.get("headline")

        logger.info(f"\n{'─'*60}")
        logger.info(f"📍 {scene_id}")

        patch_blocks: List[Dict] = []

        for brief_block in brief_scene.get("blocks", []):
            block_id = brief_block.get("block_id", "")
            title = brief_block.get("title", "")
            focal_products = brief_block.get("focal_products", [])
            theme = brief_block.get("theme", "")

            # draft에서 나레이션 텍스트 가져오기
            narration = draft_blocks.get(block_id, "")

            if not narration.strip() or not theme or not focal_products:
                logger.info(f"  ⏭ {block_id}: 나레이션/테마/제품 없음, 스킵")
                patch_blocks.append({
                    "block_id": block_id,
                    "title": title,
                    "evidence_quotes": [],
                })
                continue

            # ── 1. 후보 인용구 검색 ───────────────────────────────────────────
            all_candidates: List[Dict] = []
            for pid in focal_products:
                results = search_quotes(
                    product_id=pid,
                    canonical_theme=theme,
                    limit=candidates_per_block,
                    exclude_ids=used_review_ids,
                )
                all_candidates.extend(results)

            # 임팩트 스코어로 재정렬 후 상위 N개만 LLM에 전달
            all_candidates.sort(key=lambda x: -x.get("impact_score", 0))
            top_candidates = all_candidates[:candidates_per_block]

            logger.info(
                f"  🔍 {block_id}: {len(all_candidates)} 후보, "
                f"상위 {len(top_candidates)}개 → LLM"
            )

            # ── 2. LLM 인용구 선택 ────────────────────────────────────────────
            selection = select_quotes_for_block(
                block_id=block_id,
                narration=narration,
                theme=theme,
                focal_products=focal_products,
                candidates=top_candidates,
                client=client,
                model_id=model_id,
            )

            if selection:
                evidence_quotes = []
                for sq in selection.selected_quotes:
                    used_review_ids.add(sq.review_id)
                    evidence_quotes.append({
                        "product_id": sq.product_id,
                        "review_id": sq.review_id,
                        "star_rating": sq.star_rating,
                        "selection_reason": sq.selection_reason,
                        "highlight_phrase": sq.highlight_phrase,
                    })

                patch_blocks.append({
                    "block_id": block_id,
                    "title": title,  # Agent가 결정한 타이틀 보존
                    "evidence_quotes": evidence_quotes,
                })
                total_quotes += len(evidence_quotes)
                logger.info(f"  ✅ {block_id}: {len(evidence_quotes)} quotes")
            else:
                patch_blocks.append({
                    "block_id": block_id,
                    "title": title,
                    "evidence_quotes": [],
                })

            total_blocks += 1

        # 씬 패치 조립 — headline은 Agent가 결정한 값 보존
        patch_scene: Dict[str, Any] = {
            "scene_id": scene_id,
            "blocks": patch_blocks,
        }
        if headline:
            patch_scene["headline"] = headline

        patch_scenes.append(patch_scene)

    # ── curate_patch.json 저장 ────────────────────────────────────────────────
    patch = {"scenes": patch_scenes}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=2)

    # ── 실행 요약 ─────────────────────────────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info(f"  Curate Quotes Pipeline Complete")
    logger.info(f"{'='*60}")
    logger.info(f"  Blocks processed:       {total_blocks}")
    logger.info(f"  Total quotes assigned:   {total_quotes}")
    logger.info(f"  Unique reviews used:     {len(used_review_ids)}")
    logger.info(f"  Output:                  {output_path}")
    logger.info(f"{'='*60}\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ReviewLens: Automated Quote Curation Pipeline"
    )
    parser.add_argument(
        "--brief", default=str(DEFAULT_BRIEF),
        help=f"Agent-generated curation brief (default: {DEFAULT_BRIEF})"
    )
    parser.add_argument(
        "--draft", default=str(DEFAULT_DRAFT),
        help=f"Draft script for narration text (default: {DEFAULT_DRAFT})"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output curate_patch.json (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--candidates-per-block", type=int, default=10,
        help="Max candidates to search per block (default: 10)"
    )
    args = parser.parse_args()

    run_curation_pipeline(
        brief_path=Path(args.brief),
        draft_path=Path(args.draft),
        output_path=Path(args.output),
        candidates_per_block=args.candidates_per_block,
    )


if __name__ == "__main__":
    main()
