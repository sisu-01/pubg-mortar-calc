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
from tts import speak  # 💡 tts.py에서 speak 함수를 불러옵니다.

# --- 💡 글로벌 변수 선언 및 초기값 설정 ---
current_map = 'erangel'
is_selecting_map = False      # F7을 눌러 맵 선택 모드인지 여부를 체크하는 플래그
last_calculated_distance = None

# 맵 순서 정의 (1~6번 매핑용)
MAP_LIST = ['erangel', 'miramar', 'vikendi', 'sanhok', 'karakin', 'jackal']

def start_map_selection():
    """F7 키 입력 시 맵 선택 모드로 진입"""
    global is_selecting_map
    is_selecting_map = True
    print("\n==================================================")
    print(" 🗺️ [맵 선택 모드] 숫자 1 ~ 6을 눌러 선택하세요.")
    print(" 1: Erangel  | 2: Miramar | 3: Vikendi")
    print(" 4: Sanhok   | 5: Karakin | 6: Jackal")
    print("==================================================")
    speak("Select map")

def select_map_by_number(number):
    """숫자 1~6 입력 시 호출되어 전역 current_map을 변경"""
    global current_map, is_selecting_map
    
    # 맵 선택 모드일 때만 숫자 단축키 작동
    if is_selecting_map:
        idx = number - 1
        if 0 <= idx < len(MAP_LIST):
            current_map = MAP_LIST[idx]
            print(f"\n[변경 완료] 🗺️ 현재 타겟 맵이 [ {current_map.upper()} ] (으)로 변경되었습니다.")
            print("이제 지도를 켜고 [ F8 ]을 누르면 해당 맵 기준으로 계산합니다.")
            speak(current_map.upper())
            is_selecting_map = False # 선택이 끝나면 모드 탈출

def replay_last_distance():
    """F9를 누르면 마지막으로 계산된 거리를 다시 영어로 브리핑"""
    global last_calculated_distance
    
    if last_calculated_distance is not None:
        # pydub 배속이 걸려있으므로 "350 meters"가 0.5초만에 찰지게 뿜어져 나옵니다.
        speak(f"{last_calculated_distance} meters")
    else:
        # 아직 계산된 거리가 없을 때 F9를 누른 경우 예외 처리
        speak("No")

def run_calculator(test=False):
    """F8 키 입력 시 실행될 박격포 연산 메인 로직"""
    global current_map
    
    print(f"\n[{time.strftime('%H:%M:%S')}] 🎯 F8 감지! [ {current_map.upper()} ] 화면 분석을 시작합니다...")
    speak("shot")

    # 1. 실시간 이미지 로드 (capture 모듈 호출)
    if test:
        src_img = cv2.imread('image/image.png')
    else:
        src_img = capture.get_screenshot()
    if src_img is None:
        print("[오류] 화면을 캡처하지 못했습니다.")
        speak("screen capture error")
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
        speak("template image error")
        return

    # 2. 객체 탐지 수행
    scale_range = np.linspace(0.1, 1.0, 45)[::-1]
    match_p = find_marker_multi_scale(map_roi_cleaned, tpl_player, scale_range)
    match_m = find_marker_multi_scale(map_roi_cleaned, tpl_marker, scale_range)

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
    
    # 💡 하드코딩 구문을 지우고 전역변수 current_map을 사용하도록 연동
    heightmap_path = f"image/heightmap/{current_map}_heightmap.png"
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
    
    if isinstance(final_mortar_dist, (int, float)):
        cv2.putText(result_img, f"🎯 IN-GAME DIST: {final_mortar_dist}m", (20, 120), font, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        print(f"🎯 [계산 완료] 맵:{current_map.upper()}, 수평:{x_dist:.1f}m, 고도차:{h_diff:.1f}m (P:{player_z:.1f}m / M:{marker_z:.1f}m) -> 조준:{final_mortar_dist}m")

        global last_calculated_distance
        last_calculated_distance = final_mortar_dist

        speak(f"{final_mortar_dist} meters")

    # 반환된 값이 숫자가 아닌 경우 (사격 불가능 케이스)
    else:
        # 상황별 화면 텍스트 및 음성 멘트 분기
        if final_mortar_dist == "TOO_FAR":
            display_msg = "🎯 DIST: TOO FAR / TOO HIGH"
            voice_msg = "too far"
            print("❌ 발사 불가능: 목표가 너무 멀거나 높습니다.")
            
        elif final_mortar_dist == "TOO_CLOSE":
            display_msg = "🎯 DIST: TOO CLOSE"
            voice_msg = "too close"
            print("❌ 발사 불가능: 목표가 최소 사거리보다 가깝습니다.")
            
        else:  # "INVALID_DISTANCE_ZERO" 등 기타 예외
            display_msg = "🎯 DIST: INVALID"
            voice_msg = "impossible"
            print("❌ 발사 불가능: 잘못된 거리 데이터입니다.")

        # OpenCV 화면 출력 및 음성 출력 (빨간색 글씨)
        cv2.putText(result_img, display_msg, (20, 120), font, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        speak(voice_msg)

    cv2.imwrite("result.png", result_img)
    print("[완료] 결과가 'result.png'에 업데이트되었습니다.")


def main(test=False):
    if test:
        run_calculator(test)
        import sys
        sys.exit(0)
    print("==================================================")
    print(f" 🎯 배그 박격포 계산기 실시간 모드 작동 중... (모드: {capture.CAPTURE_MODE})")
    if capture.CAPTURE_MODE == "DXGI":
        print(" 게임 설정 상관없이 작동합니다 (전체화면 / 테두리없음).")
    else:
        print(" 인게임 설정을 [테두리 없음] 또는 [창 모드]로 하세요.")
    print("--------------------------------------------------")
    print(f" 기본 선택된 맵: [ {current_map.upper()} ]")
    print(" 🗺️ 다른 맵 선택하기: [ F7 ] 누른 후 숫자 [ 1 ~ 6 ] 선택")
    print(" 🎯 박격포 고도 계산: 지도를 열고 [ F8 ] 누르기")
    print(" 프로그램 종료는 콘솔 창에서 [ Ctrl + C ]를 누르세요.")
    print("==================================================")

    
    # 💡 2. 숫자 1~6 입력 이벤트 바인딩 (람다식을 활용해 해당 숫자 매핑)
    for i in range(1, 7):
        keyboard.add_hotkey(str(i), lambda n=i: select_map_by_number(n))

    # 💡 1. 맵 선택 변경 인터페이스 단축키 등록
    keyboard.add_hotkey("F7", start_map_selection)
    # 3. 실시간 박격포 연산 핫키 등록
    keyboard.add_hotkey("F8", run_calculator)
    # 💡 [추가] F9 키를 누르면 위 함수가 실행되도록 바인딩
    keyboard.add_hotkey('F9', replay_last_distance)    

    try:
        # 키 입력 대기 무한 루프
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[종료] 프로그램을 안전하게 종료합니다.")

if __name__ == "__main__":
    main(True)