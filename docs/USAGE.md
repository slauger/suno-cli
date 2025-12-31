# Usage Guide

## Generate a Song

### Basic Usage

```bash
suno generate --prompt <lyrics> -t "Title" -s "style" -o <output-dir>
```

**Parameters:**
- `-p, --prompt`: Lyrics/prompt - file path, URL, or inline text (required)
- `-t, --title`: Song title (required)
- `-s, --style`: Music style/genre (file path, URL, or string, required)
- `-o, --output`: Output directory (required)

### Examples

**From files:**
```bash
suno generate --prompt lyrics.txt -t "Summer Dreams" -s style.txt -o ./output
```

**From URLs:**
```bash
suno generate --prompt https://example.com/lyrics.txt \
  -t "Remote Song" \
  -s https://example.com/style.txt \
  -o ./output
```

**Inline prompt:**
```bash
suno generate --prompt "Verse 1: Walking down the street..." -t "My Song" -s "pop, upbeat" -o ./output
```

**Mix of file and URL:**
```bash
suno generate -p lyrics.txt \
  -t "My Song" \
  -s https://raw.githubusercontent.com/user/repo/main/style.txt \
  -o ./output
```

**With options:**
```bash
suno generate -p lyrics.txt -t "Rock Song" -s "rock, energetic, 140 BPM" -o ./output \
  --model V5 \
  --gender female \
  --artist "My Band" \
  --album "First Album" \
  --track 3
```

## Options

### AI Model
```bash
--model V5           # Latest model, superior musical expression
--model V4_5ALL      # Most versatile (default)
--model V4_5PLUS     # Richer sound
```

### Vocals
```bash
--gender male        # Male vocals (default)
--gender female      # Female vocals
--instrumental       # No vocals
```

### ID3 Tags
```bash
--artist "Artist Name"
--album "Album Name"
--track 5                    # Track number
--cover cover.jpg            # Custom cover image
--generate-cover             # AI-generate cover (costs credits)
--no-tags                    # Skip ID3 tags
```

## Check Status

```bash
suno status <task-id>
```

Shows current generation status and details.

## Download Song

```bash
suno download <task-id> -o <output-dir>
```

Download a previously generated song by its task ID.

## Style Prompts

Good style prompts include:
- Genre (pop, rock, jazz, etc.)
- Mood (upbeat, emotional, calm)
- Tempo (120 BPM, fast, slow)
- Instrumentation (piano-driven, guitar, electronic)

**Examples:**
```
"pop, upbeat, catchy, 120 BPM, radio-friendly"
"rock, energetic, guitar-driven, powerful drums, 140 BPM"
"ballad, emotional, piano and vocals, slow, 80 BPM"
"electronic, dance, synth-heavy, EDM, 128 BPM"
"jazz, smooth, sophisticated, piano and saxophone, 110 BPM"
```

## Output Structure

After generation:
```
output/
├── track_1.mp3        # First variant
├── track_2.mp3        # Second variant
└── metadata.json      # API metadata
```

Each MP3 includes:
- ID3 tags (title, artist, album, genre, year, track number)
- Embedded cover art
