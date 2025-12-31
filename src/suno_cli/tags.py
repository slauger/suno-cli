"""
ID3 tag management for MP3 files
"""

import requests
from pathlib import Path
from typing import Optional, Dict, Any
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error as ID3Error
from mutagen.mp3 import MP3


class TaggingError(Exception):
    """Base exception for tagging errors"""
    pass


def set_id3_tags(
    mp3_file: str,
    title: Optional[str] = None,
    artist: str = "Suno AI",
    album: Optional[str] = None,
    genre: Optional[str] = None,
    year: Optional[str] = None,
    track_number: Optional[int] = None,
    cover_url: Optional[str] = None,
    cover_file: Optional[str] = None,
) -> None:
    """
    Set ID3v2 tags for an MP3 file

    Args:
        mp3_file: Path to MP3 file
        title: Song title
        artist: Artist name (default: "Suno AI")
        album: Album name
        genre: Genre/style
        year: Year
        track_number: Track number
        cover_url: URL to download cover art from
        cover_file: Path to local cover art file

    Raises:
        TaggingError: If tagging fails
    """
    try:
        # Set basic tags
        try:
            audio = EasyID3(mp3_file)
        except ID3Error.ID3NoHeaderError:
            # File has no ID3 tag yet, create one
            audio = MP3(mp3_file)
            audio.add_tags()
            audio = EasyID3(mp3_file)

        # Set available tags
        audio['artist'] = artist
        if title:
            audio['title'] = title
        if album:
            audio['album'] = album
            audio['albumartist'] = artist
        if genre:
            audio['genre'] = genre
        if year:
            audio['date'] = year
        if track_number:
            audio['tracknumber'] = str(track_number)

        audio.save()

        # Add cover art if provided
        cover_data = None

        # Priority: custom file > URL from API
        if cover_file and Path(cover_file).exists():
            with open(cover_file, 'rb') as f:
                cover_data = f.read()
        elif cover_url:
            # Download cover from URL
            try:
                response = requests.get(cover_url, timeout=30)
                response.raise_for_status()
                cover_data = response.content
            except Exception as e:
                # Don't fail if cover download fails, just skip it
                print(f"Warning: Could not download cover art: {e}")

        if cover_data:
            try:
                audio_full = ID3(mp3_file)
                audio_full.delall("APIC")  # Remove existing covers

                # Detect image format from data
                mime_type = 'image/jpeg'
                if cover_data.startswith(b'\x89PNG'):
                    mime_type = 'image/png'
                elif cover_data.startswith(b'GIF'):
                    mime_type = 'image/gif'

                audio_full.add(
                    APIC(
                        encoding=3,  # UTF-8
                        mime=mime_type,
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=cover_data
                    )
                )
                audio_full.save()
            except Exception as e:
                # Don't fail if cover embedding fails
                print(f"Warning: Could not embed cover art: {e}")

    except Exception as e:
        raise TaggingError(f"Failed to set ID3 tags: {e}")


def extract_tags_from_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract tag information from Suno API metadata

    Args:
        metadata: Metadata dict from API response

    Returns:
        Dict with tag information (title, genre, cover_url, etc.)
    """
    tags = {}

    # Extract from response.sunoData[0] if available
    data = metadata.get('data', {})
    response = data.get('response', {})
    suno_data = response.get('sunoData', [])

    if suno_data and len(suno_data) > 0:
        track_data = suno_data[0]

        # Title
        if 'title' in track_data:
            tags['title'] = track_data['title']

        # Genre/Tags
        if 'tags' in track_data:
            tags['genre'] = track_data['tags']

        # Cover image URL
        if 'imageUrl' in track_data:
            tags['cover_url'] = track_data['imageUrl']

        # Duration (for info)
        if 'duration' in track_data:
            tags['duration'] = track_data['duration']

    return tags
