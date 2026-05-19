def convert_16bit_to_photoshop_hex(value):
    """
    16비트 정수(0~65535)를 포토샵용 6자리 Hex(#FFFFFF)로 변환하거나,
    6자리 Hex를 16비트 순수 정수로 변환합니다.
    """
    # 1. 입력값이 문자열(Hex)인 경우 -> 16비트 정수로 복원
    if isinstance(value, str):
        clean_hex = value.replace('0x', '').replace('#', '').strip()
        
        if len(clean_hex) != 6:
            raise ValueError(f"포토샵 포맷은 반드시 6자리 헥사코드여야 합니다 (예: A5A5A5): {value}")
            
        # R, G, B 중 하나의 채널 값(0~255)만 추출 (그레이스케일이므로 동일함)
        r_8bit = int(clean_hex[:2], 16)
        
        # 8비트(0~255) 값을 16비트(0~65535) 비율로 정확히 복원
        # (255일 때 정확히 65535가 나오도록 257을 곱해줍니다)
        return int(r_8bit * 257)
            
    # 2. 입력값이 정수(int)인 경우 -> 포토샵용 6자리 Hex 문자열로 변환
    elif isinstance(value, (int, float)):
        int_val = int(value)
        if not (0 <= int_val <= 65535):
            raise ValueError(f"16비트 범위를 벗어났습니다 (0~65535): {int_val}")
            
        # 16비트 값을 8비트(0~255) 스케일로 압축
        val_8bit = int(round(int_val / 257.0))
        
        # 8비트 값을 2자리 Hex로 바꾼 뒤, R/G/B에 똑같이 복사해서 6자리로 포맷팅
        hex_2digit = f"{val_8bit:02X}"
        return f"#{hex_2digit}{hex_2digit}{hex_2digit}"
        
    else:
        raise TypeError("int 또는 str 타입만 입력 가능합니다.")

def get_absolute_height(raw_pixel):
    from config import Z_SCALE, Z_REFERENCE_PIXEL
    actual_height = ((float(raw_pixel) - Z_REFERENCE_PIXEL) / 65535.0) * 512.0 * Z_SCALE
    return actual_height
    
if __name__ == "__main__":
  """
  65535 Stalber 꼭대기
  42320 돌산
  35136 400m 사격장
  32639 해수면

  예시: ffffff 246,949494 41,8e8e8e 30,8d8d8d 27,28,868686 14,828282 5,808080 1,7f7f7f 0,7e7e7e -1<br><br>
  """
  # pixel_list = [65535, 42320, 35136, 32639]
  # for p in pixel_list:
  #   height = get_absolute_height(p)
  #   print(round(height))
  
  # hex_list = ["ffffff", "949494", "8e8e8e", "8d8d8d", "868686", "828282", "808080", "7f7f7f", "7e7e7e"]
  a = ["a4a4a4"]
  for h in a:
    pixcel_data = convert_16bit_to_photoshop_hex(h)
    height = get_absolute_height(pixcel_data)
    print(round(height))

  # print('data = [')
  # for i in hex_list:
  #     print('    {')
  #     print(f'        "hex": "{i}",')
  #     pix = convert_16bit_to_photoshop_hex(i)
  #     print(f'        "bit": {pix},')
  #     print(f'        "height": {get_absolute_height(pix)}')
  #     print('    },')
  # print(']')