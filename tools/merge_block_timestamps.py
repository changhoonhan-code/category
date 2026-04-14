import json
import os
import sys

def get_theme_name_by_review_id(review_id, category_data):
    for theme in category_data.get("common_themes", []):
        for pair in theme.get("contradiction_pairs", []):
            if pair.get("positive_quote", {}).get("review_id") == review_id:
                return theme.get("theme_name")
            if pair.get("negative_quote", {}).get("review_id") == review_id:
                return theme.get("theme_name")
    return None

def main():
    # 경로 설정
    base_dir = r"d:\GEMINI"
    script_output_path = os.path.join(base_dir, "data", "script_output.json")
    timestamps_path = os.path.join(base_dir, "data", "word_timestamps.json")
    category_analysis_path = os.path.join(base_dir, "data", "category_analysis.json")
    blueprint_path = os.path.join(base_dir, "data", "comparison_blueprint.json")
    output_dir = os.path.join(base_dir, "data", "blocks")

    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    print(f"출력 디렉토리 확인/생성 완료: {output_dir}")

    # 데이터 로드 헬퍼 함수
    def load_json(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"로드 성공: {path}")
            return data
        except Exception as e:
            print(f"오류: {path} 로드 실패 - {e}")
            sys.exit(1)

    script_data = load_json(script_output_path)
    timestamps_data = load_json(timestamps_path)
    category_data = load_json(category_analysis_path)
    blueprint_data = load_json(blueprint_path)

    # 블록 데이터 추출 및 타임스탬프 + 시각화 데이터 병합
    merge_count = 0
    scenes = script_data.get("scenes", [])
    
    for scene in scenes:
        scene_type = scene.get("scene_type")
        blocks = scene.get("blocks", [])

        # 씬 전체의 공통 테마 찾기 (review_id 역추적 방식)
        theme_name_for_scene = None
        if scene_type == "theme_comparison":
            for block in blocks:
                for quote in block.get("evidence_quotes", []):
                    rid = quote.get("review_id")
                    if rid:
                        found_theme = get_theme_name_by_review_id(rid, category_data)
                        if found_theme:
                            theme_name_for_scene = found_theme
                            break
                if theme_name_for_scene:
                    break

        for block in blocks:
            block_id = block.get("block_id")
            if not block_id:
                continue

            # 1. word_timestamps.json 매핑
            block_timestamps = timestamps_data.get(block_id)
            if block_timestamps is not None:
                narration_text = block.get("narration", "")
                mapped_timestamps = []
                current_text_idx = 0
                unmatched_words = []
                
                def find_normalized(text, search_word, start_idx):
                    ignore_chars = set(".,'%+-")
                    clean_search = "".join(c for c in search_word if c not in ignore_chars).lower()
                    if not clean_search:
                        return -1, -1
                
                    for i in range(start_idx, len(text)):
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

                for wt in block_timestamps:
                    word = wt.get("word", "")
                    
                    # 1차 시도: 원문 매칭
                    idx = narration_text.find(word, current_text_idx)
                    text_end_val = idx + len(word) if idx != -1 else -1
                    
                    # 2차 시도: 대소문자 무시
                    if idx == -1:
                        idx = narration_text.lower().find(word.lower(), current_text_idx)
                        text_end_val = idx + len(word) if idx != -1 else -1
                        
                    # 3차 시도: 특수 기호 무시 정규화 매칭
                    if idx == -1:
                        idx, text_end_val = find_normalized(narration_text, word, current_text_idx)
                        
                    if idx != -1:
                        text_start = idx
                        text_end = text_end_val
                        current_text_idx = text_end
                    else:
                        text_start = -1
                        text_end = -1
                        unmatched_words.append(word)
                        
                    mapped_timestamps.append({
                        "word": word,
                        "time_start": wt.get("start"),
                        "time_end": wt.get("end"),
                        "text_start": text_start,
                        "text_end": text_end
                    })
                
                block["word_timestamps"] = mapped_timestamps
                if unmatched_words:
                    print(f"경고 [Word Align]: [{block_id}] 블록에서 {len(unmatched_words)}개의 텍스트 오프셋 매칭 실패 -> {unmatched_words}")
            else:
                block["word_timestamps"] = []
                print(f"알림: {block_id}에 해당하는 타임스탬프가 없습니다.")

            # 2. 시각화(Visualization) 데이터 병합
            vis_data = None
            if scene_type == "theme_comparison" and theme_name_for_scene:
                for ct in category_data.get("common_themes", []):
                    if ct.get("theme_name") == theme_name_for_scene:
                        vis_data = {
                            "data_type": "theme_ranking",
                            "theme_name": theme_name_for_scene,
                            "chart_data": ct.get("rankings", [])
                        }
                        break
            
            elif scene_type == "category_rating_overview":
                chart_data = []
                for p in category_data.get("products", []):
                    chart_data.append({
                        "product_id": p.get("product_id"),
                        "product_name": p.get("product_name"),
                        "all_time_rating_avg": p.get("all_time_rating_avg"),
                        "recent_review_rating_avg": p.get("recent_review_rating_avg"),
                        "population_gap": p.get("population_gap"),
                        "sold_last_month": p.get("sold_last_month")
                    })
                vis_data = {
                    "data_type": "population_gap_chart",
                    "chart_data": chart_data
                }
            
            elif scene_type == "hook":
                hook_data = blueprint_data.get("selected_hook_contradiction", {})
                vis_data = {
                    "data_type": "hook_contradiction",
                    "theme_name": hook_data.get("theme_name"),
                    "product_ids": hook_data.get("product_ids"),
                    "contradiction_summary": hook_data.get("contradiction_summary")
                }

            elif scene_type == "standout":
                standout_mapping = blueprint_data.get("standout_mapping", [])
                standout_info = next((s for s in standout_mapping if s.get("product_id", "") in block_id), None)
                if standout_info:
                    vis_data = {
                        "data_type": "standout_mapping",
                        "product_id": standout_info.get("product_id"),
                        "theme_name": standout_info.get("theme_name"),
                        "why_unique": standout_info.get("why_unique")
                    }

            if vis_data:
                block["visualization_data"] = vis_data
                
            block["scene_type"] = scene_type

            # 3. 인용구(Evidence Quotes) 순회하여 통합 리뷰 캔버스 생성 및 좌표 분배
            if "evidence_quotes" in block and len(block["evidence_quotes"]) > 0:
                from review_capture_image import generate_combined_review_card
                
                print(f"[{block_id}] 리뷰 캡처 통합 캔버스 렌더링 중...")
                combined_card_res = generate_combined_review_card(block_id, block["evidence_quotes"])
                
                if combined_card_res:
                    # 1. 블록 root 레벨에 통합 이미지 메타데이터 할당
                    block["review_card_data"] = combined_card_res.get("review_card_data")
                    
                    # 2. 각 리뷰 데이터 하위에 개별 highlight_bboxes 맵핑
                    quotes_meta = combined_card_res.get("quotes_data", [])
                    for quote in block["evidence_quotes"]:
                        matching_q = next((q for q in quotes_meta if q["review_id"] == quote.get("review_id")), None)
                        if matching_q:
                            quote["highlight_bboxes"] = matching_q.get("highlight_bboxes", [])
            
            # 불필요한 키 제거
            for key_to_remove in ["pacing_profile", "bgm_mood", "directing_hint"]:
                block.pop(key_to_remove, None)

            # 개별 블록 파일로 저장
            block_file_path = os.path.join(output_dir, f"{block_id}.json")
            try:
                with open(block_file_path, "w", encoding="utf-8") as out_f:
                    json.dump(block, out_f, ensure_ascii=False, indent=2)
                merge_count += 1
            except Exception as e:
                print(f"오류: {block_file_path} 저장 실패 - {e}")

    print(f"\n작업 완료! 총 {merge_count}개의 블록이 {output_dir} 경로에 저장되었습니다.")

if __name__ == "__main__":
    main()
