import cv2
import numpy as np

def crop_and_remove_pubg_grid_perfect(image_path, grid_mode=8, output_path="final_removed_grid.png"):
    """
    16:9 배그 스크린샷 화면 중앙에서 1:1 지도를 자른 뒤,
    2px 두께의 내부 격자선을 양옆/위아래 주변 배경 픽셀로 덮어써서 격자를 제거하는 함수.
    
    - 세로 격자선 2px: 왼쪽 1px은 왼쪽 픽셀, 오른쪽 1px은 오른쪽 픽셀로 복사
    - 가로 격자선 2px: 위쪽 1px은 위쪽 픽셀, 아래쪽 1px은 아래쪽 픽셀로 복사
    """
    # 1. 원본 이미지 불러오기
    img = cv2.imread(image_path)
    if img is None:
        print(f"에러: 이미지를 불러올 수 없습니다. 경로 확인: {image_path}")
        return False
    
    # 2. 16:9 화면 중앙에서 1:1 지도 영역 크롭 (Crop)
    height, width, _ = img.shape
    map_size = height  # 지도의 한 변 길이는 화면 높이와 동일
    
    start_x = (width - map_size) // 2
    end_x = start_x + map_size
    
    # 중앙 1:1 영역 자르기
    cropped_map = img[0:height, start_x:end_x].copy()
    
    # 3. 격자 모드에 따른 선의 개수 설정
    if grid_mode == 8:
        lines_count = 7
    elif grid_mode == 4:
        lines_count = 3
    elif grid_mode == 2:
        lines_count = 1
    else:
        print("에러: 지원하지 않는 격자 모드입니다. (2, 4, 8 중 선택)")
        return False

    # 4. 정밀 공식을 통한 한 칸의 순수 크기(block_size) 계산
    total_grid_thickness = 2 * lines_count
    pure_playable_space = map_size - 2 - total_grid_thickness
    block_size = pure_playable_space / (lines_count + 1)

    # 5. 누적 좌표를 계산하여 격자선 지우기 작업 진행
    for i in range(1, lines_count + 1):
        # i번째 격자선의 시작 위치 (2px 중 첫 번째 픽셀의 인덱스)
        start_pos = 1 + int(round((block_size * i) + (2 * (i - 1))))
        
        p1 = start_pos      # 격자선의 왼쪽 / 위쪽 1px
        p2 = start_pos + 1  # 격자선의 오른쪽 / 아래쪽 1px

        # --- 세로 격자선 지우기 (배경색 덮어쓰기) ---
        # 가장자리 1px 검은 테두리(0번, map_size-1번 픽셀)는 건드리지 않음
        if 1 <= p1 < map_size - 1:
            # p1(왼쪽선)은 그 왼쪽인 p1 - 1의 픽셀값으로 채움
            cropped_map[1:map_size-1, p1] = cropped_map[1:map_size-1, p1 - 1]
        
        if 1 <= p2 < map_size - 1:
            # p2(오른쪽선)는 그 오른쪽인 p2 + 1의 픽셀값으로 채움
            cropped_map[1:map_size-1, p2] = cropped_map[1:map_size-1, p2 + 1]

        # --- 가로 격자선 지우기 (배경색 덮어쓰기) ---
        if 1 <= p1 < map_size - 1:
            # p1(위쪽선)은 그 위쪽인 p1 - 1의 픽셀값으로 채움
            cropped_map[p1, 1:map_size-1] = cropped_map[p1 - 1, 1:map_size-1]
            
        if 1 <= p2 < map_size - 1:
            # p2(아래쪽선)는 그 아래쪽인 p2 + 1의 픽셀값으로 채움
            cropped_map[p2, 1:map_size-1] = cropped_map[p2 + 1, 1:map_size-1]

    # 6. 최종 결과 저장
    cv2.imwrite(output_path, cropped_map)
    print(f"성공: 지도 크롭 및 {grid_mode}x{grid_mode} 격자 완벽 제거 완료!")
    print(f"저장 위치: {output_path} (크기: {map_size}x{map_size})")
    return True