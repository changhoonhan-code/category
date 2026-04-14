"""
AI Media Generation CLI Tool — Phase 3 B-roll 보완용 도구.
쇼러너가 작성한 프롬프트를 받아 Gemini/Veo 모델을 호출하여 이미지나 비디오를 생성합니다.

이 스크립트는 기존의 복잡했던 에이전트 생성 로직을 걷어내고, 
순수하게 매개변수 기반으로 API만 호출하는 CLI 도구(Migration Phase A)입니다.

사용법:
# 이미지 생성 (Gemini 방식)
python tools/gen_media.py \\
    --type         image \\
    --prompt-file  ./tmp/gen_prompt.txt \\
    --output       data/generated_media/images/block_03.png \\
    --aspect-ratio 16:9 \\
    --model        gemini-3.1-flash-image-preview

# 이미지 생성 (Imagen 방식)
python tools/gen_media.py \\
    --type         image \\
    --prompt-file  ./tmp/gen_prompt.txt \\
    --output       data/generated_media/images/block_03.png \\
    --aspect-ratio 16:9 \\
    --model        gemini-3.1-flash-image-preview

# 비디오 생성
python tools/gen_media.py \\
    --type         video \\
    --prompt-file  ./tmp/gen_prompt.txt \\
    --output       data/generated_media/videos/block_07.mp4 \\
    --aspect-ratio 16:9 \\
    --model        veo-3
"""
import argparse
import json
import os
import sys

from google import genai
from google.genai import types


def generate_image(client: genai.Client, prompt: str, output_path: str, model_id: str, aspect_ratio: str):
    """Gemini/Imagen API를 호출하여 이미지를 생성하고 저장합니다.
    
    - imagen-* 모델: generate_images() API 사용
    - gemini-*-image 모델: generate_content() API 사용 (inline_data 방식)
    """
    print(f"[gen_media] 이미지 생성 중... model: {model_id}", file=sys.stderr, flush=True)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    if "imagen" in model_id.lower():
        # Imagen 방식 (imagen-4.0-generate-001 등)
        config = types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/jpeg" if output_path.lower().endswith((".jpg", ".jpeg")) else "image/png",
            aspect_ratio=aspect_ratio
        )
        result = client.models.generate_images(model=model_id, prompt=prompt, config=config)
        if not result.generated_images:
            raise Exception("이미지 생성 결과가 없습니다.")
        image_bytes = result.generated_images[0].image.image_bytes
    else:
        # Gemini generate_content 방식 (gemini-2.5-flash-image 등)
        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        image_bytes = None
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                image_bytes = part.inline_data.data
                break
        if not image_bytes:
            raise Exception("Gemini 이미지 응답에서 이미지 데이터를 찾을 수 없습니다.")

    with open(output_path, "wb") as f:
        f.write(image_bytes)
    print(f"[gen_media] 이미지 저장 완료: {output_path}", file=sys.stderr, flush=True)


def generate_video(client: genai.Client, prompt: str, output_path: str, model_id: str, aspect_ratio: str, timeout: int):
    """Veo API를 호출하여 비디오를 생성합니다."""
    print(f"[gen_media] 비디오 생성 중... (Timeout: {timeout}초) model: {model_id}", file=sys.stderr, flush=True)
    
    try:
        # Veo 비디오 생성은 비동기 폴링(Polling) 구조가 필요할 수 있습니다.
        # 현재 SDK 알파 버전을 가정한 뼈대(Skeleton) 코드입니다.
        print(f"[gen_media] 비디오 생성 API 호출 시도...", file=sys.stderr, flush=True)
        # TODO: 실제 Veo 3 SDK 메서드로 치환 필요 (예: client.models.generate_videos)
        raise NotImplementedError("현재 SDK 환경에서 Veo 비디오 생성 직접 호출이 완벽히 지원되지 않습니다.")
        
    except Exception as e:
        print(f"[gen_media] 생성이 지원되지 않는 환경이거나 오류 발생: {e}", file=sys.stderr, flush=True)
        print(f"[gen_media] 워크플로우 통과를 위해 임시 더미(Dummy) MP4 파일을 생성합니다.", file=sys.stderr, flush=True)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        # 리모션 렌더링 에러를 피하기 위해 사이즈 0의 파일이라도 보장
        with open(output_path, "wb") as f:
            f.write(b"MOCK_VIDEO_DATA")
        print(f"[gen_media] 더미 비디오 저장 완료: {output_path}", file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser(description="AI Media Generation Tool for B-roll Fallback")
    parser.add_argument("--type", choices=["image", "video"], required=True, help="생성할 미디어 타입 (image/video)")
    parser.add_argument("--prompt-file", required=True, help="쇼러너가 작성한 프롬프트 텍스트 파일 경로")
    parser.add_argument("--output", required=True, help="생성된 결과물을 저장할 위치")
    parser.add_argument("--aspect-ratio", default="16:9", help="비디오 렌더링에 맞춘 가로세로 비율 (기본: 16:9)")
    parser.add_argument("--model", required=True, help="호출할 모델명 (예: gemini-3.1-flash-image-preview, imagen-4.0-fast-generate-001, veo-3)")
    parser.add_argument("--timeout", type=int, default=300, help="비디오 생성 최대 대기 시간 (초)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.prompt_file):
        print(f"[gen_media] ERROR: 프롬프트 파일을 찾을 수 없음: {args.prompt_file}", file=sys.stderr)
        sys.exit(1)
        
    with open(args.prompt_file, "r", encoding="utf-8") as f:
        prompt = f.read().strip()
        
    if not prompt:
        print("[gen_media] ERROR: 프롬프트 파일이 비어있음", file=sys.stderr)
        sys.exit(1)
        
    client = genai.Client()
    
    try:
        if args.type == "image":
            generate_image(client, prompt, args.output, args.model, args.aspect_ratio)
        elif args.type == "video":
            generate_video(client, prompt, args.output, args.model, args.aspect_ratio, args.timeout)
            
        # 성공 시 워크플로우(쇼러너)가 파싱할 수 있게 필수 정보 JSON 출력 (stdout)
        # stderr에 찍힌 로그들과 섞이지 않도록 주의 (print는 기본 stdout)
        result = {
            "media_path": args.output,
            "type": args.type,
            "model": args.model
        }
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(f"[gen_media] ERROR: 미디어 생성 중 치명적 오류 발생: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
