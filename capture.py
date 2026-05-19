# capture.py
import cv2
import dxcam
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
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    else:
        print("[오류] DXGI 프레임을 가져오지 못했습니다. 다시 시도해주세요.")
        return None

def capture_by_gdi():
    """GDI 방식을 이용한 화면 캡처 (윈도우 핸들 기준 스크랩)"""
    game_title = "PLAYERUNKNOWN'S BATTLEGROUNDS"
    hwnd = win32gui.FindWindow(None, game_title)

    if not hwnd:
        hwnd = win32gui.GetDesktopWindow()

    rect = win32gui.GetWindowRect(hwnd)
    x = rect[0]
    y = rect[1]
    w = rect[2] - x
    h = rect[3] - y

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()

    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    saveDC.BitBlt((0, 0), (w, h), mfcDC, (0, 0), win32con.SRCCOPY)

    signedIntsArray = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(signedIntsArray, dtype="uint8")
    img.shape = (h, w, 4)

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

def get_screenshot():
    """설정된 모드에 따라 캡처 후 BGR 이미지를 반환하는 메인 인터페이스 함수"""
    if CAPTURE_MODE == "DXGI":
        return capture_by_dxgi()
    elif CAPTURE_MODE == "GDI":
        return capture_by_gdi()
    else:
        print(f"[오류] 잘못된 설정값입니다. CAPTURE_MODE를 'DXGI' 또는 'GDI'로 변경하세요.")
        return None