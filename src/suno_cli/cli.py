"""
CLI interface for suno-cli
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

import click
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .api import SunoClient, SunoAPIError
from .tags import set_id3_tags, extract_tags_from_metadata, TaggingError
from .config import Config, ConfigError

console = Console()


def format_filename(
    format_string: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    track: Optional[int] = None,
    variant: int = 1,
) -> str:
    """
    Format filename using placeholders

    Args:
        format_string: Format string with placeholders
        title: Song title
        artist: Artist name
        track: Track number
        variant: Variant number (1, 2, etc.)

    Returns:
        Formatted filename

    Placeholders:
        {title} - Song title
        {artist} - Artist name
        {track} - Track number (formatted with leading zero if < 10)
        {variant} - Variant number
    """
    # Sanitize values for filesystem
    def sanitize(value: Optional[str]) -> str:
        if value is None:
            return "Unknown"
        # Replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        result = str(value)
        for char in invalid_chars:
            result = result.replace(char, '_')
        return result.strip()

    # Format track number with leading zero if needed
    track_str = f"{track:02d}" if track is not None and track < 100 else str(track) if track is not None else ""

    # Replace placeholders
    filename = format_string
    filename = filename.replace("{title}", sanitize(title))
    filename = filename.replace("{artist}", sanitize(artist))
    filename = filename.replace("{track}", track_str)
    filename = filename.replace("{variant}", str(variant))

    return filename


def load_content(source: str, content_type: str = "content") -> str:
    """
    Load content from a file, URL, or treat as direct string

    Args:
        source: File path, URL, or direct string content
        content_type: Type of content for logging (e.g., "prompt", "style")

    Returns:
        Content as string
    """
    # Check if it's a URL
    if source.startswith(('http://', 'https://')):
        try:
            console.print(f"[dim]Fetching {content_type} from URL: {source}[/dim]")
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            return response.text.strip()
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error fetching {content_type} from URL: {e}[/red]")
            sys.exit(1)

    # Check if it's a file
    if Path(source).exists():
        try:
            with open(source, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                console.print(f"[dim]Loaded {content_type} from file: {source}[/dim]")
                return content
        except Exception as e:
            console.print(f"[red]Error reading {content_type} file: {e}[/red]")
            sys.exit(1)

    # Treat as direct string
    console.print(f"[dim]Using {content_type} string (length: {len(source)} chars)[/dim]")
    return source


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option()
@click.option('--config', type=click.Path(), help='Path to config file (default: ~/.suno-cli/config.yaml)')
@click.pass_context
def cli(ctx, config):
    """
    suno-cli: Generate songs with Suno AI from the command line

    Set your API key in config file or environment variable:
    SUNO_API_KEY=your_key_here
    """
    # Load config and store in context
    ctx.ensure_object(dict)
    try:
        ctx.obj['config'] = Config(config)
    except ConfigError as e:
        console.print(f"[yellow]Warning: Config file error: {e}[/yellow]")
        ctx.obj['config'] = Config()  # Use defaults


@cli.command()
@click.option('--prompt', '-p', required=True, help='Lyrics/prompt (file path, URL, or direct string)')
@click.option('--title', '-t', help='Song title (max 80 chars) - required for custom mode')
@click.option('--style', '-s', help='Music style/genre (string or file path) - required for custom mode')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--model', '-m',
              type=click.Choice(['V5', 'V4_5PLUS', 'V4_5ALL', 'V4_5', 'V4'], case_sensitive=False),
              help='AI model (default: from config or V4_5ALL)')
@click.option('--instrumental', is_flag=True, help='Generate instrumental only (no vocals)')
@click.option('--gender', '-g',
              type=click.Choice(['male', 'female'], case_sensitive=False),
              help='Vocal gender (default: from config or male)')
@click.option('--callback-url', help='Callback URL for task completion notifications')
@click.option('--duration', '-d', type=int, help='[Experimental] Song duration in seconds')
@click.option('--cover', '-c', type=click.Path(exists=True), help='Custom cover image (overrides API cover)')
@click.option('--generate-cover', is_flag=True, help='Generate cover art using Suno API (costs credits)')
@click.option('--artist', help='Artist name for ID3 tags (default: from config or Suno AI)')
@click.option('--album', help='Album name for ID3 tags')
@click.option('--track', type=int, help='Track number for ID3 tags (e.g., 5 for track 5 of album)')
@click.option('--no-tags', is_flag=True, help='Skip ID3 tag generation')
@click.option('--filename-format', help='Filename format (default: "{track} - {artist} - {title} ({variant}).mp3"). Placeholders: {track}, {artist}, {title}, {variant}')
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key (or set SUNO_API_KEY env var)')
@click.option('--poll-interval', type=int, help='Status polling interval in seconds (default: from config or 10)')
@click.option('--max-wait', type=int, help='Maximum wait time in seconds (default: from config or 600)')
@click.pass_context
def generate(
    ctx,
    prompt: str,
    title: Optional[str],
    style: Optional[str],
    output: str,
    model: str,
    instrumental: bool,
    gender: str,
    callback_url: Optional[str],
    duration: Optional[int],
    cover: Optional[str],
    generate_cover: bool,
    artist: str,
    album: Optional[str],
    track: Optional[int],
    no_tags: bool,
    filename_format: Optional[str],
    api_key: Optional[str],
    poll_interval: int,
    max_wait: int
):
    """
    Generate music with Suno AI

    TWO MODES:

    1. Simple Mode (auto-generate title & style):
       suno generate --prompt <prompt> -o ./output

    2. Custom Mode (full control):
       suno generate --prompt <prompt> -t "Title" -s <style> -o ./output

    The --prompt and --style options accept:
    - File path (e.g., lyrics.txt, style.txt)
    - URL (e.g., https://example.com/lyrics.txt)
    - Direct string (e.g., "Verse 1...", "pop, upbeat")

    Examples:
        # Simple mode with string
        suno generate --prompt "Create an upbeat pop song about summer" -o ./output

        # Simple mode with file (short form)
        suno generate -p prompt.txt -o ./output

        # Custom mode - strings
        suno generate -p "Verse 1..." -t "My Song" -s "pop, upbeat, 120 BPM" -o ./output

        # Custom mode - files
        suno generate --prompt lyrics.txt -t "My Song" -s style.txt -o ./output

        # Custom mode - mixed
        suno generate -p lyrics.txt -t "My Song" -s "pop, energetic" -o ./output

        # Instrumental with file
        suno generate -p prompt.txt -t "Ambient" -s "ambient, cinematic" --instrumental -o ./output
    """
    # Get config
    config = ctx.obj.get('config', Config())

    # Apply config defaults (Priority: CLI args > config file > hardcoded defaults)
    if not api_key:
        api_key = config.get('api_key') or os.getenv('SUNO_API_KEY')

    if not output:
        output = config.get('default_output_dir')

    if not output:
        console.print("[red]Error: Output directory required[/red]")
        console.print("Specify with -o/--output or set default_output_dir in config file")
        sys.exit(1)

    model = model or config.get('default_model', 'V4_5ALL')
    gender = gender or config.get('default_gender', 'male')
    artist = artist or config.get('default_artist', 'Suno AI')
    album = album or config.get('default_album')
    callback_url = callback_url or config.get('callback_url')
    poll_interval = poll_interval if poll_interval is not None else config.get('poll_interval', 10)
    max_wait = max_wait if max_wait is not None else config.get('max_wait', 600)
    filename_format = filename_format or config.get('filename_format', '{track} - {artist} - {title} ({variant}).mp3')

    # Get API key
    if not api_key:
        console.print("[red]Error: SUNO_API_KEY not found[/red]")
        console.print("Set it in config file, environment variable, or use --api-key option")
        sys.exit(1)

    # Determine mode based on title and style presence
    custom_mode = bool(title and style)

    # Validate mode requirements
    if custom_mode and not (title and style):
        console.print("[red]Error: Custom mode requires both --title and --style[/red]")
        sys.exit(1)

    # Handle prompt parameter (can be file, URL, or string)
    prompt_text = load_content(prompt, "prompt")

    # Validate prompt length based on mode
    if not custom_mode and len(prompt_text) > 500:
        console.print(f"[yellow]Warning: Simple mode prompt should be max 500 chars (current: {len(prompt_text)})[/yellow]")
        console.print("[yellow]Consider using custom mode with --title and --style for longer prompts[/yellow]")

    # Handle style parameter (can be file, URL, or string) in custom mode
    style_text = None
    if custom_mode and style:
        style_text = load_content(style, "style")

    # Create output directory
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Initialize client with callback URL if provided
    client = SunoClient(api_key, callback_url=callback_url if callback_url else None)

    try:
        # Show mode info
        mode_str = "Custom Mode" if custom_mode else "Simple Mode (AI will generate title & style)"
        console.print(f"[dim]Mode: {mode_str}[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Start generation
            task_desc = f"Starting generation for '{title}'..." if title else "Starting generation..."
            task = progress.add_task(task_desc, total=None)

            task_id = client.generate_song(
                lyrics=prompt_text,
                title=title,
                style=style_text,
                model=model,
                vocal_gender=gender,
                instrumental=instrumental,
                duration=duration,
                custom_mode=custom_mode
            )

            console.print(f"[green]✓[/green] Generation started (Task ID: {task_id})")

            # Wait for completion
            progress.update(task, description=f"Generating '{title}' (this may take 2-3 minutes)...")

            audio_urls, metadata = client.wait_for_completion(
                task_id,
                poll_interval=poll_interval,
                max_wait=max_wait
            )

            console.print(f"[green]✓[/green] Generation complete! Found {len(audio_urls)} variant(s)")

            # Generate cover art if requested (costs additional credits!)
            generated_cover_urls = []
            if generate_cover and not cover:  # Only if no custom cover provided
                try:
                    console.print(f"[yellow]Generating cover art (costs API credits)...[/yellow]")
                    progress.update(task, description="Generating cover art...")

                    cover_task_id = client.generate_cover(task_id)
                    console.print(f"[green]✓[/green] Cover generation started (Task ID: {cover_task_id})")

                    # Wait for cover generation
                    progress.update(task, description="Waiting for cover generation...")
                    generated_cover_urls, cover_metadata = client.get_cover_urls(cover_task_id)

                    console.print(f"[green]✓[/green] Cover generated! Found {len(generated_cover_urls)} variant(s)")

                    # Download cover variants
                    for idx, cover_url in enumerate(generated_cover_urls, 1):
                        cover_file = output_path / f"cover_{idx}.jpg"
                        progress.update(task, description=f"Downloading cover {idx}...")
                        client.download_audio(cover_url, str(cover_file))  # Reuse download function
                        console.print(f"[green]✓[/green] Cover saved: {cover_file.name}")

                except SunoAPIError as e:
                    console.print(f"[yellow]Warning: Cover generation failed: {e}[/yellow]")
                    console.print(f"[yellow]Continuing with song-embedded cover...[/yellow]")

            # Extract tag information from metadata
            tag_info = extract_tags_from_metadata(metadata)

            # Determine which cover to use for MP3 embedding
            # Priority: custom --cover > first generated cover > API song cover
            cover_for_embedding = cover
            if not cover_for_embedding and generated_cover_urls:
                # Use first generated cover
                cover_for_embedding = str(output_path / "cover_1.jpg")

            # Download audio files
            for idx, url in enumerate(audio_urls, 1):
                progress.update(task, description=f"Downloading variant {idx}/{len(audio_urls)}...")

                # Determine track number for filename
                # Priority: --track option > auto-numbering (if multiple variants) > None
                track_num = track if track is not None else (idx if len(audio_urls) > 1 else None)

                # Format filename
                filename = format_filename(
                    filename_format,
                    title=tag_info.get('title') or title,
                    artist=artist,
                    track=track_num,
                    variant=idx
                )
                output_file = output_path / filename
                client.download_audio(url, str(output_file))

                console.print(f"[green]✓[/green] Downloaded: {output_file}")

                # Set ID3 tags (unless disabled)
                if not no_tags:
                    try:
                        progress.update(task, description=f"Setting ID3 tags for variant {idx}...")

                        # Determine year (current year)
                        from datetime import datetime
                        current_year = str(datetime.now().year)

                        # Set tags
                        # Cover priority: custom file > generated cover > API song cover URL
                        set_id3_tags(
                            mp3_file=str(output_file),
                            title=tag_info.get('title') or title,
                            artist=artist,
                            album=album,
                            genre=tag_info.get('genre'),
                            year=current_year,
                            track_number=track_num,
                            cover_url=tag_info.get('cover_url') if not cover_for_embedding else None,
                            cover_file=cover_for_embedding
                        )

                        console.print(f"[green]✓[/green] Tags set: {output_file.name}")

                    except TaggingError as e:
                        console.print(f"[yellow]Warning: Could not set tags for {output_file.name}: {e}[/yellow]")

            # Save metadata
            metadata_file = output_path / f"metadata-{task_id}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            console.print(f"[green]✓[/green] Metadata saved: {metadata_file.name}")

        console.print(f"\n[bold green]Success![/bold green] Generated {len(audio_urls)} variant(s) in {output_path}")

    except SunoAPIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled by user[/yellow]")
        sys.exit(130)


@cli.command()
@click.argument('task_id')
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--filename-format', help='Filename format (default: "{track} - {artist} - {title} ({variant}).mp3"). Placeholders: {track}, {artist}, {title}, {variant}')
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key')
@click.pass_context
def download(ctx, task_id: str, output: str, filename_format: Optional[str], api_key: Optional[str]):
    """
    Download a previously generated song by task ID

    TASK_ID: The task ID from a previous generation

    Example:
        suno download abc123def456 -o ./output
    """
    # Get config
    config = ctx.obj.get('config', Config())

    # Apply config defaults
    if not api_key:
        api_key = config.get('api_key') or os.getenv('SUNO_API_KEY')

    if not output:
        output = config.get('default_output_dir')

    if not output:
        console.print("[red]Error: Output directory required[/red]")
        console.print("Specify with -o/--output or set default_output_dir in config file")
        sys.exit(1)

    if not api_key:
        console.print("[red]Error: SUNO_API_KEY not found[/red]")
        console.print("Set it in config file, environment variable, or use --api-key option")
        sys.exit(1)

    filename_format = filename_format or config.get('filename_format', '{track} - {artist} - {title} ({variant}).mp3')

    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    client = SunoClient(api_key)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking task status...", total=None)

            status = client.get_status(task_id)
            data = status.get('data', {})
            state = data.get('status', 'UNKNOWN')

            # Accept both SUCCESS and TEXT_SUCCESS as valid completion states
            if state not in ('SUCCESS', 'TEXT_SUCCESS'):
                console.print(f"[yellow]Warning: Task status is '{state}'[/yellow]")
                if state == 'PENDING':
                    console.print("Task is still generating. Wait for it to complete first.")
                    sys.exit(1)

            response_data = data.get('response', {})
            suno_data = response_data.get('sunoData', [])

            if not suno_data:
                console.print("[red]Error: No audio data found for this task[/red]")
                sys.exit(1)

            audio_urls = [item['audioUrl'] for item in suno_data if 'audioUrl' in item]

            # Debug: check for empty URLs
            if audio_urls and not any(audio_urls):
                console.print("[red]Error: Audio URLs are empty[/red]")
                console.print("[dim]Checking alternative URL fields...[/dim]")
                # Try alternative fields
                audio_urls = []
                for item in suno_data:
                    url = item.get('audioUrl') or item.get('sourceAudioUrl') or item.get('audio_url', '')
                    if url:
                        audio_urls.append(url)

            console.print(f"[green]✓[/green] Found {len(audio_urls)} audio file(s)")

            # Extract metadata for filename formatting
            tag_info = extract_tags_from_metadata(data)

            for idx, url in enumerate(audio_urls, 1):
                progress.update(task, description=f"Downloading file {idx}/{len(audio_urls)}...")

                # Format filename
                filename = format_filename(
                    filename_format,
                    title=tag_info.get('title'),
                    artist=config.get('default_artist', 'Suno AI'),
                    track=idx if len(audio_urls) > 1 else None,
                    variant=idx
                )
                output_file = output_path / filename
                client.download_audio(url, str(output_file))

                console.print(f"[green]✓[/green] Downloaded: {output_file}")

            metadata_file = output_path / f"metadata-{task_id}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            console.print(f"[green]✓[/green] Metadata saved: {metadata_file.name}")

        console.print(f"\n[bold green]Success![/bold green] Downloaded {len(audio_urls)} file(s) to {output_path}")

    except SunoAPIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def process_song_download(
    client: SunoClient,
    task_id: str,
    title: str,
    output_path: Path,
    cover: Optional[str],
    generate_cover: bool,
    artist: str,
    album: Optional[str],
    track: Optional[int],
    filename_format: str,
    poll_interval: int,
    max_wait: int,
    progress_task=None,
    progress_obj=None
) -> tuple[int, int]:
    """
    Download and process a completed song task

    Returns:
        tuple of (completed_count, failed_count)
    """
    try:
        # Wait for completion
        if progress_obj and progress_task:
            progress_obj.update(progress_task, description=f"Waiting for '{title}'...")

        audio_urls, metadata = client.wait_for_completion(
            task_id,
            poll_interval=poll_interval,
            max_wait=max_wait
        )

        if progress_obj and progress_task:
            progress_obj.update(progress_task, description=f"Completed '{title}', downloading...")

        # Create output directory
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate cover if requested
        generated_cover_urls = []
        if generate_cover and not cover:
            try:
                cover_task_id = client.generate_cover(task_id)
                generated_cover_urls, _ = client.get_cover_urls(cover_task_id)

                # Download cover variants
                for cover_idx, cover_url in enumerate(generated_cover_urls, 1):
                    cover_file = output_path / f"cover_{cover_idx}.jpg"
                    client.download_audio(cover_url, str(cover_file))

            except SunoAPIError:
                pass  # Silently continue without generated cover

        # Determine cover for embedding
        cover_for_embedding = cover
        if not cover_for_embedding and generated_cover_urls:
            cover_for_embedding = str(output_path / "cover_1.jpg")

        # Extract tag information
        tag_info = extract_tags_from_metadata(metadata)

        # Download audio files
        for audio_idx, url in enumerate(audio_urls, 1):
            # Determine track number for filename
            track_num = track if track is not None else (audio_idx if len(audio_urls) > 1 else None)

            # Format filename
            filename = format_filename(
                filename_format,
                title=tag_info.get('title') or title,
                artist=artist,
                track=track_num,
                variant=audio_idx
            )
            output_file = output_path / filename
            client.download_audio(url, str(output_file))

            # Set ID3 tags
            try:
                from datetime import datetime
                current_year = str(datetime.now().year)

                set_id3_tags(
                    mp3_file=str(output_file),
                    title=tag_info.get('title') or title,
                    artist=artist,
                    album=album,
                    genre=tag_info.get('genre'),
                    year=current_year,
                    track_number=track_num,
                    cover_url=tag_info.get('cover_url') if not cover_for_embedding else None,
                    cover_file=cover_for_embedding
                )
            except TaggingError:
                pass  # Continue without tags

        # Save metadata
        metadata_file = output_path / f"metadata-{task_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

        console.print(f"[green]✓[/green] {title} -> {output_path}")
        return (1, 0)  # 1 completed, 0 failed

    except SunoAPIError as e:
        console.print(f"[red]✗[/red] {title}: {e}")
        return (0, 1)  # 0 completed, 1 failed


@cli.command()
@click.argument('batch_file', type=click.Path(exists=True))
@click.option('--output-base', '-o', type=click.Path(), help='Base output directory (each song gets a subdirectory)')
@click.option('--parallel', '-p', is_flag=True, help='Generate songs in parallel (starts all at once)')
@click.option('--interactive', '-i', is_flag=True, help='Ask before processing each song (sequential mode only)')
@click.option('--delay', '-d', type=int, default=0, help='Delay in seconds between starting each song (ignored with --parallel)')
@click.option('--filename-format', help='Filename format (default: "{track} - {artist} - {title} ({variant}).mp3"). Placeholders: {track}, {artist}, {title}, {variant}')
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key (or set SUNO_API_KEY env var)')
@click.pass_context
def batch(ctx, batch_file: str, output_base: Optional[str], parallel: bool, interactive: bool, delay: int, filename_format: Optional[str], api_key: Optional[str]):
    """
    Generate multiple songs from a YAML batch file

    BATCH_FILE: Path or URL to YAML file containing song definitions

    Example YAML format:
        # Global settings
        output_base: ./my-album          # Output directory (optional)
        use_subdirectories: true         # Create subdirs per song (default: true)

        # Defaults for all songs (all optional, can be overridden per song)
        # Available fields: prompt, style, model, gender, artist, album, cover,
        #                   generate_cover, instrumental, duration
        defaults:
          prompt: ./default-lyrics.txt   # Default prompt for all songs (optional)
          style: "pop rock, energetic"   # Default style for all songs (optional)
          model: V4_5ALL
          gender: male
          artist: "My Band"
          album: "My Album"
          cover: ./cover.jpg             # Default cover for all songs
          generate_cover: false
          instrumental: false

        songs:
          - title: "Song 1"
            prompt: path/to/lyrics1.txt
            style: "pop, upbeat"
            track: 1
            output: track01              # Custom subdir name (optional)
            # Uses all defaults

          - title: "Song 2"
            prompt: "Verse 1: Walking..."
            style: path/to/style2.txt
            track: 2
            model: V5                    # Override default model
            gender: female               # Override default gender

    Priority for all parameters:
        1. Song-specific field (highest priority)
        2. YAML 'defaults' section
        3. Config file settings
        4. Hardcoded defaults (lowest priority)

    Output directory priority:
        1. Song-specific 'output' field
        2. CLI --output-base option
        3. YAML 'output_base' field
        4. Config file default_output_dir

    Examples:
        # With subdirectories (default)
        suno batch songs.yaml -o ./album

        # All songs in one directory
        suno batch songs-single-dir.yaml  # (with use_subdirectories: false)

        # Parallel generation
        suno batch songs.yaml --parallel

        # From URL
        suno batch https://example.com/album.yaml
    """
    import yaml
    import time as time_module
    from datetime import datetime

    # Get config
    config = ctx.obj.get('config', Config())

    # Apply config defaults
    if not api_key:
        api_key = config.get('api_key') or os.getenv('SUNO_API_KEY')

    if not api_key:
        console.print("[red]Error: SUNO_API_KEY not found[/red]")
        console.print("Set it in config file, environment variable, or use --api-key option")
        sys.exit(1)

    filename_format = filename_format or config.get('filename_format', '{track} - {artist} - {title} ({variant}).mp3')

    # Load batch YAML (supports files and URLs)
    try:
        yaml_content = load_content(batch_file, "batch YAML")
        batch_data = yaml.safe_load(yaml_content)
    except Exception as e:
        console.print(f"[red]Error loading batch file: {e}[/red]")
        sys.exit(1)

    songs = batch_data.get('songs', [])
    if not songs:
        console.print("[red]Error: No songs found in batch file[/red]")
        console.print("Expected format: songs: [...]")
        sys.exit(1)

    # Get global settings from YAML
    yaml_output_base = batch_data.get('output_base')
    use_subdirectories = batch_data.get('use_subdirectories', True)
    yaml_defaults = batch_data.get('defaults', {})

    # Determine final output_base
    # Priority: CLI --output-base > YAML output_base > config default_output_dir
    final_output_base = output_base or yaml_output_base or config.get('default_output_dir')

    if not final_output_base:
        console.print("[red]Error: No output directory specified[/red]")
        console.print("Specify in YAML (output_base), CLI (-o), or config file (default_output_dir)")
        sys.exit(1)

    console.print(f"[bold]Batch Generation[/bold]: {len(songs)} song(s)")
    console.print(f"[dim]Mode: {'Parallel' if parallel else 'Sequential'}[/dim]")
    console.print(f"[dim]Output: {final_output_base} (subdirectories: {use_subdirectories})[/dim]")

    # Warn if interactive mode is used with parallel mode
    if interactive and parallel:
        console.print("[yellow]Warning: --interactive is ignored in parallel mode[/yellow]")
        interactive = False
    elif interactive and len(songs) == 1:
        # No point asking if only 1 song
        interactive = False

    if interactive:
        console.print("[dim]Interactive mode: You will be prompted after each song[/dim]")

    console.print()  # Empty line

    batch_start_time = datetime.now()

    # Initialize client
    callback_url = config.get('callback_url')
    client = SunoClient(api_key, callback_url=callback_url if callback_url else None)

    # Get poll settings from config
    poll_interval = config.get('poll_interval', 10)
    max_wait = config.get('max_wait', 600)

    completed = 0
    failed = 0

    if parallel:
        # ===== PARALLEL MODE =====
        # Start all songs at once, then wait/download all
        console.print("[dim]Starting all songs in parallel...[/dim]\n")

        tasks = []

        # Start all generations
        for idx, song_def in enumerate(songs, 1):
            # Helper function to get value with priority: song > yaml defaults > config
            def get_param(key, config_key=None, fallback=None):
                """Get parameter with priority: song > yaml defaults > config > fallback"""
                if key in song_def and song_def[key] is not None:
                    return song_def[key]
                if key in yaml_defaults and yaml_defaults[key] is not None:
                    return yaml_defaults[key]
                if config_key:
                    return config.get(config_key, fallback)
                return fallback

            # Extract song parameters
            title = song_def.get('title')
            prompt_param = get_param('prompt')
            style_param = get_param('style')
            output_dir = song_def.get('output')
            model = get_param('model', 'default_model', 'V4_5ALL')
            gender = get_param('gender', 'default_gender', 'male')
            instrumental = get_param('instrumental', fallback=False)
            duration = get_param('duration')
            cover = get_param('cover')
            generate_cover = get_param('generate_cover', fallback=False)
            artist = get_param('artist', 'default_artist', 'Suno AI')
            album = get_param('album', 'default_album')
            track = song_def.get('track') or idx

            # Determine output directory
            if output_dir:
                output_path = Path(output_dir)
                if not output_path.is_absolute():
                    output_path = Path(final_output_base) / output_dir
            else:
                if use_subdirectories:
                    output_path = Path(final_output_base) / f"song_{idx:02d}"
                else:
                    output_path = Path(final_output_base)

            # Validate required fields
            if not title:
                console.print(f"[red]Error: Song {idx} missing required field 'title'[/red]")
                sys.exit(1)
            if not prompt_param:
                console.print(f"[red]Error: Song {idx} missing 'prompt' field[/red]")
                sys.exit(1)
            if not style_param:
                console.print(f"[red]Error: Song {idx} missing 'style' field[/red]")
                sys.exit(1)

            # Load content
            lyrics_text = load_content(prompt_param, f"prompt for song {idx}")
            style_text = load_content(style_param, f"style for song {idx}")

            # Start generation
            console.print(f"[cyan]{idx}/{len(songs)}[/cyan] Starting: [bold]{title}[/bold]")

            try:
                task_id = client.generate_song(
                    lyrics=lyrics_text,
                    title=title,
                    style=style_text,
                    model=model,
                    vocal_gender=gender,
                    instrumental=instrumental,
                    duration=duration,
                    custom_mode=True
                )

                tasks.append({
                    'task_id': task_id,
                    'title': title,
                    'output_path': output_path,
                    'cover': cover,
                    'generate_cover': generate_cover,
                    'artist': artist,
                    'album': album,
                    'track': track,
                })

                console.print(f"  [green]✓[/green] Task ID: {task_id}")

            except SunoAPIError as e:
                console.print(f"  [red]✗ Failed: {e}[/red]")
                failed += 1
                continue

        if not tasks:
            console.print("[red]No songs were started successfully[/red]")
            sys.exit(1)

        console.print(f"\n[green]✓[/green] Started {len(tasks)} generation(s)")
        console.print("[dim]Waiting for all songs to complete...[/dim]\n")

        # Wait for all completions and download
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for task_info in tasks:
                progress_task = progress.add_task("", total=None)

                comp, fail = process_song_download(
                    client=client,
                    task_id=task_info['task_id'],
                    title=task_info['title'],
                    output_path=task_info['output_path'],
                    cover=task_info['cover'],
                    generate_cover=task_info['generate_cover'],
                    artist=task_info['artist'],
                    album=task_info['album'],
                    track=task_info['track'],
                    filename_format=filename_format,
                    poll_interval=poll_interval,
                    max_wait=max_wait,
                    progress_task=progress_task,
                    progress_obj=progress
                )
                completed += comp
                failed += fail

    else:
        # ===== SEQUENTIAL MODE =====
        # Process each song completely before starting the next
        console.print("[dim]Processing songs sequentially...[/dim]\n")

        # Track if user selected "All" mode
        interactive_all_mode = False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            for idx, song_def in enumerate(songs, 1):
                # Helper function to get value with priority: song > yaml defaults > config
                def get_param(key, config_key=None, fallback=None):
                    """Get parameter with priority: song > yaml defaults > config > fallback"""
                    if key in song_def and song_def[key] is not None:
                        return song_def[key]
                    if key in yaml_defaults and yaml_defaults[key] is not None:
                        return yaml_defaults[key]
                    if config_key:
                        return config.get(config_key, fallback)
                    return fallback

                # Extract song parameters
                title = song_def.get('title')
                prompt_param = get_param('prompt')
                style_param = get_param('style')
                output_dir = song_def.get('output')
                model = get_param('model', 'default_model', 'V4_5ALL')
                gender = get_param('gender', 'default_gender', 'male')
                instrumental = get_param('instrumental', fallback=False)
                duration = get_param('duration')
                cover = get_param('cover')
                generate_cover = get_param('generate_cover', fallback=False)
                artist = get_param('artist', 'default_artist', 'Suno AI')
                album = get_param('album', 'default_album')
                track = song_def.get('track') or idx

                # Determine output directory
                if output_dir:
                    output_path = Path(output_dir)
                    if not output_path.is_absolute():
                        output_path = Path(final_output_base) / output_dir
                else:
                    if use_subdirectories:
                        output_path = Path(final_output_base) / f"song_{idx:02d}"
                    else:
                        output_path = Path(final_output_base)

                # Validate required fields
                if not title:
                    console.print(f"[red]Error: Song {idx} missing required field 'title'[/red]")
                    sys.exit(1)
                if not prompt_param:
                    console.print(f"[red]Error: Song {idx} missing 'prompt' field[/red]")
                    sys.exit(1)
                if not style_param:
                    console.print(f"[red]Error: Song {idx} missing 'style' field[/red]")
                    sys.exit(1)

                # Load content
                lyrics_text = load_content(prompt_param, f"prompt for song {idx}")
                style_text = load_content(style_param, f"style for song {idx}")

                # Start generation
                console.print(f"[cyan]{idx}/{len(songs)}[/cyan] Starting: [bold]{title}[/bold]")

                try:
                    progress_task = progress.add_task(f"Starting '{title}'...", total=None)

                    task_id = client.generate_song(
                        lyrics=lyrics_text,
                        title=title,
                        style=style_text,
                        model=model,
                        vocal_gender=gender,
                        instrumental=instrumental,
                        duration=duration,
                        custom_mode=True
                    )

                    console.print(f"  [green]✓[/green] Task ID: {task_id}")

                    # Immediately wait and download this song
                    comp, fail = process_song_download(
                        client=client,
                        task_id=task_id,
                        title=title,
                        output_path=output_path,
                        cover=cover,
                        generate_cover=generate_cover,
                        artist=artist,
                        album=album,
                        track=track,
                        filename_format=filename_format,
                        poll_interval=poll_interval,
                        max_wait=max_wait,
                        progress_task=progress_task,
                        progress_obj=progress
                    )
                    completed += comp
                    failed += fail

                    # Interactive mode: Ask user if they want to continue
                    if interactive and not interactive_all_mode and idx < len(songs):
                        console.print()  # Empty line for spacing
                        try:
                            response = click.prompt(
                                "Continue?",
                                type=click.Choice(['Y', 'n', 'A'], case_sensitive=False),
                                default='Y',
                                show_choices=True,
                                show_default=False
                            ).upper()

                            if response == 'N':
                                console.print("[yellow]Stopping batch processing[/yellow]")
                                break  # Exit the loop
                            elif response == 'A':
                                console.print("[dim]Continuing with all remaining songs...[/dim]")
                                interactive_all_mode = True
                            # Y is default, just continue
                        except (KeyboardInterrupt, click.Abort):
                            console.print("\n[yellow]Cancelled by user[/yellow]")
                            console.print(f"[dim]Completed: {completed}/{len(songs)}, Failed: {failed}/{len(songs)}[/dim]")
                            sys.exit(130)
                        console.print()  # Empty line for spacing

                    # Delay before next song (if configured)
                    if idx < len(songs) and delay > 0:
                        console.print(f"  [dim]Waiting {delay}s before next song...[/dim]")
                        time_module.sleep(delay)

                except SunoAPIError as e:
                    console.print(f"  [red]✗ Failed to start: {e}[/red]")
                    failed += 1

                    # Also ask in interactive mode after failures
                    if interactive and not interactive_all_mode and idx < len(songs):
                        console.print()
                        try:
                            response = click.prompt(
                                "Continue despite error?",
                                type=click.Choice(['Y', 'n', 'A'], case_sensitive=False),
                                default='Y',
                                show_choices=True,
                                show_default=False
                            ).upper()

                            if response == 'N':
                                console.print("[yellow]Stopping batch processing[/yellow]")
                                break
                            elif response == 'A':
                                console.print("[dim]Continuing with all remaining songs...[/dim]")
                                interactive_all_mode = True
                        except (KeyboardInterrupt, click.Abort):
                            console.print("\n[yellow]Cancelled by user[/yellow]")
                            console.print(f"[dim]Completed: {completed}/{len(songs)}, Failed: {failed}/{len(songs)}[/dim]")
                            sys.exit(130)
                        console.print()

                    continue

                except KeyboardInterrupt:
                    console.print("\n[yellow]Cancelled by user[/yellow]")
                    console.print(f"[dim]Completed: {completed}/{len(songs)}, Failed: {failed}/{len(songs)}[/dim]")
                    sys.exit(130)

    # Summary
    batch_duration = (datetime.now() - batch_start_time).total_seconds()
    console.print(f"\n[bold green]Batch Complete![/bold green]")
    console.print(f"[green]✓[/green] Completed: {completed}/{len(songs)}")
    if failed > 0:
        console.print(f"[red]✗[/red] Failed: {failed}/{len(songs)}")
    console.print(f"[dim]Total time: {batch_duration:.1f}s[/dim]")


@cli.command()
@click.option('--path', type=click.Path(), help='Path to create config file (default: ~/.suno-cli/config.yaml)')
def init_config(path: Optional[str]):
    """
    Create a default config file

    Example:
        suno init-config
        suno init-config --path ./custom-config.yaml
    """
    try:
        config_path = Path(path) if path else Config.DEFAULT_CONFIG_PATH

        if config_path.exists():
            console.print(f"[yellow]Config file already exists: {config_path}[/yellow]")
            if not click.confirm("Overwrite?"):
                console.print("[dim]Cancelled[/dim]")
                return

        Config.create_default_config(config_path)
        console.print(f"[green]✓[/green] Created config file: {config_path}")
        console.print(f"\n[dim]Edit the file to customize your settings[/dim]")

    except Exception as e:
        console.print(f"[red]Error creating config: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('task_id')
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key')
@click.pass_context
def status(ctx, task_id: str, api_key: Optional[str]):
    """
    Check status of a generation task

    TASK_ID: The task ID to check

    Example:
        suno status abc123def456
    """
    # Get config
    config = ctx.obj.get('config', Config())

    # Apply config defaults
    if not api_key:
        api_key = config.get('api_key') or os.getenv('SUNO_API_KEY')

    if not api_key:
        console.print("[red]Error: SUNO_API_KEY not found[/red]")
        console.print("Set it in config file, environment variable, or use --api-key option")
        sys.exit(1)

    client = SunoClient(api_key)

    try:
        result = client.get_status(task_id)
        data = result.get('data', {})
        state = data.get('status', 'UNKNOWN')

        console.print(f"\n[bold]Task ID:[/bold] {task_id}")
        console.print(f"[bold]Status:[/bold] {state}")

        if state == 'SUCCESS':
            response_data = data.get('response', {})
            suno_data = response_data.get('sunoData', [])
            console.print(f"[bold]Variants:[/bold] {len(suno_data)}")
            console.print("\n[green]✓ Generation complete![/green] Use 'suno download' to get the files.")
        elif state == 'PENDING':
            console.print("\n[yellow]⏳ Still generating... Check again in a few minutes.[/yellow]")
        elif state == 'FAILED':
            error = data.get('error', 'Unknown error')
            console.print(f"\n[red]✗ Generation failed: {error}[/red]")

        # Show raw data if verbose
        console.print(f"\n[dim]Raw response:[/dim]")
        console.print(json.dumps(result, indent=2))

    except SunoAPIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == '__main__':
    cli()
