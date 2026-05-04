import pandas as pd
import os
import math
import requests
import pymysql
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

# config에서 필요한 경로 임포트
from config import DATAS_DIR, INPUT_DIR, PROJ_ROOT, TMP_DIR
import hashlib

# ── 디자인 상수 (Amazon 리뷰 원본 스타일 완벽 대응) ─────────
# 이미지 원본 넓이 1920, 리뷰블럭 넓이 1024, 좌측 마진 20px로 설정
BASE_WIDTH = 1920
BLOCK_WIDTH = 1024
BLOCK_MARGIN_LEFT = 20
SCALE_FACTOR = 1.0

# 배경을 투명하게 처리하기 위해 Alpha 값을 0으로 설정 (RGBA 모드 사용)
BG_COLOR = (255, 255, 255, 0)
TEXT_BLACK = (15, 17, 17)        # 일반 리뷰 텍스트, 이름, 제목
TEXT_DARK_GREY = (86, 89, 89)    # 날짜, 장소, Report 등
TEXT_LIGHT_GREY = (200, 200, 200)# 파이프(|) 구분선 색상
ORANGE_VERIFIED = (196, 85, 0)       # Amazon Verified Purchase 색상 (#C45500)
STAR_GOLD = (255, 164, 28)           # Amazon 꽉 찬 별 색상 (#FFA41C)
STAR_EMPTY_BORDER = (213, 217, 217)  # Amazon 빈 별 테두리 색상
BUTTON_BORDER = (213, 217, 217)
PROFILE_BG = (230, 230, 230)

ASSET_DIR = os.path.join(PROJ_ROOT, "tools", "asset")
FONT_DIR = os.path.join(ASSET_DIR, "fonts") 

# ── DB 유틸 함수 ────────────────────────────────────────────────────────
def get_html_from_db(review_id):
    # TODO: 아래의 연결 정보를 실제 환경에 맞게 수정해주세요.
    DB_HOST = "***REDACTED_IP***"
    DB_USER = "***REDACTED_USER***"
    DB_PASS = "***REDACTED_PASS***"
    DB_NAME = "***REDACTED_DB***"
    DB_PORT = 3306

    try:
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            port=DB_PORT,
            cursorclass=pymysql.cursors.DictCursor  # 결과를 딕셔너리 형태로 반환
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT meta FROM amazon_reviews WHERE review_id = %s", (review_id,))
            result = cursor.fetchone()
            if result and 'meta' in result:
                return result['meta']
    except Exception as e:
        print(f"DB 데이터 불러오기 에러 ({review_id}): {e}")
    finally:
        try:
            conn.close()
        except:
            pass
    return None

# ── 폰트 캐싱 함수 ────────────────────────────────────────────────────────
def get_font(font_type, size):
    font_files = {
        "regular": "amazonember_rg.ttf",
        "bold": "amazonember_bd.ttf",
        "italic": "amazonember_lt.ttf"
    }
    font_name = font_files.get(font_type, "amazonember_rg.ttf")
    font_path = os.path.join(FONT_DIR, font_name)
    
    fallback = "arialbd.ttf" if font_type == "bold" else "arial.ttf"
    try:
        return ImageFont.truetype(font_path, int(size * SCALE_FACTOR))
    except:
        try:
            return ImageFont.truetype(fallback, int(size * SCALE_FACTOR))
        except:
            return ImageFont.load_default()

# ── 리뷰 카드 그리기 메인 프로세스 ──────────────────────────────────────────
def draw_single_review(review_id, soup, image, draw, start_y, highlight_phrase=None):
    
    # 1. 정보 추출 (HTML 파싱)
    # --- 이름 ---
    name_tag = soup.find('span', class_='a-profile-name')
    reviewer_name = name_tag.text.strip() if name_tag else "Amazon Customer"
    
    # --- 프로필 아바타 ---
    avatar_url = None
    avatar_div = soup.find('div', class_='a-profile-avatar')
    if avatar_div:
        img_tag = avatar_div.find('img')
        if img_tag:
            avatar_url = img_tag.get('data-src') or img_tag.get('src')
            if "grey-pixel.gif" in avatar_url and img_tag.get('data-src'):
                avatar_url = img_tag.get('data-src')
    
    # --- 별점 ---
    star_rating = 5
    rating_tag = soup.find('i', {'data-hook': 'review-star-rating'})
    if rating_tag:
        alt_span = rating_tag.find('span')
        if alt_span and "out of 5" in alt_span.text:
            try:
                star_rating = int(float(alt_span.text.split()[0]))
            except: pass
        else:
            for c in rating_tag.get('class', []):
                if c.startswith('a-star-'):
                    try: star_rating = int(c.replace('a-star-', ''))
                    except: pass
                    
    # --- 제목 ---
    title_tag = soup.find('a', {'data-hook': 'review-title'})
    if title_tag:
        spans = title_tag.find_all('span')
        title_text = spans[-1].text.strip() if spans else title_tag.text.strip()
        title_text = title_text.replace('5.0 out of 5 stars', '').strip()
    else:
        title_text = "Great product!"
        
    # --- 날짜 ---
    date_tag = soup.find('span', {'data-hook': 'review-date'})
    date_text = date_tag.text.strip() if date_tag else "Reviewed on Amazon"
    
    # --- 베리파이드 & 옵션 ---
    vp_tag = soup.find('span', {'data-hook': 'avp-badge'})
    has_vp = True if vp_tag else False
    
    variant_text = ""
    format_strip = soup.find('div', class_='review-format-strip')
    if format_strip:
        # Verified Purchase가 아닌 다른 태그를 옵션명으로 간주
        formats = format_strip.find_all('a', class_='a-size-mini')
        for f in formats:
            if 'avp-badge' not in f.get('data-hook', '') and f.text:
                variant_text = f.text.strip()
                break
                
    # --- 본문 ---
    body_tag = soup.find('span', {'data-hook': 'review-body'})
    review_body = body_tag.text.strip() if body_tag else "Excellent!"
    
    import glob
    # 썸네일 URL을 찾던 로직 삭제 (로컬 폴더에서 오프라인 로드하도록 변경)
            
    # --- Helpful Text 추출 ---
    helpful_tag = soup.find('span', {'data-hook': 'helpful-vote-statement'})
    if not helpful_tag:
        helpful_tag = soup.find('span', class_='cr-vote-text')
    helpful_text = helpful_tag.text.strip() if helpful_tag else ""

    # 2. 폰트 로드
    font_name = get_font("bold", 14)
    font_title = get_font("bold", 14)
    font_date = get_font("regular", 13)
    font_body = get_font("regular", 14)
    font_vp = get_font("bold", 13)
    
    # 리뷰블럭 내부 마진은 20으로 유지하되, 전체 margin_x는 블럭 좌측 마진을 더하여 시프트
    inner_margin = 20
    margin_x = BLOCK_MARGIN_LEFT + inner_margin
    current_y = start_y
    
    # --- Profile Picture & Name ---
    pfp_size = 34
    pfp_pos = (margin_x, current_y)
    pfp_image = None
    
    def get_cached_image(url):
        tmp_cache = os.path.join(TMP_DIR, "img_cache")
        os.makedirs(tmp_cache, exist_ok=True)
        h = hashlib.md5(url.encode()).hexdigest() + ".jpg"
        cp = os.path.join(tmp_cache, h)
        if os.path.exists(cp):
            return Image.open(cp)
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                i = Image.open(BytesIO(r.content)).convert("RGB")
                i.save(cp)
                return i
        except: pass
        return None

    if avatar_url:
        pfp_raw = get_cached_image(avatar_url)
        if pfp_raw:
            pfp_image = ImageOps.fit(pfp_raw, (pfp_size, pfp_size), Image.Resampling.LANCZOS)
            # 픽셀화 (모자이크) 처리
            m_size = 2 # 모자이크 강도 (숫자가 클수록 픽셀이 큼, 작게 하려면 2~3 추천)
            small = pfp_image.resize((max(1, int(pfp_size / m_size)), max(1, int(pfp_size / m_size))), Image.Resampling.NEAREST)
            pfp_image = small.resize((pfp_size, pfp_size), Image.Resampling.NEAREST)

    if pfp_image:
        mask = Image.new('L', (pfp_size, pfp_size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, pfp_size, pfp_size), fill=255)
        image.paste(pfp_image, pfp_pos, mask)
    else:
        draw.ellipse((pfp_pos[0], pfp_pos[1], pfp_pos[0]+pfp_size, pfp_pos[1]+pfp_size), fill=PROFILE_BG)

    # 이름 출력 및 픽셀화 (개인정보 보호)
    name_x = margin_x + pfp_size + 10
    name_y = current_y + (pfp_size - 14) // 2 
    draw.text((name_x, name_y), reviewer_name, font=font_name, fill=TEXT_BLACK)
    
    # 텍스트가 그려진 영역을 잘라내어 모자이크 처리 (해상도 반응형)
    text_bbox_rel = font_name.getbbox(reviewer_name)
    if text_bbox_rel:
        rel_left, rel_top, rel_right, rel_bottom = text_bbox_rel
        name_w = rel_right - rel_left
        name_h = rel_bottom - rel_top
        
        if name_w > 0 and name_h > 0:
            # 렌더링 시 위아래 여백을 보장하기 위해 크롭 영역에 패딩 추가
            pad_y = 6
            crop_x1 = int(name_x + rel_left)
            crop_y1 = int(name_y + rel_top - pad_y)
            crop_x2 = int(name_x + rel_right)
            crop_y2 = int(name_y + rel_bottom + pad_y)
            
            crop_w = crop_x2 - crop_x1
            crop_h = crop_y2 - crop_y1
            
            text_bbox = (crop_x1, crop_y1, crop_x2, crop_y2)
            text_crop = image.crop(text_bbox)
            
            t_mosaic = 2.5 # 텍스트 모자이크 강도 (숫자가 클수록 픽셀이 큼, 작게 하려면 2~3 추천)
            small_txt = text_crop.resize((max(1, int(crop_w / t_mosaic)), max(1, int(crop_h / t_mosaic))), Image.Resampling.NEAREST)
            pixelated_txt = small_txt.resize((crop_w, crop_h), Image.Resampling.NEAREST)
            
            image.paste(pixelated_txt, (crop_x1, crop_y1))

    current_y += pfp_size + 8
    
    # --- Stars & Title ---
    star_size = 16
    def draw_star(sx, sy, size, filled):
        cx, cy = sx + size / 2, sy + size / 2
        R = size / 2
        r = R * 0.45  # 좀 더 통통한 아마존 느낌의 비율
        pts = []
        for i in range(10):
            angle = i * math.pi / 5 - math.pi / 2
            radius = R if i % 2 == 0 else r
            pts.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
            
        if filled:
            draw.polygon(pts, fill=STAR_GOLD, outline=STAR_GOLD, width=1)
        else:
            # 빈 별은 회색 테두리, 채우기 없음
            draw.polygon(pts, fill=None, outline=STAR_EMPTY_BORDER, width=1)

    for i in range(5):
        # 간격 최소화 (아마존 스타일)
        draw_star(margin_x + i * (star_size + 1), current_y, star_size, i < star_rating)
        
    title_x = margin_x + 5 * (star_size + 1) + 8
    draw.text((title_x, current_y - 1), title_text, font=font_title, fill=TEXT_BLACK)
    current_y += star_size + 6 

    # --- Date ---
    draw.text((margin_x, current_y), date_text, font=font_date, fill=TEXT_DARK_GREY)
    current_y += 20
    
    # --- Color Variant & Verified Purchase ---
    cur_x = margin_x
    if variant_text:
        # "Color: "
        draw.text((cur_x, current_y), "Color: ", font=font_date, fill=TEXT_DARK_GREY)
        cur_x += int(font_date.getlength("Color: "))
        # Variant Value
        draw.text((cur_x, current_y), variant_text, font=font_date, fill=TEXT_DARK_GREY)
        cur_x += int(font_date.getlength(variant_text)) + 8
        # Pipe
        draw.text((cur_x, current_y), "|", font=font_date, fill=TEXT_LIGHT_GREY)
        cur_x += int(font_date.getlength("|")) + 8

    if has_vp:
        draw.text((cur_x, current_y), "Verified Purchase", font=font_vp, fill=ORANGE_VERIFIED)
    
    current_y += 24
    
    # --- Body Text (Word wrapper) & Highlight BBox ---
    def find_normalized(text, search_word):
        if not search_word: return -1, -1
        ignore_chars = set(".,'%+- \n\r")
        clean_search = "".join(c for c in search_word if c not in ignore_chars).lower()
        if not clean_search: return -1, -1

        for i in range(len(text)):
            if text[i] not in ignore_chars and text[i].lower() == clean_search[0]:
                t_idx = i
                s_idx = 0
                while t_idx < len(text) and s_idx < len(clean_search):
                    if text[t_idx] in ignore_chars:
                        t_idx += 1
                        continue
                    if text[t_idx].lower() == clean_search[s_idx]:
                        t_idx += 1
                        s_idx += 1
                    else:
                        break
                if s_idx == len(clean_search):
                    return i, t_idx
        return -1, -1

    h_start, h_end = -1, -1
    if highlight_phrase:
        h_start, h_end = find_normalized(review_body, highlight_phrase)

    # 텍스트 최대 넓이는 1920 캔버스가 아닌 리뷰블럭 넓이(1024)를 기준으로 계산
    max_text_width = BLOCK_WIDTH - inner_margin * 2 - 10
    lines_info = []
    current_char_idx = 0
    
    for para in review_body.split('\n'):
        if not para.strip():
            lines_info.append(("", current_char_idx, current_char_idx))
            current_char_idx += 1
            continue
            
        words = []
        word_start = current_char_idx
        for w in para.split(' '):
            words.append((w, word_start, word_start + len(w)))
            word_start += len(w) + 1
            
        current_line_words = []
        current_line_str = ""
        line_start_idx = current_char_idx
        
        for w, ws, we in words:
            test_line = current_line_str + " " + w if current_line_str else w
            if font_body.getlength(test_line) <= max_text_width:
                current_line_words.append((w, ws, we))
                current_line_str = test_line
            else:
                if current_line_words:
                    lines_info.append((current_line_str, line_start_idx, current_line_words[-1][2]))
                current_line_words = [(w, ws, we)]
                current_line_str = w
                line_start_idx = ws
                
        if current_line_words:
            lines_info.append((current_line_str, line_start_idx, current_line_words[-1][2]))
            
        current_char_idx += len(para) + 1

    highlight_bboxes_px = []
    line_height = 20
    
    for line_str, ls_idx, le_idx in lines_info:
        if line_str:
            draw.text((margin_x, current_y), line_str, font=font_body, fill=TEXT_BLACK)
            
            if h_start != -1 and h_end != -1:
                # Overlap check
                if max(h_start, ls_idx) < min(h_end, le_idx):
                    os_idx = max(h_start, ls_idx)
                    oe_idx = min(h_end, le_idx)
                    
                    prefix_str = review_body[ls_idx:os_idx]
                    highlight_str = review_body[os_idx:oe_idx]
                    
                    prefix_px = font_body.getlength(prefix_str)
                    highlight_px = font_body.getlength(highlight_str)
                    
                    hx = margin_x + prefix_px
                    hy = current_y + 2
                    hw = highlight_px
                    hh = line_height - 2
                    highlight_bboxes_px.append([hx, hy, hw, hh])
                    
        current_y += line_height
        
    current_y += 12
    
    # --- Image Thumbnails (HTML 파싱 + 로컬 폴더 지원) ---
    thumbnail_bboxes_px = []
    
    # 다중 제품 폴더 구조 (products/product_a 등) 전체에서 로컬 썸네일 재귀 탐색
    media_pattern = os.path.join(DATAS_DIR, "products", "*", "**", f"{review_id}_*.jpg")
    image_files = sorted(glob.glob(media_pattern, recursive=True))
    
    thumbs = []
    thumb_h = 81
    
    # 로컬 파일이 있으면 로컬부터 로드
    if image_files:
        for f in image_files[:10]:
            try:
                img_raw = Image.open(f).convert("RGB")
                orig_w, orig_h = img_raw.size
                if orig_h > 0:
                    new_w = max(1, int(orig_w * (thumb_h / orig_h)))
                    img_resized = img_raw.resize((new_w, thumb_h), Image.Resampling.LANCZOS)
                    thumbs.append(img_resized)
            except: pass
    else:
        # 로컬(Photos)에 없으면 DB에 저장된 HTML에서 썸네일 URL을 파싱하여 온라인(혹은 캐시)에서 로드
        image_urls = []
        for img in soup.find_all('img'):
            classes = img.get('class', [])
            if classes and 'review-image-tile' in classes:
                src = img.get('src')
                if src:
                    image_urls.append(src)
                    
        for url in image_urls[:10]:
            img_raw = get_cached_image(url)
            if img_raw:
                try:
                    orig_w, orig_h = img_raw.size
                    if orig_h > 0:
                        new_w = max(1, int(orig_w * (thumb_h / orig_h)))
                        img_resized = img_raw.resize((new_w, thumb_h), Image.Resampling.LANCZOS)
                        thumbs.append(img_resized)
                except: pass

    if thumbs:
        tx = margin_x
        ty = current_y
        for t in thumbs:
            image.paste(t, (tx, ty))
            thumbnail_bboxes_px.append([tx, ty, t.width, t.height])
            tx += t.width + 8
        current_y += thumb_h + 24
    else:
        current_y += 10 


    # --- Helpful Text ---
    if helpful_text:
        draw.text((margin_x, current_y), helpful_text, font=font_date, fill=TEXT_DARK_GREY)
        current_y += 24

    # --- Buttons (Helpful & Report) ---
    btn_text = "Helpful"
    padding_x = 24
    bx_w = int(font_date.getlength(btn_text)) + padding_x * 2
    bx_h = 32
    
    draw.rounded_rectangle([margin_x, current_y, margin_x + bx_w, current_y + bx_h], radius=16, outline=BUTTON_BORDER, width=1)
    
    bx_text_x = margin_x + padding_x
    bx_text_y = current_y + (bx_h - 13)//2 - 1
    draw.text((bx_text_x, bx_text_y), btn_text, font=font_date, fill=TEXT_BLACK)
    
    report_x = margin_x + bx_w + 16
    draw.text((report_x, bx_text_y), "|   Report", font=font_date, fill=TEXT_LIGHT_GREY)
    
    current_y += bx_h + 30
    
    # 개별 렌더링 종료: 현재 Y값과 추출된 텍스트/썸네일 기준 픽셀 기반 BBox를 반환
    return current_y, highlight_bboxes_px, thumbnail_bboxes_px

def generate_combined_review_card(block_id: str, quotes: list, output_dir: str = None) -> dict:
    """블록 내 여러 리뷰를 수직으로 이어붙이고 통합된 정규화 좌표계를 리턴하는 API."""
    if not quotes:
        return None
        
    if output_dir is None:
        output_dir = os.path.join(DATAS_DIR, "review_cards")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"card_combined_{block_id}.webp")
    
    MAX_HEIGHT = 20000
    # 리뷰 카드의 배경을 투명하게 만들기 위해 이미지 모드를 'RGB'에서 'RGBA'로 변경
    image = Image.new("RGBA", (BASE_WIDTH, MAX_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(image)
    
    current_y = 20
    all_quotes_data = []
    
    for quote in quotes:
        r_id = quote.get("review_id")
        h_phrase = quote.get("highlight_phrase")
        b_id = quote.get("block_id")
        
        if not r_id:
            continue
            
        html_snippet = get_html_from_db(r_id)
        if not html_snippet:
            print(f"Error: DB에서 {r_id}의 HTML 데이터를 찾을 수 없습니다.")
            continue
            
        soup = BeautifulSoup(html_snippet, 'html.parser')
        
        # Draw the single review onto the shared canvas
        new_y, highlight_bboxes_px, thumbnail_bboxes_px = draw_single_review(r_id, soup, image, draw, current_y, h_phrase)
        
        # Save px bboxes to normalize later
        all_quotes_data.append({
            "review_id": r_id,
            "block_id": b_id,
            "bboxes_px": highlight_bboxes_px,
            "thumb_bboxes_px": thumbnail_bboxes_px
        })
        
        # Add gap for next review
        current_y = new_y + 60

    # Final Crop
    final_height = current_y - 60 + 20 # subtract last explicit gap and add tiny bottom padding
    if final_height <= 20: 
        return None # Nothing drawn
        
    # 최종 자르기도 원본 이미지 사이즈(1920)를 기준으로 수행
    final_image = image.crop((0, 0, BASE_WIDTH, final_height))
    # 이미지 용량 최적화를 위해 WebP 포맷을 사용하되, 텍스트가 뭉개지지 않도록 무손실(lossless)로 저장
    final_image.save(output_path, format="WEBP", lossless=True, quality=100, method=6)
    
    # Bboxes를 픽셀 단위(x1, y1, x2, y2)로 리턴
    # 원본 이미지의 좌측 상단 모서리를 (0,0) 기준으로 한 절대 픽셀 좌표
    quotes_output = []
    for q_data in all_quotes_data:
        pixel_bboxes = []
        for box in q_data["bboxes_px"]:
            hx, hy, hw, hh = box
            
            # 좌측 상단(x1, y1)과 우측 하단(x2, y2) 픽셀 좌표 계산
            x1 = int(round(hx))
            y1 = int(round(hy))
            x2 = int(round(hx + hw))
            y2 = int(round(hy + hh))
            
            pixel_bboxes.append({
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            })
            
        thumb_bboxes = []
        for box in q_data["thumb_bboxes_px"]:
            tx, ty, tw, th = box
            
            x1 = int(round(tx))
            y1 = int(round(ty))
            x2 = int(round(tx + tw))
            y2 = int(round(ty + th))
            
            thumb_bboxes.append({
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2
            })
            
        quotes_output.append({
            "review_id": q_data["review_id"],
            "block_id": q_data.get("block_id"),
            "highlight_bboxes": pixel_bboxes,
            "thumbnail_bboxes": thumb_bboxes
        })

    return {
        "review_card_data": {
            "image_path": output_path,
            "size": {"width": BASE_WIDTH, "height": final_height}
        },
        "quotes_data": quotes_output
    }


def main(review_ids=None):
    output_dir = os.path.join(DATAS_DIR, "review_cards")
    os.makedirs(output_dir, exist_ok=True)
    
    date_csv_path = os.path.join(INPUT_DIR, "cleaned_reviews.csv")
    csv_path = os.path.join(DATAS_DIR, "buying_guide_extracted.csv")
    
    df = pd.read_csv(csv_path) if os.path.exists(csv_path) else None
    date_df = pd.read_csv(date_csv_path) if os.path.exists(date_csv_path) else None
    
    if df is None or date_df is None:
        print("필수 CSV 파일이 없습니다.")
        return
        
    date_df = date_df[['review_id', 'date']].drop_duplicates()
    merged_df = df.merge(date_df, on='review_id', how='left')
    merged_df['date'] = pd.to_datetime(merged_df['date'], errors='coerce')
    merged_df = merged_df.sort_values(by='date', ascending=True).reset_index(drop=True)
    
    # 특정 리뷰 ID 리스트가 입력된 경우 필터링
    if review_ids:
        merged_df = merged_df[merged_df['review_id'].isin(review_ids)]
        
    if merged_df.empty:
        print("처리할 리뷰 데이터가 없습니다.")
        return

    print(f"전체 {len(merged_df)}개의 카드에 대한 파일 생성 시작! (로컬 캐싱 적용)")
    success_count = 0
    
    # 전체 순회
    for idx, row in merged_df.iterrows():
        try:
            review_id = str(row['review_id']) if 'review_id' in row else f"idx_{idx}"
        except:
            review_id = f"idx_{idx}"
            
        out_file = os.path.join(output_dir, f"card_{review_id}.webp")
        
        # 1. DB에서 HTML 질의
        html_snippet = get_html_from_db(review_id)
        
        # 2. 파싱 및 그리기
        if html_snippet:
            try:
                create_review_card(review_id, html_snippet, out_file)
                print(f"✅ 생성 성공: {out_file}")
                success_count += 1
            except Exception as e:
                print(f"그리기 실패 ({review_id}): {e}")
        else:
            print(f"DB에 데이터 없음 또는 연결 실패 패스 ({review_id})")
            
    print(f"🎉 렌더링 완료! {success_count}개의 카드가 추출/생성되었습니다.")

if __name__ == "__main__":
    # 특정 리뷰 ID만 생성하려면 리스트를 전달하세요. 예: main(['REVIEW_ID_1', 'REVIEW_ID_2'])
    main(['R1HZODJ2ZI3AYF'])
