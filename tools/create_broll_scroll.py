import os
import glob
import cv2
import numpy as np

def main():
    PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CARDS_DIR = os.path.join(PROJ_ROOT, "datas", "review_cards")
    OUTPUT_VIDEO = os.path.join(PROJ_ROOT, "datas", "review_scroll_broll.mp4")

    # --- 영상 스펙 설정 ---
    VIDEO_WIDTH = 1920      # 모니터 가로 해상도 꽉 채우기
    VIDEO_HEIGHT = 1080     # 16:9 일반 모니터 화면 크기 (1080p)
    FPS = 15
    DURATION_SEC = 15       # 15초짜리 B-roll 영상
    SCROLL_SPEED = 45       # 프레임 당 픽셀 (초당 약 675px 이동)
    BLUR_KERNEL = (11, 11)  # OpenCV 가우시안 블러 렌즈 크기 (※ 반드시 홀수여야 함!)
    
    TOTAL_FRAMES = FPS * DURATION_SEC
    
    # 15초 동안 필요한 전체 스크롤 세로 길이 계산 = 화면 높이 + (이동 거리)
    REQ_PIXELS = VIDEO_HEIGHT + SCROLL_SPEED * (TOTAL_FRAMES + 1)
    
    image_files = sorted(glob.glob(os.path.join(CARDS_DIR, "card_*.png")))
    if not image_files:
        print("에러: 'data/review_cards' 폴더에 만들어진 리뷰 카드 이미지가 없어! 먼저 생성 스크립트를 돌려줘.")
        return

    print(f"로드할 리뷰 이미지 탐색 중... (목표 스크롤 길이: 약 {REQ_PIXELS}px 확보)")

    stacked_img = None
    current_h = 0
    imgs_to_stack = []

    for f in image_files:
        img = cv2.imread(f)
        if img is None: continue
        
        # 글씨를 못 읽게 리얼하게 블러 씌우기
        blur_img = cv2.GaussianBlur(img, BLUR_KERNEL, 0)
        
        # 리뷰 카드 사이에 약간의 간격(배경색) 추가를 위한 마진 생성
        margin_h = 20
        margin_block = np.full((margin_h, blur_img.shape[1], 3), (255, 255, 255), dtype=np.uint8)
        
        imgs_to_stack.append(blur_img)
        imgs_to_stack.append(margin_block)
        
        current_h += (blur_img.shape[0] + margin_h)
        if current_h >= REQ_PIXELS:
            break

    if not imgs_to_stack:
        print("로드 가능한 이미지가 없습니다.")
        return

    # 메모리상에서 세로로 길게 사진 쫙 이어 붙이기
    canvas = np.vstack(imgs_to_stack)
    canvas_h, canvas_w, _ = canvas.shape

    # 영상 생성기 준비 (아마존 웹페이지 화면 묘사를 위해 흰색 배경 사용)
    bg_color = (255, 255, 255) # 아마존 웹 브라우저 배경색 (White)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, FPS, (VIDEO_WIDTH, VIDEO_HEIGHT))

    # 모니터 화면(1920px) 정중앙에 아마존 리뷰(1000px)가 위치하도록 여백(Offset) 계산
    x_offset = (VIDEO_WIDTH - canvas_w) // 2

    print(f"🎬 B-roll 영상 렌더링 시작: {OUTPUT_VIDEO} (총 {TOTAL_FRAMES} 프레임)")

    y_start = 0
    for f_idx in range(TOTAL_FRAMES):
        # 꽉 찬 화면 프레임 만들기
        frame = np.full((VIDEO_HEIGHT, VIDEO_WIDTH, 3), bg_color, dtype=np.uint8)
        
        y_end = y_start + VIDEO_HEIGHT
        
        # 만약 스크롤이 끝까지 도달하면, 더 이상 이동 안 하고 정지 (혹은 반복)
        if y_end > canvas_h:
            y_end = canvas_h
            y_start = y_end - VIDEO_HEIGHT
            
        crop = canvas[y_start:y_end, :]
        hc = crop.shape[0]
        
        # 정중앙에 이미지 붙여넣기
        frame[:hc, x_offset:x_offset+canvas_w] = crop
        
        out.write(frame)
        y_start += SCROLL_SPEED
        
        if f_idx > 0 and f_idx % (FPS * 3) == 0:
            print(f"진행: {f_idx}/{TOTAL_FRAMES} 프레임 렌더링 중...")

    out.release()
    print(f"✅ 압도적 분위기의 15초 리뷰 스크롤 B-roll 영상이 완료됐어!: {OUTPUT_VIDEO}")

if __name__ == "__main__":
    main()
