# main.py
import time
import cv2
import numpy as np
import keyboard
import config
from detector import find_markers_simultaneously
from ballistics import get_mortar_in_game_distance, calculate_physical_distance, get_absolute_height
from grid_remover import remove_pubg_grid

import capture
from tts import speak  

# --- 💡 글로벌 변수 선언 및 초기값 설정 ---
current_map = 'jackal'
current_color_idx = 0  # 기본값: 0번 (Yellow)

is_selecting_map = False      
is_selecting_color = False

last_calculated_distance = None

def start_map_selection():
    """F7 키 입력 시 맵 선택 모드로 진입"""
    global is_selecting_map, is_selecting_color
    is_selecting_map = True
    is_selecting_color = False  # 색상 선택 모드 해제
    print("\n==================================================")
    print(" 🗺️ [맵 선택 모드] 숫자 1 ~ 6을 눌러 선택하세요.")
    print(" 1: Erangel  | 2: Miramar | 3: Vikendi")
    print(" 4: Sanhok   | 5: Karakin | 6: Jackal")
    print("==================================================")
    speak("Select map")


def select_map_by_number(number):
    """숫자 1~6 입력 시 호출되어 전역 current_map을 변경"""
    global current_map, is_selecting_map
    if is_selecting_map:
        idx = number - 1
        if 0 <= idx < len(config.MAP_LIST):
            current_map = config.MAP_LIST[idx]
            print(f"\n[변경 완료] 🗺️ 현재 타겟 맵이 [ {current_map.upper()} ] (으)로 변경되었습니다.")
            speak(current_map.upper())
            is_selecting_map = False 


def start_color_selection():
    """F6 키 입력 시 마커 색상 선택 모드로 진입"""
    global is_selecting_color, is_selecting_map
    is_selecting_color = True
    is_selecting_map = False  # 맵 선택 모드 해제
    print("\n==================================================")
    print(" 🎨 [마커 색상 선택 모드] 숫자 1 ~ 4를 눌러 선택하세요.")
    print(" 1: Yellow (e9e511) | 2: Pink (ff00ff)")
    print(" 3: Red (ff0000)    | 4: Blue (0000ff)")
    print("==================================================")
    speak("Select color")


def select_shortcut_handler(number):
    """숫자 1~6 키가 눌렸을 때 현재 모드(맵 선택 vs 색상 선택)에 따라 분기 처리"""
    global is_selecting_map, is_selecting_color, current_color_idx
    
    if is_selecting_map:
        select_map_by_number(number)
    elif is_selecting_color:
        idx = number - 1
        if 0 <= idx < len(config.COLOR_LIST):
            current_color_idx = idx
            selected_name = config.COLOR_NAMES[idx]
            print(f"\n[변경 완료] 🎨 타겟 마커 색상이 [ {selected_name} ] (# {config.COLOR_LIST[idx]}) 로 변경되었습니다.")
            speak(selected_name)
            is_selecting_color = False


def replay_last_distance():
    """F9를 누르면 마지막으로 계산된 거리를 다시 브리핑"""
    global last_calculated_distance
    if last_calculated_distance is not None:
        speak(f"{last_calculated_distance} meters")
    else:
        speak("No")


def run_calculator(test=False):
    """F8 키 입력 시 실행될 박격포 연산 메인 로직"""
    global current_map, current_color_idx
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🎯 F8 감지! [ {current_map.upper()} ] 화면 분석을 시작합니다... (타겟 색상: {config.COLOR_NAMES[current_color_idx]})")
    speak("shot")

    # 1. 실시간 이미지 로드
    if test:
        src_img = cv2.imread('images/image.png')
    else:
        src_img = capture.get_screenshot()
        
    if src_img is None:
        print("[오류] 화면을 캡처하지 못했습니다.")
        speak("screen capture error")
        return

    h, w, _ = src_img.shape
    map_size = h
    start_x = (w - map_size) // 2

    # 마커 탐지를 위해 컬러 ROI 쪼개기
    color_map_roi = src_img[0:h, start_x : start_x + map_size].copy()
    color_map_cleaned = remove_pubg_grid(color_map_roi, grid_mode=8)
    
    tpl_player = cv2.imread("images/templates/player.png", cv2.IMREAD_GRAYSCALE)
    tpl_marker = cv2.imread("images/templates/marker.png", cv2.IMREAD_GRAYSCALE)

    if tpl_player is None or tpl_marker is None:
        print("[오류] player.png 또는 marker.png 템플릿 이미지를 확인하세요.")
        speak("template image error")
        return

    # 2. 객체 탐지 수행
    scale_range = np.linspace(0.1, 1.0, 45)[::-1]

    target_hex = config.COLOR_LIST[current_color_idx]

    match_p, match_m = find_markers_simultaneously(
        color_map_cleaned, 
        tpl_player, 
        tpl_marker, 
        scale_range, 
        target_hex
    )

    # config의 MATCH_THRESHOLD 사용
    if not (match_p and match_p["max_val"] >= config.MATCH_THRESHOLD) or not (match_m and match_m["max_val"] >= config.MATCH_THRESHOLD):
        print(f"❌ 플레이어 또는 마커를 화면에서 찾을 수 없습니다. (현재 선택 맵: {current_map.upper()})")
        speak("no marker")
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
    
    heightmap_path = f"images/heightmap/{current_map}_heightmap.png"
    heightmap = cv2.imread(heightmap_path, cv2.IMREAD_UNCHANGED)
    if heightmap is None:
        print(f"[오류] 하이트맵 이미지({heightmap_path})를 로드할 수 없습니다. 파일명을 확인해 주세요.")
        speak("heightmap error")
        return
        
    hm_h, hm_w = heightmap.shape[:2]
    p_hx = max(0, min(int(p_rx * (hm_w - 1)), hm_w - 1))
    p_hy = max(0, min(int(p_ry * (hm_h - 1)), hm_h - 1))
    m_hx = max(0, min(int(m_rx * (hm_w - 1)), hm_w - 1))
    m_hy = max(0, min(int(m_ry * (hm_h - 1)), hm_h - 1))

    scale_xy = config.MAP_SCALES.get(current_map, 0.9765625)
    
    x_dist = calculate_physical_distance(p_hx, p_hy, m_hx, m_hy, scale_xy)
    player_z = get_absolute_height(heightmap, p_hx, p_hy)
    marker_z = get_absolute_height(heightmap, m_hx, m_hy)
    h_diff = marker_z - player_z

    final_mortar_dist = get_mortar_in_game_distance(x_dist, h_diff, config.MORTAR_STEPS)
    
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
    
    if isinstance(final_mortar_dist, (int, float)):
        cv2.putText(result_img, f"🎯 IN-GAME DIST: {final_mortar_dist}m", (20, 120), font, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        print(f"🎯 [계산 완료] 맵:{current_map.upper()}, 수평:{x_dist:.1f}m, 고도차:{h_diff:.1f}m (P:{player_z:.1f}m / M:{marker_z:.1f}m) -> 조준:{final_mortar_dist}m")

        global last_calculated_distance
        last_calculated_distance = final_mortar_dist
        speak(f"{final_mortar_dist} meters")
    else:
        if final_mortar_dist == "TOO_FAR":
            display_msg = "🎯 DIST: TOO FAR / TOO HIGH"
            voice_msg = "too far"
            print("❌ 발사 불가능: 목표가 너무 멀거나 높습니다.")
        elif final_mortar_dist == "TOO_CLOSE":
            display_msg = "🎯 DIST: TOO CLOSE"
            voice_msg = "too close"
            print("❌ 발사 불가능: 목표가 최소 사거리보다 가깝습니다.")
        else:
            display_msg = "🎯 DIST: INVALID"
            voice_msg = "impossible"
            print("❌ 발사 불가능: 잘못된 거리 데이터입니다.")

        cv2.putText(result_img, display_msg, (20, 120), font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        speak(voice_msg)

    cv2.imwrite("images/debug/result.png", result_img)
    print("[완료] 결과가 'images/debug/result.png'에 업데이트되었습니다.")


def main(test=False):
    if test:
        run_calculator(test)
        import sys
        sys.exit(0)
        
    print("==================================================")
    print(f" 🎯 배그 박격포 계산기 실시간 모드 작동 중... (모드: {config.CAPTURE_MODE})")
    print("--------------------------------------------------")
    print(f" 기본 선택된 맵: [ {current_map.upper()} ]")
    print(f" 기본 선택된 색상: [ {config.COLOR_NAMES[current_color_idx]} ]")
    print(" 🎨 다른 마커 선택하기: [ F6 ] 누른 후 숫자 [ 1 ~ 4 ] 선택")
    print(" 🗺️ 다른 맵 선택하기: [ F7 ] 누른 후 숫자 [ 1 ~ 6 ] 선택")
    print(" 🎯 박격포 고도 계산: 지도를 열고 [ F8 ] 누르기")
    print(" 👂 박격포 거리 다시 듣기는 [ F9 ] 누르기")
    print("==================================================")

    # 💡 숫자 1~6 핫키 등록 핸들러 통합 수정
    for i in range(1, 7):
        keyboard.add_hotkey(str(i), lambda n=i: select_shortcut_handler(n))

    # 핫키 등록
    keyboard.add_hotkey("F6", start_color_selection)
    keyboard.add_hotkey("F7", start_map_selection)
    keyboard.add_hotkey("F8", run_calculator, args=[test])
    keyboard.add_hotkey('F9', replay_last_distance)    

    try:
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[종료] 프로그램을 안전하게 종료합니다.")

if __name__ == "__main__":
    main()