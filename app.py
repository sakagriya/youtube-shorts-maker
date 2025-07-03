import os
import logging
import tempfile
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from utils import download_file, apply_ducking, add_watermark, add_subtitle
from youtube_uploader import upload_video_to_youtube

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'aac', 'm4a'}

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_video_from_request(request):
    """Save video from various input sources to /tmp/input_video.mp4"""
    video_path = '/tmp/input_video.mp4'
    
    # Check for raw binary data (Content-Type: video/mp4)
    if request.content_type and request.content_type.startswith('video/'):
        logger.info("Processing raw video binary data")
        with open(video_path, 'wb') as f:
            f.write(request.get_data())
        return video_path
    
    # Check for video_url in form data or JSON
    data = request.get_json() if request.is_json else request.form
    
    if 'video_url' in data:
        logger.info(f"Downloading video from URL: {data['video_url']}")
        download_file(data['video_url'], video_path)
        return video_path
    
    # Check for video_file upload
    if 'video_file' in request.files:
        file = request.files['video_file']
        if file and file.filename and allowed_file(file.filename, ALLOWED_VIDEO_EXTENSIONS):
            logger.info(f"Saving uploaded video file: {file.filename}")
            file.save(video_path)
            return video_path
    
    raise ValueError("No valid video input provided")

def save_audio_from_request(request):
    """Save audio from various input sources to /tmp/input_audio.mp3"""
    audio_path = '/tmp/input_audio.mp3'
    
    # Check for raw binary data (Content-Type: audio/mpeg)
    if request.content_type and request.content_type.startswith('audio/'):
        logger.info("Processing raw audio binary data")
        with open(audio_path, 'wb') as f:
            f.write(request.get_data())
        return audio_path
    
    # Check for audio_url in form data or JSON
    data = request.get_json() if request.is_json else request.form
    
    if 'audio_url' in data:
        logger.info(f"Downloading audio from URL: {data['audio_url']}")
        download_file(data['audio_url'], audio_path)
        return audio_path
    
    # Check for audio_file upload
    if 'audio_file' in request.files:
        file = request.files['audio_file']
        if file and file.filename and allowed_file(file.filename, ALLOWED_AUDIO_EXTENSIONS):
            logger.info(f"Saving uploaded audio file: {file.filename}")
            file.save(audio_path)
            return audio_path
    
    return None  # Audio is optional

@app.route('/run', methods=['POST'])
def process_youtube_short():
    try:
        logger.info("Starting YouTube Shorts processing")
        
        # Get form data or JSON data
        data = request.get_json() if request.is_json else request.form
        
        # Extract metadata
        username = data.get('username', '')
        subtitle_text = data.get('subtitle_text', '')
        title = data.get('title', 'YouTube Short')
        description = data.get('description', '')
        tags = data.get('tags', '')
        
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        logger.info(f"Processing with username: {username}, title: {title}")
        
        # Step 1: Save video from input source
        try:
            video_path = save_video_from_request(request)
            logger.info(f"Video saved to: {video_path}")
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        
        # Step 2: Save audio from input source (optional)
        audio_path = save_audio_from_request(request)
        if audio_path:
            logger.info(f"Audio saved to: {audio_path}")
        
        # Step 3: Apply audio ducking if audio is provided
        if audio_path:
            logger.info("Applying audio ducking")
            ducked_video_path = '/tmp/ducked_video.mp4'
            apply_ducking(video_path, audio_path, ducked_video_path)
            video_path = ducked_video_path
        
        # Step 4: Add watermark
        if username:
            logger.info(f"Adding watermark for user: {username}")
            watermark_video_path = '/tmp/watermark_video.mp4'
            add_watermark(video_path, watermark_video_path, username)
            video_path = watermark_video_path
        
        # Step 5: Add subtitle
        if subtitle_text:
            logger.info("Adding subtitles")
            subtitle_video_path = '/tmp/subtitle_video.mp4'
            add_subtitle(video_path, subtitle_video_path, subtitle_text)
            video_path = subtitle_video_path
        
        # Step 6: Save final output
        final_output_path = '/tmp/final_output.mp4'
        os.rename(video_path, final_output_path)
        logger.info(f"Final video saved to: {final_output_path}")
        
        # Step 7: Upload to YouTube
        logger.info("Uploading to YouTube")
        video_id = upload_video_to_youtube(
            video_path=final_output_path,
            title=title,
            description=description,
            tags=tags
        )
        
        # Clean up temporary files
        cleanup_files = [
            '/tmp/input_video.mp4',
            '/tmp/input_audio.mp3',
            '/tmp/ducked_video.mp4',
            '/tmp/watermark_video.mp4',
            '/tmp/subtitle_video.mp4',
            final_output_path
        ]
        
        for file_path in cleanup_files:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up: {file_path}")
        
        return jsonify({
            'success': True,
            'message': 'YouTube Short processed and uploaded successfully',
            'video_id': video_id,
            'video_url': f'https://www.youtube.com/watch?v={video_id}'
        })
        
    except Exception as e:
        logger.error(f"Error processing YouTube Short: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'message': 'YouTube Shorts API is running'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'Available endpoints: POST /run, GET /health'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
