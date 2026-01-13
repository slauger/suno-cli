"""
Convert MP3 files to MP4 videos (for YouTube uploads)
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from mutagen.id3 import ID3, APIC


class ConversionError(Exception):
    """Base exception for conversion errors"""
    pass


def check_ffmpeg_installed() -> bool:
    """
    Check if ffmpeg is installed and available

    Returns:
        True if ffmpeg is available, False otherwise
    """
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def extract_cover_from_mp3(mp3_file: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Extract cover art from MP3 ID3 tags

    Args:
        mp3_file: Path to MP3 file
        output_path: Optional path to save cover (default: temp file)

    Returns:
        Path to extracted cover file, or None if no cover found

    Raises:
        ConversionError: If extraction fails
    """
    try:
        audio = ID3(mp3_file)

        # Find APIC (cover art) frame
        for tag in audio.values():
            if isinstance(tag, APIC):
                # Determine file extension from mime type
                ext = 'jpg'
                if tag.mime == 'image/png':
                    ext = 'png'
                elif tag.mime == 'image/gif':
                    ext = 'gif'

                # Save to output path or temp file
                if output_path:
                    cover_path = output_path
                else:
                    # Create temp file
                    fd, cover_path = tempfile.mkstemp(suffix=f'.{ext}')
                    os.close(fd)

                with open(cover_path, 'wb') as f:
                    f.write(tag.data)

                return cover_path

        # No cover found
        return None

    except Exception as e:
        raise ConversionError(f"Failed to extract cover art: {e}")


def convert_mp3_to_mp4(
    mp3_file: str,
    output_file: Optional[str] = None,
    cover_file: Optional[str] = None,
    resolution: str = "1920x1080",
    framerate: int = 1,
    overwrite: bool = False
) -> str:
    """
    Convert MP3 to MP4 video with static cover image

    Args:
        mp3_file: Path to input MP3 file
        output_file: Path to output MP4 file (default: same name as input with .mp4 extension)
        cover_file: Path to cover image (if None, extracts from MP3 ID3 tags)
        resolution: Video resolution (default: 1920x1080)
        framerate: Video framerate (default: 1 fps for static image)
        overwrite: Overwrite existing output file

    Returns:
        Path to created MP4 file

    Raises:
        ConversionError: If conversion fails
    """
    # Check ffmpeg
    if not check_ffmpeg_installed():
        raise ConversionError(
            "ffmpeg is not installed. Please install ffmpeg:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: sudo apt-get install ffmpeg\n"
            "  Windows: Download from https://ffmpeg.org/download.html"
        )

    # Validate input
    mp3_path = Path(mp3_file)
    if not mp3_path.exists():
        raise ConversionError(f"Input file not found: {mp3_file}")

    # Determine output file
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = mp3_path.with_suffix('.mp4')

    # Check if output exists
    if output_path.exists() and not overwrite:
        raise ConversionError(
            f"Output file already exists: {output_path}\n"
            "Use --overwrite to replace it"
        )

    # Handle cover art
    temp_cover = None
    try:
        if cover_file:
            # Use provided cover
            if not Path(cover_file).exists():
                raise ConversionError(f"Cover file not found: {cover_file}")
            cover_path = cover_file
        else:
            # Extract from MP3
            cover_path = extract_cover_from_mp3(str(mp3_path))
            if not cover_path:
                raise ConversionError(
                    "No cover art found in MP3 file. "
                    "Please provide a cover image with --cover option"
                )
            temp_cover = cover_path  # Mark for cleanup

        # Build ffmpeg command
        # -loop 1: loop the image
        # -framerate: input framerate (low since it's static)
        # -i: input files (image, then audio)
        # -c:v libx264: H.264 video codec (YouTube compatible)
        # -tune stillimage: optimize for static image
        # -pix_fmt yuv420p: pixel format (YouTube compatible)
        # -c:a aac: AAC audio codec (YouTube compatible)
        # -b:a 192k: audio bitrate
        # -shortest: end when audio ends
        # -movflags +faststart: optimize for streaming

        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-framerate', str(framerate),
            '-i', cover_path,
            '-i', str(mp3_path),
            '-c:v', 'libx264',
            '-tune', 'stillimage',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            '-movflags', '+faststart',
            '-vf', f'scale={resolution}:force_original_aspect_ratio=decrease,pad={resolution}:(ow-iw)/2:(oh-ih)/2',
        ]

        if overwrite:
            cmd.append('-y')

        cmd.append(str(output_path))

        # Run ffmpeg
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise ConversionError(f"ffmpeg failed:\n{result.stderr}")

        return str(output_path)

    finally:
        # Cleanup temp cover if created
        if temp_cover and Path(temp_cover).exists():
            try:
                os.unlink(temp_cover)
            except:
                pass  # Ignore cleanup errors


def convert_directory(
    directory: str,
    output_dir: Optional[str] = None,
    cover_file: Optional[str] = None,
    resolution: str = "1920x1080",
    framerate: int = 1,
    overwrite: bool = False
) -> list[tuple[str, str]]:
    """
    Convert all MP3 files in a directory to MP4

    Args:
        directory: Input directory containing MP3 files
        output_dir: Output directory (default: same as input)
        cover_file: Cover image to use for all files (if None, extracts from each MP3)
        resolution: Video resolution
        framerate: Video framerate
        overwrite: Overwrite existing files

    Returns:
        List of tuples (input_file, output_file) for successful conversions

    Raises:
        ConversionError: If directory not found or no MP3 files found
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        raise ConversionError(f"Directory not found: {directory}")

    # Find all MP3 files
    mp3_files = list(dir_path.glob("*.mp3"))
    if not mp3_files:
        raise ConversionError(f"No MP3 files found in: {directory}")

    # Determine output directory
    out_path = Path(output_dir) if output_dir else dir_path
    out_path.mkdir(parents=True, exist_ok=True)

    # Convert each file
    results = []
    errors = []

    for mp3_file in mp3_files:
        try:
            output_file = out_path / mp3_file.with_suffix('.mp4').name

            converted = convert_mp3_to_mp4(
                str(mp3_file),
                str(output_file),
                cover_file=cover_file,
                resolution=resolution,
                framerate=framerate,
                overwrite=overwrite
            )

            results.append((str(mp3_file), converted))

        except ConversionError as e:
            errors.append((str(mp3_file), str(e)))

    # Report errors if any
    if errors:
        error_msg = "\n".join([f"  {f}: {e}" for f, e in errors])
        raise ConversionError(f"Some conversions failed:\n{error_msg}")

    return results
