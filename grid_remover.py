# grid_remover.py
import cv2
import numpy as np

def remove_pubg_grid(img_gray, grid_mode=8):
    """
    그레이스케일 지도 ROI 이미지에서 2px 두께의 내부 격자선을 
    양옆/위아래 주변 배경 픽셀로 덮어써서 완벽하게 제거합니다.
    
    Args:
        img_gray (numpy.ndarray): 전처리된 그레이스케일 지도 ROI 이미지 (1:1 비율)
        grid_mode (int): 격자 모드 (2, 4, 8 중 선택)
        
    Returns:
        numpy.ndarray: 격자선이 완벽히 마스킹 지워진 깨끗한 그레이스케일 이미지
    """
    map_size = img_gray.shape[0]
    cleaned_map = img_gray.copy()
    
    # 격자 모드에 따른 선의 개수 설정
    if grid_mode == 8:
        lines_count = 7
    elif grid_mode == 4:
        lines_count = 3
    elif grid_mode == 2:
        lines_count = 1
    else:
        # 지원하지 않는 모드일 경우 예외 처리로서 가공 없이 원본 반환
        return cleaned_map

    # 정밀 공식을 통한 한 칸의 순수 크기(block_size) 계산
    total_grid_thickness = 2 * lines_count
    pure_playable_space = map_size - 2 - total_grid_thickness
    block_size = pure_playable_space / (lines_count + 1)

    # 누적 좌표를 계산하여 격자선 지우기 작업 진행
    for i in range(1, lines_count + 1):
        # i번째 격자선의 시작 위치 (2px 중 첫 번째 픽셀의 인덱스)
        start_pos = 1 + int(round((block_size * i) + (2 * (i - 1))))
        
        p1 = start_pos      # 격자선의 왼쪽 / 위쪽 1px
        p2 = start_pos + 1  # 격자선의 오른쪽 / 아래쪽 1px

        # --- 세로 격자선 지우기 (배경색 덮어쓰기) ---
        if 1 <= p1 < map_size - 1:
            cleaned_map[1:map_size-1, p1] = cleaned_map[1:map_size-1, p1 - 1]
        
        if 1 <= p2 < map_size - 1:
            cleaned_map[1:map_size-1, p2] = cleaned_map[1:map_size-1, p2 + 1]

        # --- 가로 격자선 지우기 (배경색 덮어쓰기) ---
        if 1 <= p1 < map_size - 1:
            cleaned_map[p1, 1:map_size-1] = cleaned_map[p1 - 1, 1:map_size-1]
            
        if 1 <= p2 < map_size - 1:
            cleaned_map[p2, 1:map_size-1] = cleaned_map[p2 + 1, 1:map_size-1]

    return cleaned_map