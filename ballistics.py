# ballistics.py
import math
from config import Z_SCALE, Z_REFERENCE_PIXEL

def get_mortar_in_game_distance(x, H, mortar_steps):
    """탄도학 공식을 기반으로 인게임 박격포 사거리 배정 값을 계산합니다."""
    inside_sqrt = 1 - (H / 350) - (pow(x, 2) / pow(700, 2))
    if inside_sqrt < 0:
        return None

    tan_theta = (700 / x) * (1 + math.sqrt(inside_sqrt))
    theta_deg = (math.atan(tan_theta) * 180) / math.pi
    
    exact_distance = 700 * math.sin(2 * ((90 - theta_deg) * math.pi / 180))
    closest_in_game_distance = min(mortar_steps, key=lambda curr: abs(curr - exact_distance))
    return closest_in_game_distance

def calculate_physical_distance(p_hx, p_hy, m_hx, m_hy, scale_xy):
    """두 좌표 간의 지정된 scale_xy가 적용된 물리적 수평 거리를 계산합니다."""
    dx_pixels = (m_hx - p_hx) * scale_xy
    dy_pixels = (m_hy - p_hy) * scale_xy
    return math.sqrt(dx_pixels**2 + dy_pixels**2)

def get_absolute_height(heightmap, hx, hy):
    """
    16비트 하이트맵 픽셀 값에서 에란겔 표준 기준점(32639)을 차감하여
    모든 맵에 공유되는 실제 인게임 미터(m) 단위 고도를 반환합니다.
    """
    raw_pixel = heightmap[hy, hx]
    # 3채널(BGR)로 읽혔을 경우를 대비한 안전장치
    if hasattr(raw_pixel, '__len__'):
        raw_pixel = raw_pixel[0]
    # 💡 과거 검증하신 정밀 공식을 16비트 스케일에 완벽 매핑
    actual_height = ((float(raw_pixel) - Z_REFERENCE_PIXEL) / 65535.0) * 512.0 * Z_SCALE
    print(raw_pixel, actual_height)
    return actual_height