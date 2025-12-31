"""
Suno API Client for sunoapi.org
"""

import time
from typing import Dict, List, Optional, Tuple
import requests


class SunoAPIError(Exception):
    """Base exception for Suno API errors"""
    pass


class SunoClient:
    """Client for interacting with Suno AI via sunoapi.org"""

    BASE_URL = "https://api.sunoapi.org/api/v1"
    COVER_ENDPOINT = "https://api.sunoapi.org/api/v1/generate/cover"

    def __init__(self, api_key: str, callback_url: Optional[str] = None):
        """
        Initialize Suno API client

        Args:
            api_key: Your sunoapi.org API key
            callback_url: Optional callback URL for async notifications
        """
        self.api_key = api_key
        self.callback_url = callback_url or "https://example.com/callback"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })

    def generate_song(
        self,
        lyrics: str,
        title: Optional[str] = None,
        style: Optional[str] = None,
        model: str = "V4_5ALL",
        vocal_gender: str = "male",
        instrumental: bool = False,
        duration: Optional[int] = None,
        custom_mode: bool = True,
    ) -> str:
        """
        Generate a song with Suno AI

        Args:
            lyrics: Song lyrics/prompt content
            title: Song title (max 80 chars) - required if custom_mode=True
            style: Style/genre description - required if custom_mode=True
            model: AI model (V5, V4_5PLUS, V4_5ALL, V4_5, V4)
            vocal_gender: Vocal gender (male/female)
            instrumental: Generate instrumental only (no vocals)
            duration: Desired song length in seconds (experimental, optional)
            custom_mode: Use custom mode (True) or simple mode (False)

        Returns:
            Task ID for tracking the generation

        Raises:
            SunoAPIError: If generation request fails
        """
        # Build base payload
        payload = {
            "customMode": custom_mode,
            "instrumental": instrumental,
            "prompt": lyrics,
            "model": model,
            "callBackUrl": self.callback_url,
            "vocalGender": vocal_gender
        }

        # Custom mode requires title and style
        if custom_mode:
            if not title or not style:
                raise SunoAPIError("Custom mode requires both title and style")
            payload["title"] = title
            payload["style"] = style
        else:
            # Simple mode - title and style should be empty
            payload["title"] = ""
            payload["style"] = ""

        # Add experimental parameters if provided
        if duration is not None:
            payload["duration"] = duration

        try:
            response = self.session.post(
                f"{self.BASE_URL}/generate",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Handle nested response structure
            task_id = result.get('taskId') or result.get('data', {}).get('taskId')

            if not task_id:
                raise SunoAPIError(f"No taskId in response: {result}")

            return task_id

        except requests.exceptions.RequestException as e:
            raise SunoAPIError(f"Failed to generate song: {e}")

    def get_status(self, task_id: str) -> Dict:
        """
        Get generation status for a task

        Args:
            task_id: Task ID from generate_song()

        Returns:
            Status dictionary with state and data

        Raises:
            SunoAPIError: If status check fails
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/generate/record-info",
                params={"taskId": task_id},
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise SunoAPIError(f"Failed to get status: {e}")

    def wait_for_completion(
        self,
        task_id: str,
        poll_interval: int = 10,
        max_wait: int = 600
    ) -> Tuple[List[str], Dict]:
        """
        Wait for song generation to complete

        Args:
            task_id: Task ID to monitor
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait

        Returns:
            Tuple of (audio_urls, metadata)

        Raises:
            SunoAPIError: If generation fails or times out
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait:
                raise SunoAPIError(f"Timeout after {max_wait}s waiting for task {task_id}")

            status = self.get_status(task_id)
            data = status.get('data', {})
            state = data.get('status', 'PENDING')

            if state == 'SUCCESS':
                # Extract audio URLs from nested structure
                response_data = data.get('response', {})
                suno_data = response_data.get('sunoData', [])

                if not suno_data:
                    raise SunoAPIError(f"No sunoData in successful response: {status}")

                # Extract URLs from all generated variants
                audio_urls = []
                for item in suno_data:
                    if 'audioUrl' in item:
                        audio_urls.append(item['audioUrl'])

                return audio_urls, data

            elif state == 'FAILED':
                error_msg = data.get('error', 'Unknown error')
                raise SunoAPIError(f"Generation failed: {error_msg}")

            # Still pending, wait and retry
            time.sleep(poll_interval)

    def download_audio(self, url: str, output_path: str) -> None:
        """
        Download audio file from URL

        Args:
            url: Audio file URL
            output_path: Local path to save file

        Raises:
            SunoAPIError: If download fails
        """
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

        except requests.exceptions.RequestException as e:
            raise SunoAPIError(f"Failed to download audio: {e}")

    def generate_cover(self, music_task_id: str) -> str:
        """
        Generate cover art for a music task

        Note: This costs additional API credits and can only be called once per music task.

        Args:
            music_task_id: The task ID from generate_song()

        Returns:
            Cover task ID for tracking the generation

        Raises:
            SunoAPIError: If cover generation request fails
        """
        payload = {
            "taskId": music_task_id,
            "callBackUrl": self.callback_url
        }

        try:
            response = self.session.post(
                self.COVER_ENDPOINT,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()

            # Handle nested response structure
            task_id = result.get('taskId') or result.get('data', {}).get('taskId')

            if not task_id:
                raise SunoAPIError(f"No taskId in cover response: {result}")

            return task_id

        except requests.exceptions.RequestException as e:
            raise SunoAPIError(f"Failed to generate cover: {e}")

    def get_cover_urls(self, cover_task_id: str) -> Tuple[List[str], Dict]:
        """
        Get generated cover image URLs

        Args:
            cover_task_id: Cover task ID from generate_cover()

        Returns:
            Tuple of (cover_urls, metadata)
            Typically returns 2 cover variants

        Raises:
            SunoAPIError: If fetching fails
        """
        # Wait for cover generation to complete
        cover_urls, metadata = self.wait_for_completion(
            cover_task_id,
            poll_interval=5,
            max_wait=300  # Covers usually faster than songs
        )

        return cover_urls, metadata
