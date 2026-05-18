# main.py
import cv2
import numpy as np
import config
from detector import find_marker_multi_scale
from ballistics import get_mortar_in_game_distance, calculate_physical_distance, get_absolute_height
# 🌟 [유지보수 향상] 독립 분리된 격자 제거 컴포넌트 모듈 호출
from grid_remover import remove_pubg_grid

def main():
    # 1. 이미지 로드 및 전처리
    src_img = cv2.imread("image/screen.png")
    if src_img is None:
        print("[오류] image/screen.png 파일을 찾을 수 없습니다.")
        return

    h, w, _ = src_img.shape
    map_size = h
    start_x = (w - map_size) // 2

    gray_src = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
    
    # 쪼개진 이미지의 메모리 독립성을 위해 .copy() 사용
    map_roi = gray_src[0:h, start_x : start_x + map_size].copy()
    
    # 🌟 [모듈 연동 부] 매칭 윈도우 전 단계에서 격자 필터링 수행
    # 기본값으로 인게임 미니맵/지도 환경에 맞춘 grid_mode 지정 (2, 4, 8)
    map_roi_cleaned = remove_pubg_grid(map_roi, grid_mode=8)
    
    tpl_player = cv2.imread("image/player.png", 0)
    tpl_marker = cv2.imread("image/marker.png", 0)

    if tpl_player is None or tpl_marker is None:
        print("[오류] player.png 또는 marker.png 템플릿 이미지를 확인하세요.")
        return

    # 2. 객체 탐지 수행 (모듈을 거쳐 격자가 완벽히 필터링된 이미지 타겟팅)
    scale_range = np.linspace(0.1, 1.0, 45)[::-1]
    match_p = find_marker_multi_scale(map_roi_cleaned, tpl_player, scale_range)
    match_m = find_marker_multi_scale(map_roi_cleaned, tpl_marker, scale_range)

    if not (match_p and match_p["max_val"] >= config.MATCH_THRESHOLD) or not (match_m and match_m["max_val"] >= config.MATCH_THRESHOLD):
        print("❌ 플레이어 또는 마커를 화면에서 찾을 수 없습니다. (모듈 처리 필터 상태를 점검하세요)")
        return

    # --------------------------------------------------------
    # 🔄 버그가 해결된 직관적인 좌표 변환 로직 (그대로 유지)
    # --------------------------------------------------------
    p_top_left = match_p["max_loc"]
    m_top_left = match_m["max_loc"]

    # [단계 1] 잘라낸 지도 내부(0 ~ map_size) 기준의 순수 중심점/밑변 좌표 구하기
    p_roi_cx = p_top_left[0] + (match_p["w"] // 2)
    p_roi_cy = p_top_left[1] + (match_p["h"] // 2)
    
    m_roi_cx = m_top_left[0] + (match_m["w"] // 2)
    m_roi_cy = m_top_left[1] + match_m["h"]

    # [단계 2] 하이트맵 매핑을 위한 지도 기준 상대 비율 계산
    p_rx, p_ry = p_roi_cx / map_size, p_roi_cy / map_size
    m_rx, m_ry = m_roi_cx / map_size, m_roi_cy / map_size

    # [단계 3] 원본 screen.png(전체 화면 크기) 위에 그리기 위한 좌표 변환
    p_cx = p_roi_cx + start_x
    p_cy = p_roi_cy
    
    m_cx = m_roi_cx + start_x
    m_cy = m_roi_cy
    
    current_map = 'jackal'  # 💡 현재 분석 중인 맵 지정 (동적 변경 가능)
    
    heightmap_path = f"image/heightmap/{current_map}_heightmap.png"
    heightmap = cv2.imread(heightmap_path, cv2.IMREAD_UNCHANGED)
    if heightmap is None:
        print(f"[오류] 하이트맵 이미지({heightmap_path})를 로드할 수 없습니다.")
        return
        
    hm_h, hm_w = heightmap.shape[:2]
    p_hx = max(0, min(int(p_rx * (hm_w - 1)), hm_w - 1))
    p_hy = max(0, min(int(p_ry * (hm_h - 1)), hm_h - 1))
    m_hx = max(0, min(int(m_rx * (hm_w - 1)), hm_w - 1))
    m_hy = max(0, min(int(m_ry * (hm_h - 1)), hm_h - 1))

    # 안전장치: 혹시라도 정의되지 않은 맵 이름일 경우 기본값 지정
    scale_xy = config.MAP_SCALES.get(current_map, 0.9765625)
    # 수평 거리 및 고도차 계산
    x_dist = calculate_physical_distance(p_hx, p_hy, m_hx, m_hy, scale_xy)
    player_z = get_absolute_height(heightmap, p_hx, p_hy)
    marker_z = get_absolute_height(heightmap, m_hx, m_hy)
    h_diff = marker_z - player_z

    # 4. 탄도학 조준값 계산
    final_mortar_dist = get_mortar_in_game_distance(x_dist, h_diff, config.MORTAR_STEPS)

    # 5. 시각화 및 결과 저장
    result_img = src_img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    
    # 가이드선 및 점 작도
    cv2.circle(result_img, (p_cx, p_cy), 6, (0, 0, 255), -1) 
    cv2.circle(result_img, (m_cx, m_cy), 6, (0, 0, 255), -1) 
    cv2.line(result_img, (p_cx, p_cy), (m_cx, m_cy), (0, 255, 255), 2)

    # 객체별 높이 텍스트 UI 생성
    p_text = f"{player_z:.1f}m"
    m_text = f"{marker_z:.1f}m"
    
    for text, (cx, cy) in [(p_text, (p_cx, p_cy)), (m_text, (m_cx, m_cy))]:
        cv2.putText(result_img, text, (cx + 15, cy - 15), font, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(result_img, text, (cx + 15, cy - 15), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

    # 요약 정보창 인터페이스
    cv2.rectangle(result_img, (10, 10), (460, 140), (0, 0, 0), -1)
    cv2.putText(result_img, f"Horizontal Dist: {x_dist:.2f}m", (20, 40), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(result_img, f"Height Diff (H): {h_diff:.2f}m", (20, 80), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    
    if final_mortar_dist:
        cv2.putText(result_img, f"🎯 IN-GAME DIST: {final_mortar_dist}m", (20, 120), font, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        print(f"🎯 [계산 완료] 수평:{x_dist:.1f}m, 고도차:{h_diff:.1f}m (P:{player_z:.1f}m / M:{marker_z:.1f}m) -> 조준:{final_mortar_dist}m")
    else:
        cv2.putText(result_img, "🎯 IN-GAME DIST: IMPOSSIBLE", (20, 120), font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        print("❌ 발사 불가능 구역입니다.")

    cv2.imwrite("result.png", result_img)

if __name__ == "__main__":
    main()