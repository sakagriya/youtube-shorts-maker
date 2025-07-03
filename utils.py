import os
import requests
import subprocess
import logging
from urllib.parse import urlparse

try:
    from moviepy.editor import VideoFileClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("MoviePy not available. Some video functionality may be limited.")

logger = logging.getLogger(__name__)

def download_file(url, output_path):
    """Download a file from URL to the specified path"""
    try:
        logger.info(f"Downloading file from {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"File downloaded successfully to {output_path}")
        return output_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise Exception(f"Failed to download file from {url}: {str(e)}")

def get_video_duration(video_path):
    """Get video duration using moviepy or ffprobe as fallback"""
    if MOVIEPY_AVAILABLE:
        try:
            with VideoFileClip(video_path) as clip:
                return clip.duration
        except Exception as e:
            logger.warning(f"MoviePy failed, falling back to ffprobe: {str(e)}")
    
    # Fallback to ffprobe if MoviePy is not available
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            raise Exception(f"ffprobe failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Error getting video duration: {str(e)}")
        raise Exception(f"Failed to get video duration: {str(e)}")

def apply_ducking(video_path, audio_path, output_path):
    """Apply audio ducking - lower video audio when overlay audio is playing"""
    try:
        logger.info("Applying audio ducking")
        
        # Get video duration to ensure audio doesn't exceed it
        video_duration = get_video_duration(video_path)
        
        # FFmpeg command for audio ducking
        # This reduces the original video audio volume when the overlay audio is present
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-filter_complex',
            f'[0:a]volume=0.3[lowered];[1:a]volume=1.0[overlay];[lowered][overlay]amix=inputs=2:duration=first[audio]',
            '-map', '0:v',
            '-map', '[audio]',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:v', '2M',
            '-b:a', '128k',
            '-t', str(video_duration),
            output_path
        ]
        
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Audio ducking failed: {result.stderr}")
        
        logger.info("Audio ducking completed successfully")
        
    except Exception as e:
        logger.error(f"Error applying audio ducking: {str(e)}")
        raise Exception(f"Failed to apply audio ducking: {str(e)}")

def add_watermark(video_path, output_path, username):
    """Add watermark text to video"""
    try:
        logger.info(f"Adding watermark for username: {username}")
        
        watermark_text = f"Sumber: @{username}"
        
        # FFmpeg command for adding text watermark
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', 
            f"drawtext=text='{watermark_text}':fontsize=24:fontcolor=white:x=10:y=10:box=1:boxcolor=black@0.5:boxborderw=5",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-b:v', '2M',
            output_path
        ]
        
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Watermark addition failed: {result.stderr}")
        
        logger.info("Watermark added successfully")
        
    except Exception as e:
        logger.error(f"Error adding watermark: {str(e)}")
        raise Exception(f"Failed to add watermark: {str(e)}")

def add_subtitle(video_path, output_path, subtitle_text):
    """Add subtitle text to video (centered at bottom)"""
    try:
        logger.info("Adding subtitle text")
        
        # Escape special characters in subtitle text
        escaped_text = subtitle_text.replace("'", r"\'").replace(":", r"\:")
        
        # FFmpeg command for adding subtitle text
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf',
            f"drawtext=text='{escaped_text}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=h-text_h-20:box=1:boxcolor=black@0.7:boxborderw=5",
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-b:v', '2M',
            output_path
        ]
        
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Subtitle addition failed: {result.stderr}")
        
        logger.info("Subtitle added successfully")
        
    except Exception as e:
        logger.error(f"Error adding subtitle: {str(e)}")
        raise Exception(f"Failed to add subtitle: {str(e)}")

def validate_video_file(video_path):
    """Validate that the video file is readable and has valid format"""
    try:
        if MOVIEPY_AVAILABLE:
            with VideoFileClip(video_path) as clip:
                duration = clip.duration
                if duration <= 0:
                    raise Exception("Video has no duration")
                return True
        else:
            # Use ffprobe for validation if MoviePy is not available
            duration = get_video_duration(video_path)
            if duration <= 0:
                raise Exception("Video has no duration")
            return True
    except Exception as e:
        logger.error(f"Video validation failed: {str(e)}")
        raise Exception(f"Invalid video file: {str(e)}")

def convert_video_to_shorts_format(video_path, output_path):
    """Convert video to YouTube Shorts format (9:16 aspect ratio, max 60 seconds)"""
    try:
        logger.info("Converting video to YouTube Shorts format")
        
        # FFmpeg command to convert to vertical format suitable for Shorts
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:v', '2M',
            '-b:a', '128k',
            '-t', '60',  # Limit to 60 seconds for Shorts
            output_path
        ]
        
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise Exception(f"Video format conversion failed: {result.stderr}")
        
        logger.info("Video converted to Shorts format successfully")
        
    except Exception as e:
        logger.error(f"Error converting video format: {str(e)}")
        raise Exception(f"Failed to convert video format: {str(e)}")
