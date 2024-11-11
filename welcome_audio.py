# welcome_audio.py
from gtts import gTTS
import os

def create_audio_from_text(text: str, folder_path: str, filename: str = "welcome_message.mp3"):
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, filename)
    tts = gTTS(text=text, lang='en')
    tts.save(filepath)
    print(f"Audio file saved as {filepath}")
