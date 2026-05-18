# detector.py
import cv2
import numpy as np

def find_marker_multi_scale(screenshot_gray, template_gray, scale_range):
    """다중 스케일 템플릿 매칭을 통해 최적의 객체 위치를 탐지합니다."""
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