import os
import time
import cv2
import dxcam
import keyboard
import numpy as np
import win32con
import win32gui
import win32ui

# ==========================================
# [설정값] 캡처 모드를 설정하세요.
# "DXGI" : 전체화면/테두리없음용 (배그 안티치트 우회, 추천)
# "GDI"  : 창모드/테두리없음용 (win32 API 방식)
# ==========================================
CAPTURE_MODE = "GDI"

# DXGI 전역 카메라 객체 초기화 (DXGI 모드일 때만 생성)
camera = dxcam.create() if CAPTURE_MODE == "DXGI" else None

def capture_by_dxgi():
    """DXGI 방식을 이용한 화면 캡처 (VRAM에서 직접 복사)"""
    if camera is None:
        print("[오류] DXGI 카메라 객체가 초기화되지 않았습니다.")
        return None

    frame = camera.grab()
    if frame is not None:
        # dxcam의 RGB 배열을 OpenCV 표준 BGR로 변환
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        print("[오류] DXGI 프레임을 가져오지 못했습니다. 다시 시도해주세요.")
        return None


def capture_by_gdi():
    """GDI 방식을 이용한 화면 캡처 (윈도우 핸들 기준 스크랩)"""
    game_title = "PLAYERUNKNOWN'S BATTLEGROUNDS"
    hwnd = win32gui.FindWindow(None, game_title)

    if not hwnd:
        print(
            "[경고] 배그 창을 찾을 수 없습니다. 전체 화면(주 모니터) 전체를 캡처합니다."
        )
        hwnd = win32gui.GetDesktopWindow()

    # 창 크기 가져오기
    rect = win32gui.GetWindowRect(hwnd)
    x = rect[0]
    y = rect[1]
    w = rect[2] - x
    h = rect[3] - y

    # GDI 오브젝트 생성 및 메모리 디바이스 컨텍스트(DC) 매칭
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    # 데이터 비트맵 복사
    saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

    # numpy 배열로 변환하여 OpenCV가 읽을 수 있도록 가공
    signedIntsArray = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype="uint8")
    img.shape = (h, w, 4)

    # 리소스 해제 (메모리 누수 방지)
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    # RGBA -> BGR 변환 (투명도 채널 제거)
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def handle_capture():
    """F8 핫키 감지 시 설정된 모드에 따라 캡처 프로세스를 처리하는 메인 핸들러"""
    print(
        f"\n[{time.strftime('%H:%M:%S')}] F8 감지! ({CAPTURE_MODE} 방식 캡처 중...)"
    )

    # 설정값에 따른 분기 처리
    if CAPTURE_MODE == "DXGI":
        frame_bgr = capture_by_dxgi()
    elif CAPTURE_MODE == "GDI":
        frame_bgr = capture_by_gdi()
    else:
        print(
            f"[오류] 잘못된 설정값입니다. CAPTURE_MODE를 'DXGI' 또는 'GDI'로 변경하세요."
        )
        return

    # 이미지 저장 처리
    if frame_bgr is not None:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"battleground_{CAPTURE_MODE.lower()}_{timestamp}.png"

        cv2.imwrite(filename, frame_bgr)
        print(f"[성공] 안전하게 화면이 저장되었습니다: {filename}")


def main():
    print("==================================================")
    print(f" 배그 안심 [ {CAPTURE_MODE} + F8 ] 캡처 프로그램 작동 중...")

    if CAPTURE_MODE == "DXGI":
        print(" 게임이 [전체 화면]이든 [테두리 없음]이든 잘 작동합니다.")
    else:
        print(" 인게임 설정을 [테두리 없음] 또는 [창 모드]로 하세요.")

    print("--------------------------------------------------")
    print(" 인게임에서 [ F8 ] 키를 누르면 화면을 저장합니다.")
    print(" 프로그램 종료는 콘솔 창에서 [ Ctrl + C ]를 누르세요.")
    print("==================================================")

    # F8 키 매핑
    keyboard.add_hotkey("F8", handle_capture)

    try:
        # 키 입력 무한 대기
        keyboard.wait()
    except KeyboardInterrupt:
        print("\n[종료] 프로그램을 안전하게 종료합니다.")

if __name__ == "__main__":
    main()