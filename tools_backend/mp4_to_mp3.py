# tools_backend/mp4_to_mp3.py
import os
import uuid
from moviepy import VideoFileClip

def convert_mp4_to_mp3(upload_folder, file_storage):
    try:
        # Save uploaded MP4
        filename = f"{uuid.uuid4()}.mp4"
        file_path = os.path.join(upload_folder, filename)
        file_storage.save(file_path)

        # Convert to MP3
        mp3_filename = filename.replace(".mp4", ".mp3")
        mp3_path = os.path.join(upload_folder, mp3_filename)

        video = VideoFileClip(file_path)
        video.audio.write_audiofile(mp3_path)
        video.close()

        return mp3_filename, None
    except Exception as e:
        return None, str(e)
