# main.py
import time
import cv2
import numpy as np
import keyboard
import config
from detector import find_marker_multi_scale
from ballistics import get_mortar_in_game_distance, calculate_physical_distance, get_absolute_height
from grid_remover import remove_pubg_grid

# 🌟 [유지보수 향상] 캡처 전용 모듈 추가
import capture 

def run_calculator():
    """F8 키 입력 시 실행될 박격포 연산 메인 로직"""
    print(f"\n[{time.strftime('%H:%M:%S')}] 🎯 F8 감지! 실시간 화면 분석을 시작합니다...")

    # 1. 실시간 이미지 로드 (capture 모듈 호출)
    src_img = capture.get_screenshot()
    if src_img is None:
        print("[오류] 화면을 캡처하지 못했습니다.")
        return

    h, w, _ = src_img.shape
    map_size = h
    start_x = (w - map_size) // 2

    gray_src = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY)
    
    # 쪼개진 이미지의 메모리 독립성을 위해 .copy() 사용
    map_roi = gray_src[0:h, start_x : start_x + map_size].copy()
    
    # 격자 필터링 수행 (2, 4, 8)
    map_roi_cleaned = remove_pubg_grid(map_roi, grid_mode=8)
    
    tpl_player = cv2.imread("image/player.png", 0)
    tpl_marker = cv2.imread("image/marker.png", 0)

    if tpl_player is None or tpl_marker is None:
        print("[오류] player.png 또는 marker.png 템플릿 이미지를 확인하세요.")
        return

    # 2. 객체 탐지 수행
    scale_range = np.linspace(0.1, 1.0, 45)[::-1]
    match_p = find_marker_multi_scale(map_roi_cleaned, tpl_player, scale_range)
    match_m = find_marker_multi_scale(map_roi_cleaned, tpl_marker, scale_range)

    if not (match_p and match_p["max_val"] >= config.MATCH_THRESHOLD) or not (match_m and match_m["max_val"] >= config.MATCH_THRESHOLD):
        print("❌ 플레이어 또는 마커를 화면에서 찾을 수 없습니다. (지도를 켜둔 상태인지 확인하세요)")
        return

    # 좌표 변환 로직
    p_top_left = match_p["max_loc"]
    m_top_left = match_m["max_loc"]

    p_roi_cx = p_top_left[0] + (match_p["w"] // 2)
    p_roi_cy = p_top_left[1] + (match_p["h"] // 2)
    
    m_roi_cx = m_top_left[0] + (match_m["w"] // 2)
    m_roi_cy = m_top_left[1] + match_m["h"]

    p_rx, p_ry = p_roi_cx / map_size, p_roi_cy / map_size
    m_rx, m_ry = m_roi_cx / map_size, m_roi_cy / map_size

    p_cx = p_roi_cx + start_x
    p_cy = p_roi_cy
    
    m_cx = m_roi_cx + start_x
    m_cy = m_roi_cy
    
    current_map = 'jackal'  # 💡 현재 분석 중인 맵 지정
    
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
    
    cv2.circle(result_img, (p_cx, p_cy), 6, (0, 0, 255), -1) 
    cv2.circle(result_img, (m_cx, m_cy), 6, (0, 0, 255), -1) 
    cv2.line(result_img, (p_cx, p_cy), (m_cx, m_cy), (0, 255, 255), 2)

    p_text = f"{player_z:.1f}m"
    m_text = f"{marker_z:.1f}m"
    
    for text, (cx, cy) in [(p_text, (p_cx, p_cy)), (m_text, (m_cx, m_cy))]:
        cv2.putText(result_img, text, (cx + 15, cy - 15), font, 0.6, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(result_img, text, (cx + 15, cy - 15), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

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
    print("[완료] 결과가 'result.png'에 업데이트되었습니다.")


def main():
    print("==================================================")
    print(f" 🎯 배그 박격포 계산기 실시간 모드 작동 중... (모드: {capture.CAPTURE_MODE})")
    if capture.CAPTURE_MODE == "DXGI":
        print(" 게임 설정 상관없이 작동합니다 (전체화면 / 테두리없음).")
    else:
        print(" 인게임 설정을 [테두리 없음] 또는 [창 모드]로 하세요.")
    print("--------------------------------------------------")
    print(" 인게임에서 지도를 열고 [ F8 ] 키를 누르면 계산을 시작합니다.")
    print(" 프로그램 종료는 콘솔 창에서 [ Ctrl + C ]를 누르세요.")
    print("==================================================")

    # F8 키를 누르면 계산기 함수 실행하도록 등록
    keyboard.add_hotkey("F8", run_calculator)

    try:
        # 키 입력 대기 무한 루프
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[종료] 프로그램을 안전하게 종료합니다.")

if __name__ == "__main__":
    main()