# ballistics.py
import math
from config import SCALE_Z

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
    # 💡 하드코딩된 변수 대신 매개변수로 받은 scale_xy 사용
    dx_pixels = (m_hx - p_hx) * scale_xy
    dy_pixels = (m_hy - p_hy) * scale_xy
    return math.sqrt(dx_pixels**2 + dy_pixels**2)

def get_absolute_height(heightmap, hx, hy):
    """하이트맵 이미지에서 특정 좌표의 SCALE_Z가 반영된 절대 고도를 반환합니다."""
    return (heightmap[hy, hx] / 65535.0) * 512.0 * SCALE_Z