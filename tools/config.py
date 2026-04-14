"""
ReviewLens 공유 설정 — 모든 도구가 참조하는 모델 ID, 경로, 상수.

사용법:
    from config import MODELS, PROJ_ROOT, DATAS_DIR
"""
import os

# ── 프로젝트 경로 ────────────────────────────────────────────────────────────
PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATAS_DIR = os.path.join(PROJ_ROOT, "data")
INPUT_DIR = os.path.join(PROJ_ROOT, "one_product")
TOOLS_DIR = os.path.join(PROJ_ROOT, "tools")
TMP_DIR = os.path.join(PROJ_ROOT, "tmp")

# ── Gemini API 모델 ID ──────────────────────────────────────────────────────
MODELS = {
    "analysis": "gemini-3.1-flash-lite-preview",     # 단순 리뷰 분류/전처리용 (초고속/가성비)
    "analysis_pro": "gemini-pro-latest",  # 순차적 추론, 프롬프트 준수용 (고지능/어드밴스드)
    "tts": "gemini-2.5-pro-preview-tts",             # TTS 나레이션 합성
    "stt": "gemini-3-flash-preview",           # STT 단어 정렬
    "image_gemini": "gemini-3.1-flash-image-preview", # 이미지 생성 (Gemini)
    "video": "veo-3.1-generate-preview",                                 # 영상 생성
}

# ── TTS 설정 ─────────────────────────────────────────────────────────────────
TTS_VOICE = "Rasalgethi"
TTS_SPEED = 1.0       # FFmpeg atempo 배율 (1.0 = 후처리 없음)
TTS_SAMPLE_RATE = 24000
TTS_SAMPLE_WIDTH = 2   # 16-bit PCM
TTS_CHANNELS = 1       # mono

# ── 동시성 / 재시도 ──────────────────────────────────────────────────────────
MAX_CONCURRENT = 5
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # 초
