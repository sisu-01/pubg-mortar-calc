# detector.py
import cv2
import numpy as np

def find_marker_multi_scale(screenshot_gray, template_gray, scale_range):
    """기존 플레이어 탐지용 다중 스케일 템플릿 매칭 (흑백)"""
    best_match = None
    template_h, template_w = template_gray.shape[:2]

    for scale in scale_range:
        w = int(template_w * scale)
        h = int(template_h * scale)

        if w < 10 or h < 10:
            continue

        resized_template = cv2.resize(template_gray, (w, h), interpolation=cv2.INTER_AREA)
        res = cv2.matchTemplate(screenshot_gray, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if best_match is None or max_val > best_match["max_val"]:
            best_match = {
                "max_val": max_val,
                "max_loc": max_loc,
                "w": w,
                "h": h,
            }
    return best_match


def find_color_marker_multi_scale(screenshot_color, template_image, scale_range, target_hex):
    """
    특정 단색 마커만 필터링하여 다중 스케일 템플릿 매칭을 수행합니다.
    변형 및 압축이 없는 깨끗한 이미지이므로 HEX 값의 오차 범위를 아주 좁게 주어 처리합니다.
    """
    best_match = None
    
    # 1. HEX 코드를 BGR 값으로 변환
    r = int(target_hex[0:2], 16)
    g = int(target_hex[2:4], 16)
    b = int(target_hex[4:6], 16)
    
    tol = 0 # tolerance(허용 오차)
    lower_bound = np.array([max(0, b-tol), max(0, g-tol), max(0, r-tol)], dtype=np.uint8)
    upper_bound = np.array([min(255, b+tol), min(255, g+tol), min(255, r+tol)], dtype=np.uint8)

    # 3. 마스킹 수행
    mask_src = cv2.inRange(screenshot_color, lower_bound, upper_bound)
    # 4. 템플릿 이미지도 똑같이 해당 색상만 남기도록 흑백 마스크화
    # mask_tpl = cv2.inRange(template_color, lower_bound, upper_bound)

    cv2.imwrite("mask_src.png", mask_src)
    cv2.imwrite("mask_tpl.png", template_image)

    template_h, template_w = template_image.shape[:2]

    # 5. 추출된 단색 마스크(흑백 구조)를 기반으로 다중 스케일 템플릿 매칭 진행
    for scale in scale_range:
        w = int(template_w * scale)
        h = int(template_h * scale)

        if w < 10 or h < 10:
            continue

        resized_template = cv2.resize(template_image, (w, h), interpolation=cv2.INTER_AREA)
        
        # 스크린샷 마스크 이미지와 템플릿 마스크 이미지를 매칭합니다.
        res = cv2.matchTemplate(mask_src, resized_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        if best_match is None or max_val > best_match["max_val"]:
            best_match = {
                "max_val": max_val,
                "max_loc": max_loc,
                "w": w,
                "h": h,
            }
            
    return best_match