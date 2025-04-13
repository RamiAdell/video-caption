import os
import logging
import numpy as np
from moviepy.editor import VideoFileClip
from PIL import Image, ImageDraw, ImageFont
from pysrt import SubRipFile
import whisper
from deep_translator import GoogleTranslator
from pydub.utils import mediainfo
from config import Config

def extract_audio_from_video(video_path, audio_path):
    video = VideoFileClip(video_path)
    video.audio.write_audiofile(audio_path)

def audio2text(wav_file_path, output_srt):
    model = whisper.load_model("small")
    result = model.transcribe(wav_file_path)
    write_srt_whisper(output_srt, result["segments"])

def write_srt_whisper(output_file, segments):
    with open(output_file, 'w') as f:
        for index, segment in enumerate(segments):
            start_time = segment['start']
            end_time = segment['end']
            text = segment['text']
            f.write(f"{index + 1}\n")
            f.write(f"{format_timestamp(start_time)} --> {format_timestamp(end_time)}\n")
            f.write(f"{text}\n\n")

def format_timestamp(seconds):
    ms = int((seconds - int(seconds)) * 1000)
    return f"{int(seconds//3600):02}:{int((seconds%3600)//60):02}:{int(seconds%60):02},{ms:03}"

def add_captions_to_video(video_path, srt_path, output_path, font_name, font_size, font_color):
    video = VideoFileClip(video_path)
    subs = SubRipFile.open(srt_path)

    font_path = os.path.join(Config.FONTS_FOLDER, font_name)
    if not os.path.isfile(font_path):
        raise FileNotFoundError(f"Font file '{font_path}' not found.")
    font = ImageFont.truetype(font_path, font_size)

    def add_text_overlay(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        draw = ImageDraw.Draw(img)

        for sub in subs:
            start = sub.start.ordinal / 1000
            end = sub.end.ordinal / 1000
            if start <= t <= end:
                text = sub.text
                max_width = int(img.size[0] * 0.9)
                lines = []
                current_line = ""
                for word in text.split():
                    test_line = f"{current_line} {word}".strip()
                    test_width = draw.textlength(test_line, font=font)
                    if test_width <= max_width:
                        current_line = test_line
                    else:
                        lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)

                line_height = font_size + 5
                total_height = len(lines) * line_height
                text_y = img.size[1] - total_height - 50

                for i, line in enumerate(lines):
                    line_width = draw.textlength(line, font=font)
                    text_x = (img.size[0] - line_width) // 2
                    draw.text((text_x, text_y + i * line_height), line, font=font, fill=font_color)

                break

        return np.array(img)

    captioned_video = video.fl(add_text_overlay)
    captioned_video.write_videofile(output_path, codec='libx264', fps=video.fps)

    video.close()
    captioned_video.close()

def translate_srt(srt_file_path, target_language, output_path):
    subs = SubRipFile.open(srt_file_path)
    translator = GoogleTranslator(source='auto', target=target_language)

    for sub in subs:
        original_text = sub.text
        try:
            translated_text = translator.translate(original_text)
            logging.debug(f"Original: {original_text} | Translated: {translated_text}")
            sub.text = translated_text
        except Exception as e:
            logging.error(f"Translation failed for '{original_text}' with error: {str(e)}")
            sub.text = original_text

    subs.save(output_path, encoding='utf-8')

