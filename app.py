from flask import Flask, request, jsonify, send_from_directory
import os
import logging
import secrets
from datetime import datetime, timedelta
from pydub.utils import mediainfo
from utils.video_utils import extract_audio_from_video, audio2text, translate_srt, add_captions_to_video
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB limit
app.config['SIGNED_URL_EXPIRY'] = 3600  # 1 hour expiry for signed URLs
app.secret_key = secrets.token_hex(16)  # Secret key for signing URLs

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def generate_signed_url(filename, expiry=None):
    """
    Generate a signed URL for a file.
    """
    if expiry is None:
        expiry = app.config['SIGNED_URL_EXPIRY']
    expiration_time = datetime.utcnow() + timedelta(seconds=expiry)
    token = secrets.token_urlsafe(32)  # Generate a secure token
    signed_url = f"/download_video?filename={filename}&token={token}&expires={expiration_time.timestamp()}"
    return signed_url

 


@app.route('/process', methods=['POST'])
def process():
    try:
        # Get the user ID and video file from the request
        user_id = request.form.get('user_id')
        video_file = request.files['video']
        chosen_language = request.form.get('language', 'en')
        font_name = request.form.get('fontFamily', 'Poppins-Bold.ttf')
        font_size = int(request.form.get('fontSize', 36))
        font_color = request.form.get('fontColor', 'black')

        # Save the video file
        video_filename = f"{user_id}-{secure_filename(video_file.filename)}"
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
        video_file.save(video_path)

        # Extract audio from the video
        audio_path = os.path.join(
            app.config['UPLOAD_FOLDER'], f"{user_id}-audio.wav")
        extract_audio_from_video(video_path, audio_path)

        # Convert audio to text and generate subtitles
        srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}-subtitles.srt")
        audio2text(audio_path, srt_path)

        # Translate subtitles to the chosen language
        translated_srt_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{user_id}-Translated_subtitles.srt")
        translate_srt(srt_path, chosen_language, translated_srt_path)

        # Add captions to the video
        output_video_filename = f"{user_id}-output_video.mp4"
        output_video_path = os.path.join(
            app.config['UPLOAD_FOLDER'], output_video_filename)
        add_captions_to_video(video_path, translated_srt_path,
                              output_video_path, font_name, font_size, font_color)

        # Generate a signed URL for the processed video
        signed_url = generate_signed_url(output_video_filename)

        # Clean up temporary files
   

        # Return the signed URL
        return jsonify({'video_url': "https://www.nexmediaai.com/video-processing"+signed_url,
                        "video_path": video_path,
                        "translated_srt_path": translated_srt_path, 
                        "output_video_path": output_video_path, 
                        "font_name": font_name, 
                        "font_size": font_size, 
                        "font_color": font_color})

    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/download_video', methods=['GET'])
def download_video():
    try:
        filename = request.args.get('filename')
        token = request.args.get('token')
        expires = request.args.get('expires')

        if not filename or not token or not expires:
            return jsonify({'error': 'Invalid URL'}), 400

        # Check if the URL has expired
        expiration_time = datetime.fromtimestamp(float(expires))
        if datetime.utcnow() > expiration_time:
            return jsonify({'error': 'URL has expired'}), 403

        # Construct the path to the processed video
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Check if the video exists
        if not os.path.exists(video_path):
            return jsonify({'error': 'Video not found'}), 404

        # Send the video file as an attachment
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

    except Exception as e:
        logging.error(f"Error downloading video: {str(e)}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run()
