import threading
import os
from gtts import gTTS
import pygame
from pydub import AudioSegment
from config import TTS_SPEED_FACTOR

# 오디오 파일 임시 폴더 생성
if not os.path.exists("tmp_audio"):
    os.makedirs("tmp_audio")

# pygame 오디오 믹서 초기화 (표준 주파수로 안정적으로 세팅)
pygame.mixer.init()

def _speak_google(text):
    try:
        # 파일명 정의 (원본 파일과 배속 처리된 파일 구분)
        safe_filename = "".join([c for c in text if c.isalnum()]).rstrip()
        orig_path = f"tmp_audio/{safe_filename}_orig.mp3"
        speed_path = f"tmp_audio/{safe_filename}_speed.mp3"
        
        # 1. 원본 파일이 없다면 구글에서 먼저 다운로드
        if not os.path.exists(orig_path):
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(orig_path)
            
            # 2. 다운로드 직후 pydub을 이용해 속도를 물리적으로 변환 후 저장 (최초 1회만 연산)
            sound = AudioSegment.from_file(orig_path, format="mp3")
            
            # pydub의 speedup 기능을 이용해 음의 왜곡 없이 템포만 조절
            fast_sound = sound.speedup(playback_speed=TTS_SPEED_FACTOR)
            fast_sound.export(speed_path, format="mp3")
        
        # 💡 연타 대응: 현재 채널 0번에서 소리가 나고 있다면 즉시 강제 정지!
        channel = pygame.mixer.Channel(0)
        if channel.get_busy():
            channel.stop()
        
        # 3. 배속 처리가 완료된 고유 파일을 불러와 재생
        sound_to_play = pygame.mixer.Sound(speed_path)
        channel.play(sound_to_play)
            
    except Exception as e:
        print(f"[TTS 내부 재생 에러] {e}")

def speak(text):
    """메인 스레드 대기 없는 쾌속 비동기 래퍼"""
    t = threading.Thread(target=_speak_google, args=(text,), daemon=True)
    t.start()