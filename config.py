import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# YouTube API Configuration
YOUTUBE_CLIENT_ID = os.getenv('YOUTUBE_CLIENT_ID', '')
YOUTUBE_CLIENT_SECRET = os.getenv('YOUTUBE_CLIENT_SECRET', '')
YOUTUBE_REFRESH_TOKEN = os.getenv('YOUTUBE_REFRESH_TOKEN', '')

# YouTube API Scopes
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# File paths
TEMP_DIR = '/tmp'

# Video processing settings
DEFAULT_VIDEO_CODEC = 'libx264'
DEFAULT_AUDIO_CODEC = 'aac'
DEFAULT_VIDEO_BITRATE = '2M'
DEFAULT_AUDIO_BITRATE = '128k'

# Watermark settings
WATERMARK_FONT_SIZE = 24
WATERMARK_FONT_COLOR = 'white'
WATERMARK_POSITION = '10:10'  # x:y position from top-left

# Subtitle settings
SUBTITLE_FONT_SIZE = 32
SUBTITLE_FONT_COLOR = 'white'
SUBTITLE_OUTLINE_COLOR = 'black'
SUBTITLE_OUTLINE_WIDTH = 2
