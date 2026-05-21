# detector.py
import cv2
import numpy as np
from config import TOL

def find_markers_simultaneously(screenshot_color, tpl_player, tpl_marker, scale_range, target_hex):
    """
    플레이어와 마커가 동일한 가변 색상을 공유하므로,
    마스크 생성과 외곽선(Contour) 탐지를 딱 '1번'만 수행하여 동시에 모두 찾아냅니다.
    """
    best_player = None
    best_marker = None

    # 1. HEX 코드를 BGR 값으로 변환
    r = int(target_hex[0:2], 16)
    g = int(target_hex[2:4], 16)
    b = int(target_hex[4:6], 16)
    
    lower_bound = np.array([max(0, b-TOL), max(0, g-TOL), max(0, r-TOL)], dtype=np.uint8)
    upper_bound = np.array([min(255, b+TOL), min(255, g+TOL), min(255, r+TOL)], dtype=np.uint8)

    # 2. 공통 색상 마스크 생성 (딱 1번만 연산)
    mask_src = cv2.inRange(screenshot_color, lower_bound, upper_bound)
    cv2.imwrite("images/debug/1_no_morph_mask_src.png", mask_src)
    # 타원형 커널 정의 (원형/물방울 마커용 추천)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    # 2. [늘리기 단계] 팽창(Dilation) 연산 수행 및 저장
    # 주변의 빈틈이나 구멍을 메우기 위해 흰색 영역이 확장된 상태입니다.
    mask_dilated = cv2.dilate(mask_src, kernel, iterations=1)
    cv2.imwrite("images/debug/2_dilated_mask_src.png", mask_dilated)
    # 3. [줄이기 단계] 침식(Erosion) 연산 수행 및 저장 (최종 결과물)
    # 늘어난 외곽선을 다시 원상복구하여 형태를 다듬은 상태입니다.
    mask_src = cv2.erode(mask_dilated, kernel, iterations=1)
    cv2.imwrite("images/debug/3_yes_morph_mask_src.png", mask_src)

    # 3. 템플릿 정보 로드
    p_h, p_w = tpl_player.shape[:2]
    m_h, m_w = tpl_marker.shape[:2]

    # 4. 마스크 내부에서 해당 색상을 가진 모든 덩어리 추출 (딱 1번만 연산)
    contours, _ = cv2.findContours(mask_src, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 5. 발견된 덩어리들을 루프 돌며 '비율'에 따라 즉석 분류 및 매칭
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        
        # 노이즈 제거
        if w < 10 or h < 10: 
            continue
            
        # 현재 덩어리의 가로세로 비율
        src_aspect_ratio = w / h

        # 사각형 주변에 여유 마진(+5, -5)을 주어 ROI 잘라내기
        roi_y1 = max(0, y - 5)
        roi_y2 = min(mask_src.shape[0], y + h + 5)
        roi_x1 = max(0, x - 5)
        roi_x2 = min(mask_src.shape[1], x + w + 5)
        roi_src = mask_src[roi_y1:roi_y2, roi_x1:roi_x2]

        # ---------------------------------------------------------
        # 분류항목 A: 비율이 1:1에 가까우면 '플레이어'로 판단하고 매칭
        # ---------------------------------------------------------
        if src_aspect_ratio > 0.88:
            for scale in scale_range:
                tw, th = int(p_w * scale), int(p_h * scale)
                if tw < 10 or th < 10 or tw > roi_src.shape[1] or th > roi_src.shape[0]: 
                    continue

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
        # 분류항목 B: 비율이 세로로 길면 '마커'로 판단하고 매칭
        # ---------------------------------------------------------
        else:
            for scale in scale_range:
                tw, th = int(m_w * scale), int(m_h * scale)
                if tw < 10 or th < 10 or tw > roi_src.shape[1] or th > roi_src.shape[0]: 
                    continue

                resized_tpl = cv2.resize(tpl_marker, (tw, th), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(roi_src, resized_tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)

                if best_marker is None or max_val > best_marker["max_val"]:
                    best_marker = {
                        "max_val": max_val,
                        "max_loc": (roi_x1 + max_loc[0], roi_y1 + max_loc[1]),
                        "w": tw, "h": th
                    }

    # 최종 결과 반환
    return best_player, best_marker