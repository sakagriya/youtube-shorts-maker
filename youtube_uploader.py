import os
import logging
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from config import (
    YOUTUBE_CLIENT_ID, 
    YOUTUBE_CLIENT_SECRET, 
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_UPLOAD_SCOPE,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION
)

logger = logging.getLogger(__name__)

def get_youtube_service():
    """Get authenticated YouTube service"""
    try:
        # Create credentials from refresh token
        credentials = Credentials(
            token=None,
            refresh_token=YOUTUBE_REFRESH_TOKEN,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=YOUTUBE_CLIENT_ID,
            client_secret=YOUTUBE_CLIENT_SECRET,
            scopes=YOUTUBE_UPLOAD_SCOPE
        )
        
        # Refresh the token if needed
        if credentials.expired:
            credentials.refresh(Request())
        
        # Build the service
        service = build(
            YOUTUBE_API_SERVICE_NAME,
            YOUTUBE_API_VERSION,
            credentials=credentials
        )
        
        logger.info("YouTube service authenticated successfully")
        return service
        
    except Exception as e:
        logger.error(f"Error authenticating YouTube service: {str(e)}")
        raise Exception(f"Failed to authenticate with YouTube API: {str(e)}")

def upload_video_to_youtube(video_path, title, description="", tags=None, privacy_status="public"):
    """Upload video to YouTube"""
    try:
        logger.info(f"Starting YouTube upload for video: {title}")
        
        if not os.path.exists(video_path):
            raise Exception(f"Video file not found: {video_path}")
        
        # Get YouTube service
        youtube = get_youtube_service()
        
        # Prepare video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags if tags else [],
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Create media upload object
        media = MediaFileUpload(
            video_path,
            chunksize=-1,
            resumable=True,
            mimetype='video/mp4'
        )
        
        # Execute the upload
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        logger.info("Uploading video to YouTube...")
        
        # Execute the request and handle resumable upload
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    logger.info(f"Upload progress: {int(status.progress() * 100)}%")
            except Exception as e:
                error = e
                retry += 1
                if retry > 3:
                    raise Exception(f"Upload failed after 3 retries: {str(error)}")
                logger.warning(f"Upload error (retry {retry}): {str(e)}")
        
        if response is not None:
            if 'id' in response:
                video_id = response['id']
                logger.info(f"Video uploaded successfully. Video ID: {video_id}")
                return video_id
            else:
                raise Exception("Upload completed but no video ID returned")
        
    except Exception as e:
        logger.error(f"Error uploading video to YouTube: {str(e)}")
        raise Exception(f"Failed to upload video to YouTube: {str(e)}")

def create_youtube_playlist(title, description="", privacy_status="public"):
    """Create a YouTube playlist"""
    try:
        logger.info(f"Creating YouTube playlist: {title}")
        
        youtube = get_youtube_service()
        
        body = {
            'snippet': {
                'title': title,
                'description': description
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }
        
        request = youtube.playlists().insert(
            part='snippet,status',
            body=body
        )
        
        response = request.execute()
        
        if 'id' in response:
            playlist_id = response['id']
            logger.info(f"Playlist created successfully. Playlist ID: {playlist_id}")
            return playlist_id
        else:
            raise Exception("Playlist creation failed")
            
    except Exception as e:
        logger.error(f"Error creating YouTube playlist: {str(e)}")
        raise Exception(f"Failed to create YouTube playlist: {str(e)}")

def add_video_to_playlist(playlist_id, video_id):
    """Add a video to a YouTube playlist"""
    try:
        logger.info(f"Adding video {video_id} to playlist {playlist_id}")
        
        youtube = get_youtube_service()
        
        body = {
            'snippet': {
                'playlistId': playlist_id,
                'resourceId': {
                    'kind': 'youtube#video',
                    'videoId': video_id
                }
            }
        }
        
        request = youtube.playlistItems().insert(
            part='snippet',
            body=body
        )
        
        response = request.execute()
        
        if 'id' in response:
            logger.info("Video added to playlist successfully")
            return response['id']
        else:
            raise Exception("Failed to add video to playlist")
            
    except Exception as e:
        logger.error(f"Error adding video to playlist: {str(e)}")
        raise Exception(f"Failed to add video to playlist: {str(e)}")

def get_video_info(video_id):
    """Get information about a YouTube video"""
    try:
        logger.info(f"Getting info for video: {video_id}")
        
        youtube = get_youtube_service()
        
        request = youtube.videos().list(
            part='snippet,status,statistics',
            id=video_id
        )
        
        response = request.execute()
        
        if response['items']:
            video_info = response['items'][0]
            logger.info("Video info retrieved successfully")
            return video_info
        else:
            raise Exception("Video not found")
            
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}")
        raise Exception(f"Failed to get video info: {str(e)}")
