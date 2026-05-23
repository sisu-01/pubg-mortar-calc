import os
import json
import re
from PIL import Image

def build_world_heightmap_swapped():
    # 경로 설정
    base_dir = os.getcwd()
    data_dir = os.path.join(base_dir, "data")
    result_dir = os.path.join(base_dir, "result")
    
    # 디버깅용 저장 폴더
    debug_a_dir = os.path.join(result_dir, "debug_A_tiles")
    debug_b_dir = os.path.join(result_dir, "debug_B_sections")
    
    os.makedirs(result_dir, exist_ok=True)
    os.makedirs(debug_a_dir, exist_ok=True)
    os.makedirs(debug_b_dir, exist_ok=True)
    
    if not os.path.exists(data_dir):
        print(f"[-] 에러: {data_dir} 폴더를 찾을 수 없습니다.")
        return

    print("[*] 1단계: /data 폴더 내부 파일 분석 및 그리드 구성 중...")
    
    file_pattern = re.compile(r"Heightmap_x(\d+)_y(\d+)_(\d+)\.json")
    world_grid = {}
    
    for fname in os.listdir(data_dir):
        match = file_pattern.match(fname)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            sub_id = int(match.group(3))
            
            if (x, y) not in world_grid:
                world_grid[(x, y)] = {}
            world_grid[(x, y)][sub_id] = fname

    if not world_grid:
        print("[-] 유효한 Heightmap 설정 파일을 찾지 못했습니다.")
        return

    all_x = [k[0] for k in world_grid.keys()]
    all_y = [k[1] for k in world_grid.keys()]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    
    grid_cols = max_x - min_x + 1
    grid_rows = max_y - min_y + 1
    
    print(f"[+] 총 {len(world_grid)}개의 대형 지역 감지. 범위: X({min_x}~{max_x}), Y({min_y}~{max_y})")

    # 32비트 안전 모드(I)로 마스터 도화지 생성
    final_world_map = Image.new("I", (grid_cols * 2048, grid_rows * 2048))
    tile_pattern = re.compile(r"Landscape_\d+_\d+_Heightmap_\d+")

    for (x, y), subs in world_grid.items():
        print(f"[*] 'B' 이미지 병합 중: [X:{x}, Y:{y}]")
        
        image_B = Image.new("I", (2048, 2048))
        
        # [핵심 수정 1] B(1024x1024) 조각 병합 레이아웃 스왑 완료
        # 기존: 01이 좌하, 02가 우상 -> 수정: 01이 우상, 02가 좌하
        sub_layout = {
            0: (0, 0),       # 00 -> 좌상단
            1: (1024, 0),    # 01 -> 우상단 (스왑됨)
            2: (0, 1024),    # 02 -> 좌하단 (스왑됨)
            3: (1024, 1024)  # 03 -> 우하단
        }
        
        for sub_id in sorted(sub_layout.keys()):
            if sub_id not in subs: continue
                
            json_fname = subs[sub_id]
            json_path = os.path.join(data_dir, json_fname)
            ubulk_path = os.path.join(data_dir, json_fname.replace(".json", ".ubulk"))
            
            if not os.path.exists(ubulk_path): continue

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list): data = [data]

            extracted_offsets = []
            for obj in data:
                if obj.get("Type") != "Texture2D": continue
                name = obj.get("Name", "")
                if not tile_pattern.match(name): continue
                if obj.get("PixelFormat") != "PF_G16": continue
                
                mips = obj.get("Mips", [])
                if not mips: continue
                
                main_mip = mips[0]
                if main_mip.get("SizeX", 0) != 512 or main_mip.get("SizeY", 0) != 512: continue
                
                bulk_data = main_mip.get("BulkData", {})
                offset_str = bulk_data.get("OffsetInFile")
                if not offset_str: continue
                
                offset = int(offset_str, 0) if isinstance(offset_str, str) else int(offset_str)
                extracted_offsets.append(offset)
                
                if len(extracted_offsets) >= 4:
                    break

            if len(extracted_offsets) < 4:
                continue

            image_A = Image.new("I", (1024, 1024))
            
            # [핵심 수정 2] A(512x512) 타일 병합 레이아웃 스왑 완료
            # 기존: 2번째가 좌하, 3번째가 우상 -> 수정: 2번째가 우상, 3번째가 좌하
            tile_layout = [
                (0, 0),       # 첫 번째 추출 타일 -> 좌상단
                (0, 512),     # 세 번째 추출 타일 -> 좌하단 (스왑됨)
                (512, 0),     # 두 번째 추출 타일 -> 우상단 (스왑됨)
                (512, 512)    # 네 번째 추출 타일 -> 우하단
            ]

            with open(ubulk_path, "rb") as ub:
                for idx, offset in enumerate(extracted_offsets):
                    ub.seek(offset)
                    raw_bytes = ub.read(512 * 512 * 2)
                    if len(raw_bytes) < (512 * 512 * 2): continue
                    
                    tile_img = Image.frombytes("I;16", (512, 512), raw_bytes).convert("I")
                    pos_a = tile_layout[idx]
                    image_A.paste(tile_img, pos_a)

            # 디버그용 A 이미지 저장
            debug_a_name = f"A_x{x}_y{y}_sub{sub_id:02d}.png"
            image_A.convert("I;16").save(os.path.join(debug_a_dir, debug_a_name))

            pos_b = sub_layout[sub_id]
            image_B.paste(image_A, pos_b)

        # 디버그용 B 이미지 저장
        debug_b_name = f"B_x{x}_y{y}.png"
        image_B.convert("I;16").save(os.path.join(debug_b_dir, debug_b_name))

        world_pos_x = (x - min_x) * 2048
        world_pos_y = (y - min_y) * 2048
        final_world_map.paste(image_B, (world_pos_x, world_pos_y))

    # 최종 결과물 저장
    output_path = os.path.join(result_dir, "final_world_heightmap.png")
    print(f"\n[*] 좌표 배치가 완벽히 수정된 최종 마스터 맵 저장 중...")
    final_world_map.convert("I;16").save(output_path)
    print(f"[+] 성공: 월드 대형 하이트맵 생성 완료! 경로: {output_path}")

if __name__ == "__main__":
    build_world_heightmap_swapped()