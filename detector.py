# detector.py
import cv2
import numpy as np

def find_markers_simultaneously(screenshot_color, tpl_player, tpl_marker, scale_range, player_hex, marker_hex):
    """
    마스크 추출 및 외곽선 탐지를 최초 1회만 수행하고,
    루프를 돌며 플레이어와 마커를 동시에 찾아 연산량을 절반으로 줄입니다.
    """
    best_player = None
    best_marker = None

    # 1. 두 타겟 색상에 대한 개별 마스크 생성
    # (플레이어와 마커 색상이 다를 수 있으므로 마스킹은 각각 하되, 전체 화면 기준 1번씩만 수행)
    def get_mask(hex_str):
        r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
        tol = 50
        lower = np.array([max(0, b-tol), max(0, g-tol), max(0, r-tol)], dtype=np.uint8)
        upper = np.array([min(255, b+tol), min(255, g+tol), min(255, r+tol)], dtype=np.uint8)
        return cv2.inRange(screenshot_color, lower, upper)

    mask_p_src = get_mask(player_hex)
    mask_m_src = get_mask(marker_hex)

    # 2. 템플릿 비율 미리 계산
    p_h, p_w = tpl_player.shape[:2]
    m_h, m_w = tpl_marker.shape[:2]

    # ---------------------------------------------------------
    # PART A: 플레이어 탐색 (Player 마스크 기반)
    # ---------------------------------------------------------
    contours_p, _ = cv2.findContours(mask_p_src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours_p:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 10 or h < 10: continue
        
        # 가로세로 비율 검증 (플레이어는 1:1 근처여야 함)
        if w / h <= 0.88: 
            continue  # 세로로 긴 형태(마커)는 플레이어가 아니므로 패스

        # 합격한 덩어리 구역 매칭
        roi_y1, roi_y2 = max(0, y - 5), min(mask_p_src.shape[0], y + h + 5)
        roi_x1, roi_x2 = max(0, x - 5), min(mask_p_src.shape[1], x + w + 5)
        roi_src = mask_p_src[roi_y1:roi_y2, roi_x1:roi_x2]

        for scale in scale_range:
            tw, th = int(p_w * scale), int(p_h * scale)
            if tw < 10 or th < 10 or tw > roi_src.shape[1] or th > roi_src.shape[0]: continue

            resized_tpl = cv2.resize(tpl_player, (tw, th), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(roi_src, resized_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if best_player is None or max_val > best_player["max_val"]:
                best_player = {
                    "max_val": max_val,
                    "max_loc": (roi_x1 + max_loc[0], roi_y1 + max_loc[1]),
                    "w": tw, "h": th
                }

    # ---------------------------------------------------------
    # PART B: 마커 탐색 (Marker 마스크 기반)
    # ---------------------------------------------------------
    contours_m, _ = cv2.findContours(mask_m_src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours_m:
        x, y, w, h = cv2.boundingRect(contour)
        if w < 10 or h < 10: continue
        
        # 가로세로 비율 검증 (마커는 세로로 길어야 함)
        if w / h > 0.88: 
            continue  # 1:1에 가까운 형태(플레이어)는 마커가 아니므로 패스

        # 합격한 덩어리 구역 매칭
        roi_y1, roi_y2 = max(0, y - 5), min(mask_m_src.shape[0], y + h + 5)
        roi_x1, roi_x2 = max(0, x - 5), min(mask_m_src.shape[1], x + w + 5)
        roi_src = mask_m_src[roi_y1:roi_y2, roi_x1:roi_x2]

        for scale in scale_range:
            tw, th = int(m_w * scale), int(m_h * scale)
            if tw < 10 or th < 10 or tw > roi_src.shape[1] or th > roi_src.shape[0]: continue

            resized_tpl = cv2.resize(tpl_marker, (tw, th), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(roi_src, resized_tpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)

            if best_marker is None or max_val > best_marker["max_val"]:
                best_marker = {
                    "max_val": max_val,
                    "max_loc": (roi_x1 + max_loc[0], roi_y1 + max_loc[1]),
                    "w": tw, "h": th
                }

    # 두 결과를 튜플 형태로 동시에 반환합니다.
    return best_player, best_marker