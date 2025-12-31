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


@click.group()
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
@click.argument('prompt')
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
    api_key: Optional[str],
    poll_interval: int,
    max_wait: int
):
    """
    Generate music with Suno AI

    PROMPT: Lyrics/prompt (file path or direct string)

    TWO MODES:

    1. Simple Mode (auto-generate title & style):
       suno generate <prompt> -o ./output

    2. Custom Mode (full control):
       suno generate <prompt> -t "Title" -s <style> -o ./output

    Both PROMPT and STYLE can be:
    - File path (e.g., lyrics.txt, style.txt)
    - Direct string (e.g., "Verse 1...", "pop, upbeat")

    Examples:
        # Simple mode with string
        suno generate "Create an upbeat pop song about summer" -o ./output

        # Simple mode with file
        suno generate prompt.txt -o ./output

        # Custom mode - strings
        suno generate "Verse 1..." -t "My Song" -s "pop, upbeat, 120 BPM" -o ./output

        # Custom mode - files
        suno generate lyrics.txt -t "My Song" -s style.txt -o ./output

        # Custom mode - mixed
        suno generate lyrics.txt -t "My Song" -s "pop, energetic" -o ./output

        # Instrumental with file
        suno generate prompt.txt -t "Ambient" -s "ambient, cinematic" -o ./output --instrumental
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

                output_file = output_path / f"track_{idx}.mp3"
                client.download_audio(url, str(output_file))

                console.print(f"[green]✓[/green] Downloaded: {output_file}")

                # Set ID3 tags (unless disabled)
                if not no_tags:
                    try:
                        progress.update(task, description=f"Setting ID3 tags for variant {idx}...")

                        # Determine year (current year)
                        from datetime import datetime
                        current_year = str(datetime.now().year)

                        # Determine track number
                        # Priority: --track option > auto-numbering (if multiple variants) > None
                        track_num = track if track is not None else (idx if len(audio_urls) > 1 else None)

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
            metadata_file = output_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)

            console.print(f"[green]✓[/green] Metadata saved: {metadata_file}")

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
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key')
@click.pass_context
def download(ctx, task_id: str, output: str, api_key: Optional[str]):
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

            if state != 'SUCCESS':
                console.print(f"[yellow]Warning: Task status is '{state}' (expected SUCCESS)[/yellow]")
                if state == 'PENDING':
                    console.print("Task is still generating. Wait for it to complete first.")
                    sys.exit(1)

            response_data = data.get('response', {})
            suno_data = response_data.get('sunoData', [])

            if not suno_data:
                console.print("[red]Error: No audio data found for this task[/red]")
                sys.exit(1)

            audio_urls = [item['audioUrl'] for item in suno_data if 'audioUrl' in item]

            console.print(f"[green]✓[/green] Found {len(audio_urls)} audio file(s)")

            for idx, url in enumerate(audio_urls, 1):
                progress.update(task, description=f"Downloading file {idx}/{len(audio_urls)}...")

                output_file = output_path / f"track_{idx}.mp3"
                client.download_audio(url, str(output_file))

                console.print(f"[green]✓[/green] Downloaded: {output_file}")

            metadata_file = output_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            console.print(f"[green]✓[/green] Metadata saved: {metadata_file}")

        console.print(f"\n[bold green]Success![/bold green] Downloaded {len(audio_urls)} file(s) to {output_path}")

    except SunoAPIError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('batch_file', type=click.Path(exists=True))
@click.option('--output-base', '-o', type=click.Path(), help='Base output directory (each song gets a subdirectory)')
@click.option('--parallel', '-p', is_flag=True, help='Generate songs in parallel (starts all at once)')
@click.option('--delay', '-d', type=int, default=0, help='Delay in seconds between starting each song (ignored with --parallel)')
@click.option('--api-key', envvar='SUNO_API_KEY', help='Suno API key (or set SUNO_API_KEY env var)')
@click.pass_context
def batch(ctx, batch_file: str, output_base: Optional[str], parallel: bool, delay: int, api_key: Optional[str]):
    """
    Generate multiple songs from a YAML batch file

    BATCH_FILE: Path or URL to YAML file containing song definitions

    Example YAML format:
        songs:
          - title: "Song 1"
            lyrics: path/to/lyrics1.txt
            style: "pop, upbeat"
            output: ./song1
          - title: "Song 2"
            lyrics: "Verse 1: Walking..."
            style: path/to/style2.txt
            model: V5
            gender: female

    Examples:
        suno batch songs.yaml -o ./album
        suno batch https://example.com/album.yaml -o ./album
        suno batch songs.yaml --parallel
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

    console.print(f"[bold]Batch Generation[/bold]: {len(songs)} song(s)")
    console.print(f"[dim]Mode: {'Parallel' if parallel else 'Sequential'}[/dim]\n")

    # Track task IDs and metadata
    tasks = []
    batch_start_time = datetime.now()

    # Initialize client
    callback_url = config.get('callback_url')
    client = SunoClient(api_key, callback_url=callback_url if callback_url else None)

    # Start all generations
    for idx, song_def in enumerate(songs, 1):
        # Extract song parameters
        title = song_def.get('title')
        lyrics_param = song_def.get('lyrics')
        style_param = song_def.get('style')
        output_dir = song_def.get('output')
        model = song_def.get('model') or config.get('default_model', 'V4_5ALL')
        gender = song_def.get('gender') or config.get('default_gender', 'male')
        instrumental = song_def.get('instrumental', False)
        duration = song_def.get('duration')
        cover = song_def.get('cover')
        generate_cover = song_def.get('generate_cover', False)
        artist = song_def.get('artist') or config.get('default_artist', 'Suno AI')
        album = song_def.get('album') or config.get('default_album')
        track = song_def.get('track') or idx

        # Determine output directory
        if not output_dir:
            if output_base:
                # Use base + song number
                output_dir = Path(output_base) / f"song_{idx:02d}"
            elif config.get('default_output_dir'):
                output_dir = Path(config.get('default_output_dir')) / f"song_{idx:02d}"
            else:
                console.print(f"[red]Error: No output directory for song {idx}[/red]")
                console.print("Specify 'output' in YAML or use -o/--output-base")
                sys.exit(1)

        output_path = Path(output_dir)

        # Validate required fields
        if not lyrics_param or not title or not style_param:
            console.print(f"[red]Error: Song {idx} missing required fields (title, lyrics, style)[/red]")
            sys.exit(1)

        # Load lyrics (file, URL, or string)
        lyrics_text = load_content(lyrics_param, f"lyrics for song {idx}")

        # Load style (file, URL, or string)
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
                'index': idx
            })

            console.print(f"  [green]✓[/green] Task ID: {task_id}")

        except SunoAPIError as e:
            console.print(f"  [red]✗ Failed: {e}[/red]")
            continue

        # Delay between songs (if not parallel)
        if not parallel and idx < len(songs) and delay > 0:
            console.print(f"  [dim]Waiting {delay}s before next song...[/dim]")
            time_module.sleep(delay)

    if not tasks:
        console.print("[red]No songs were started successfully[/red]")
        sys.exit(1)

    console.print(f"\n[green]✓[/green] Started {len(tasks)} generation(s)")
    console.print("[dim]Waiting for all songs to complete...[/dim]\n")

    # Wait for all completions and download
    completed = 0
    failed = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for task_info in tasks:
            task_id = task_info['task_id']
            title = task_info['title']
            output_path = task_info['output_path']

            progress_task = progress.add_task(f"Waiting for '{title}'...", total=None)

            try:
                # Wait for completion
                poll_interval = config.get('poll_interval', 10)
                max_wait = config.get('max_wait', 600)

                audio_urls, metadata = client.wait_for_completion(
                    task_id,
                    poll_interval=poll_interval,
                    max_wait=max_wait
                )

                progress.update(progress_task, description=f"Completed '{title}', downloading...")

                # Create output directory
                output_path.mkdir(parents=True, exist_ok=True)

                # Generate cover if requested
                generated_cover_urls = []
                if task_info['generate_cover'] and not task_info['cover']:
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
                cover_for_embedding = task_info['cover']
                if not cover_for_embedding and generated_cover_urls:
                    cover_for_embedding = str(output_path / "cover_1.jpg")

                # Extract tag information
                tag_info = extract_tags_from_metadata(metadata)

                # Download audio files
                for audio_idx, url in enumerate(audio_urls, 1):
                    output_file = output_path / f"track_{audio_idx}.mp3"
                    client.download_audio(url, str(output_file))

                    # Set ID3 tags
                    try:
                        from datetime import datetime
                        current_year = str(datetime.now().year)

                        track_num = task_info['track'] if task_info['track'] is not None else (audio_idx if len(audio_urls) > 1 else None)

                        set_id3_tags(
                            mp3_file=str(output_file),
                            title=tag_info.get('title') or title,
                            artist=task_info['artist'],
                            album=task_info['album'],
                            genre=tag_info.get('genre'),
                            year=current_year,
                            track_number=track_num,
                            cover_url=tag_info.get('cover_url') if not cover_for_embedding else None,
                            cover_file=cover_for_embedding
                        )
                    except TaggingError:
                        pass  # Continue without tags

                # Save metadata
                metadata_file = output_path / "metadata.json"
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)

                completed += 1
                console.print(f"[green]✓[/green] [{completed}/{len(tasks)}] {title} -> {output_path}")

            except SunoAPIError as e:
                failed += 1
                console.print(f"[red]✗[/red] [{completed + failed}/{len(tasks)}] {title}: {e}")
                continue

            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled by user[/yellow]")
                console.print(f"[dim]Completed: {completed}/{len(tasks)}, Failed: {failed}/{len(tasks)}[/dim]")
                sys.exit(130)

    # Summary
    batch_duration = (datetime.now() - batch_start_time).total_seconds()
    console.print(f"\n[bold green]Batch Complete![/bold green]")
    console.print(f"[green]✓[/green] Completed: {completed}/{len(tasks)}")
    if failed > 0:
        console.print(f"[red]✗[/red] Failed: {failed}/{len(tasks)}")
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
