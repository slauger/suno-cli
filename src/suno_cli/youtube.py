"""
YouTube upload functionality for suno-cli
"""

import os
import sys
import pickle
from pathlib import Path
from typing import Optional, Dict, Any

# YouTube API imports (optional dependency)
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    YOUTUBE_AVAILABLE = True
except ImportError:
    YOUTUBE_AVAILABLE = False


class YouTubeError(Exception):
    """Base exception for YouTube upload errors"""
    pass


# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Default credentials path
DEFAULT_CREDENTIALS_DIR = Path.home() / '.suno-cli' / 'youtube'
DEFAULT_TOKEN_FILE = DEFAULT_CREDENTIALS_DIR / 'token.pickle'
DEFAULT_CLIENT_SECRETS_FILE = DEFAULT_CREDENTIALS_DIR / 'client_secrets.json'


def check_youtube_available() -> bool:
    """
    Check if YouTube API dependencies are installed

    Returns:
        True if available, False otherwise
    """
    return YOUTUBE_AVAILABLE


def ensure_youtube_available():
    """
    Ensure YouTube API dependencies are installed

    Raises:
        YouTubeError: If dependencies are not installed
    """
    if not YOUTUBE_AVAILABLE:
        raise YouTubeError(
            "YouTube API dependencies not installed.\n"
            "Install with: pip install 'suno-cli[youtube]'\n"
            "Or manually: pip install google-auth-oauthlib google-api-python-client"
        )


def get_authenticated_service(
    client_secrets_file: Optional[str] = None,
    token_file: Optional[str] = None
) -> Any:
    """
    Authenticate with YouTube API and return service object

    Args:
        client_secrets_file: Path to OAuth2 client secrets JSON file
        token_file: Path to stored token pickle file

    Returns:
        YouTube API service object

    Raises:
        YouTubeError: If authentication fails
    """
    ensure_youtube_available()

    # Use defaults if not provided
    if not client_secrets_file:
        client_secrets_file = str(DEFAULT_CLIENT_SECRETS_FILE)
    if not token_file:
        token_file = str(DEFAULT_TOKEN_FILE)

    # Check if client secrets exist
    if not Path(client_secrets_file).exists():
        raise YouTubeError(
            f"OAuth2 client secrets file not found: {client_secrets_file}\n\n"
            "To set up YouTube uploads:\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Create a new project (or select existing)\n"
            "3. Enable YouTube Data API v3\n"
            "4. Create OAuth 2.0 credentials (Desktop app)\n"
            "5. Download client secrets JSON\n"
            f"6. Save it as: {DEFAULT_CLIENT_SECRETS_FILE}\n"
            "   Or use --client-secrets option to specify path\n\n"
            "See: https://developers.google.com/youtube/v3/getting-started"
        )

    credentials = None

    # Load saved token if exists
    token_path = Path(token_file)
    if token_path.exists():
        with open(token_path, 'rb') as f:
            credentials = pickle.load(f)

    # If no valid credentials, authenticate
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # Refresh expired token
            credentials.refresh(Request())
        else:
            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        # Save token for future use
        token_path.parent.mkdir(parents=True, exist_ok=True)
        with open(token_path, 'wb') as f:
            pickle.dump(credentials, f)

    # Build YouTube service
    return build('youtube', 'v3', credentials=credentials)


def upload_video(
    video_file: str,
    title: str,
    description: Optional[str] = None,
    tags: Optional[list[str]] = None,
    category: str = "10",  # Music category
    privacy: str = "private",
    client_secrets_file: Optional[str] = None,
    token_file: Optional[str] = None,
    notify_subscribers: bool = False
) -> Dict[str, Any]:
    """
    Upload video to YouTube

    Args:
        video_file: Path to video file (MP4)
        title: Video title (max 100 chars)
        description: Video description (optional, max 5000 chars)
        tags: List of tags (optional, max 500 chars total)
        category: YouTube category ID (default: "10" = Music)
        privacy: Privacy status: "public", "private", or "unlisted" (default: "private")
        client_secrets_file: Path to OAuth2 client secrets
        token_file: Path to stored token
        notify_subscribers: Whether to notify subscribers (only for public videos)

    Returns:
        Dict with video information (id, url, etc.)

    Raises:
        YouTubeError: If upload fails

    YouTube Categories:
        1=Film & Animation, 2=Autos & Vehicles, 10=Music, 15=Pets & Animals,
        17=Sports, 19=Travel & Events, 20=Gaming, 22=People & Blogs,
        23=Comedy, 24=Entertainment, 25=News & Politics, 26=Howto & Style,
        27=Education, 28=Science & Technology, 29=Nonprofits & Activism
    """
    ensure_youtube_available()

    # Validate input
    video_path = Path(video_file)
    if not video_path.exists():
        raise YouTubeError(f"Video file not found: {video_file}")

    if not video_path.suffix.lower() in ['.mp4', '.mov', '.avi', '.flv', '.wmv']:
        raise YouTubeError(f"Unsupported video format: {video_path.suffix}")

    if len(title) > 100:
        raise YouTubeError(f"Title too long (max 100 chars): {len(title)} chars")

    if description and len(description) > 5000:
        raise YouTubeError(f"Description too long (max 5000 chars): {len(description)} chars")

    if privacy not in ['public', 'private', 'unlisted']:
        raise YouTubeError(f"Invalid privacy setting: {privacy}")

    # Get authenticated service
    youtube = get_authenticated_service(client_secrets_file, token_file)

    # Prepare video metadata
    body = {
        'snippet': {
            'title': title,
            'description': description or '',
            'tags': tags or [],
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False,
        }
    }

    # Add notify subscribers flag only if public
    if privacy == 'public':
        body['status']['publishAt'] = None  # Publish immediately
        if not notify_subscribers:
            # Suppress notifications
            body['status']['publishAt'] = None

    # Create media upload
    media = MediaFileUpload(
        str(video_path),
        chunksize=1024*1024,  # 1MB chunks
        resumable=True
    )

    # Execute upload
    try:
        request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media,
            notifySubscribers=notify_subscribers if privacy == 'public' else False
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                # Progress update (percentage uploaded)
                progress = int(status.progress() * 100)
                # This will be captured by caller for display
                print(f"Upload progress: {progress}%", file=sys.stderr)

        video_id = response['id']
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        return {
            'id': video_id,
            'url': video_url,
            'title': response['snippet']['title'],
            'privacy': response['status']['privacyStatus']
        }

    except Exception as e:
        raise YouTubeError(f"Upload failed: {e}")


def init_youtube_auth(client_secrets_file: Optional[str] = None):
    """
    Initialize YouTube authentication (setup wizard)

    Args:
        client_secrets_file: Path to OAuth2 client secrets file

    Raises:
        YouTubeError: If initialization fails
    """
    ensure_youtube_available()

    # Create directory
    DEFAULT_CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if client secrets provided
    if client_secrets_file:
        src = Path(client_secrets_file)
        if not src.exists():
            raise YouTubeError(f"Client secrets file not found: {client_secrets_file}")

        # Copy to default location
        import shutil
        shutil.copy(src, DEFAULT_CLIENT_SECRETS_FILE)
        print(f"Copied client secrets to: {DEFAULT_CLIENT_SECRETS_FILE}")

    # Try to authenticate (will trigger OAuth flow)
    try:
        youtube = get_authenticated_service()
        # Test API access
        request = youtube.channels().list(part='snippet', mine=True)
        response = request.execute()

        if 'items' in response and len(response['items']) > 0:
            channel_title = response['items'][0]['snippet']['title']
            return {
                'success': True,
                'channel': channel_title,
                'token_file': str(DEFAULT_TOKEN_FILE)
            }
        else:
            raise YouTubeError("No YouTube channel found for this account")

    except Exception as e:
        raise YouTubeError(f"Authentication failed: {e}")
