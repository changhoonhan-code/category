"""
ReviewLens 공유 설정 — 모든 도구가 참조하는 모델 ID, 경로, 상수.

사용법:
    from config import MODELS, PROJ_ROOT, DATAS_DIR
"""
import os

# ── 프로젝트 경로 ────────────────────────────────────────────────────────────
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(PROJ_ROOT, "data")
INPUT_DIR = os.path.join(PROJ_ROOT, "products")
TOOLS_DIR = os.path.join(PROJ_ROOT, "tools")
TMP_DIR = os.path.join(PROJ_ROOT, "tmp")

# ── Gemini API 모델 ID ──────────────────────────────────────────────────────
MODELS = {
    "analysis": "gemini-3.1-flash-lite-preview",     # 단순 리뷰 분류/전처리용 (초고속/가성비)
    "analysis_pro": "gemini-pro-latest",  # 순차적 추론, 프롬프트 준수용 (고지능/어드밴스드)
    "tts": "gemini-3.1-flash-tts-preview",             # TTS 나레이션 합성
    "stt": "gemini-3-flash-preview",           # STT 단어 정렬
    "image_gemini": "gemini-3.1-flash-image-preview", # 이미지 생성 (Gemini)
    "video": "veo-3.1-generate-preview",                                 # 영상 생성
}

# ── TTS 설정 ─────────────────────────────────────────────────────────────────
TTS_VOICE = "Rasalgethi"
TTS_TEMPERATURE = 1.0  # TTS 표현력 (0.0=단조, 1.0=절제, 2.0=극적). Consumer Navigator = 절제된 분석가.
TTS_SPEED = 1.0       # FFmpeg atempo 배율 (1.0 = 후처리 없음)
TTS_SAMPLE_RATE = 24000
TTS_SAMPLE_WIDTH = 2   # 16-bit PCM
TTS_CHANNELS = 1       # mono

# ── 동시성 / 재시도 ──────────────────────────────────────────────────────────
MAX_CONCURRENT = 5
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # 초
BLOCKS_PER_GROUP = 5    # /prompt 워크플로우: 그룹당 최대 블록 수 (인지과부하 방지)

# ── 파이프라인 계약 (SSOT) ────────────────────────────────────────────────
# 모든 도구가 공유하는 상수를 pipeline_contracts.json에서 싱글턴 로드.
# Usage: from config import contracts
import json as _json

_CONTRACTS_PATH = os.path.join(TOOLS_DIR, "pipeline_contracts.json")
_contracts_cache = None


def contracts():
    """pipeline_contracts.json을 싱글턴으로 로드. 모든 도구가 이걸 import."""
    global _contracts_cache
    if _contracts_cache is None:
        with open(_CONTRACTS_PATH, "r", encoding="utf-8") as f:
            _contracts_cache = _json.load(f)
    return _contracts_cache
