import cv2

# 1. 이미지 불러오기
image_path = "images/screenshot.png"  # 원본 이미지 파일명
img = cv2.imread(image_path)

if img is None:
    print(f"이미지를 찾을 수 없습니다: {image_path}")
else:
    # 2. 이미지의 실제 해상도 가져오기 (1920x1080, 3840x2160 등 자동 대응)
    height, width, _ = img.shape
    print(f"입력 이미지 해상도: {width}x{height}")
    
    # 3. 1920x1080 기준으로 계산한 비율 적용
    margin_right_ratio = 31 / 1920
    margin_bottom_ratio = 28 / 1080
    
    minimap_width_ratio = 461 / 1920
    minimap_height_ratio = 461 / 1080
    
    # 4. 현재 해상도에 맞는 픽셀 값으로 변환 (오타 수정 완료 ✨)
    current_margin_right = int(round(width * margin_right_ratio))
    current_margin_bottom = int(round(height * margin_bottom_ratio))
    current_minimap_width = int(round(width * minimap_width_ratio))
    current_minimap_height = int(round(height * minimap_height_ratio))  # 이 부분이 수정되었습니다.
    
    # 5. 최종 슬라이싱 좌표 계산
    x_end = width - current_margin_right
    x_start = x_end - current_minimap_width
    
    y_end = height - current_margin_bottom
    y_start = y_end - current_minimap_height
    
    # 6. 이미지 자르기 및 저장
    minimap = img[y_start:y_end, x_start:x_end]
    
    output_path = "images/minimap_cropped_ratio.png"
    cv2.imwrite(output_path, minimap)
    print(f"잘라낸 미니맵 크기: {minimap.shape[1]}x{minimap.shape[0]}")
    print(f"미니맵이 성공적으로 저장되었습니다: {output_path}")