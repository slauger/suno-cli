# Examples

This directory contains example files to get you started with suno-cli.

## Directory Structure

```
examples/
├── lyrics/          # Example lyrics files
├── styles/          # Quick style prompts (.txt)
├── style-guides/    # Detailed style guides (.md)
└── batch/           # Batch generation examples (.yaml)
```

## Quick Start

### Generate a Single Song

```bash
suno generate --prompt examples/lyrics/example.txt \
  -t "Dancing Tonight" \
  -s examples/styles/pop.txt \
  -o ./output
```

### Generate Multiple Songs (Batch)

```bash
suno batch examples/batch/album_example.yaml -o ./my-album
```

## Available Files

### Lyrics (`lyrics/`)

- **example.txt** - Sample song lyrics in verse-chorus structure

### Styles (`styles/`)

Quick, one-line style prompts ready to use:

**Pop & Ballad:**
- `pop.txt` - Upbeat pop style
- `ballad.txt` - Emotional ballad

**Schlager & Party:**
- `schlager.txt` - Classic German Schlager
- `schlager_modern.txt` - Modern Schlager with Discofox beat
- `malle_party.txt` - Mallorca party music (Ballermann)
- `austropop_party.txt` - Austrian party Schlager with Alpine vibes
- `austropop_folk.txt` - Austrian folk-pop, storytelling style

**Metal:**
- `metalcore.txt` - Aggressive metalcore with breakdowns
- `death_metal.txt` - Brutal death metal

### Style Guides (`style-guides/`)

Comprehensive production guides with detailed tips:

- `malle_party.md` - Complete Ballermann/Malle party music guide
- `austropop_folk.md` - Austrian folk-pop guide (STS style)
- `metalcore.md` - Metalcore production and vocal guide

> **Note:** The `.txt` files contain just the style prompt string for direct use with the CLI. The `.md` files are detailed reference guides with production tips, vocal styles, instrumentation details, and more.

### Batch Files (`batch/`)

Example YAML configurations for batch generation:

- `album_example.yaml` - Multi-genre album example
- `schlager_album.yaml` - German Schlager album with cover art
- `remote_example.yaml` - Using HTTP URLs for lyrics and styles
- `batch-simple.yaml` - Minimal batch example
- `batch-variations.yaml` - Different style variations
- `batch-album.yaml` - Full album with metadata
- `config_example.yaml` - Example config file

## Usage Examples

### Single Song with Style File

```bash
suno generate --prompt examples/lyrics/example.txt \
  -t "Tanz mit mir" \
  -s examples/styles/schlager.txt \
  -o ./output \
  --gender male
```

### Single Song with Inline Style

```bash
suno generate -p examples/lyrics/example.txt \
  -t "Summer Vibes" \
  -s "pop, upbeat, 120 BPM" \
  -o ./output
```

### Using URLs for Lyrics and Styles

You can also use HTTP/HTTPS URLs for lyrics and styles:

```bash
suno generate --prompt https://example.com/lyrics.txt \
  -t "Remote Song" \
  -s https://example.com/style.txt \
  -o ./output
```

This works for both single songs and in batch YAML files.

### Using URLs for Batch Files

You can even load the batch YAML file itself from a URL:

```bash
suno batch https://example.com/album.yaml -o ./my-album
```

This allows you to share complete album configurations via URL!

### Batch Generation (Sequential)

```bash
suno batch examples/batch/album_example.yaml -o ./my-album
```

### Batch Generation (Parallel)

```bash
suno batch examples/batch/schlager_album.yaml -o ./schlager --parallel
```

## Writing Your Own Prompts

### Style Prompts

Good style prompts include:

1. **Genre** - Pop, Rock, Schlager, Country, etc.
2. **Mood** - Upbeat, emotional, energetic, intimate
3. **Instrumentation** - Piano, guitar, strings, electronic
4. **Tempo** - Specific BPM or descriptive (slow, mid-tempo, fast)
5. **Vocal style** - Powerful, warm, intimate, duo feeling
6. **Production style** - Modern, vintage, clean, raw
7. **Reference artists** - "similar to [Artist Name]"

Example:
```
Indie folk, acoustic guitar, warm vocals, intimate,
organic instrumentation, harmonies, storytelling, 95 BPM,
similar to Bon Iver
```

### API Character Limits

Be aware of API limits when creating prompts (automatically validated by suno-cli):

- **Style:** Max 1000 chars (V4_5+) or 200 chars (V4)
- **Lyrics:** Max 5000 chars (V4_5+) or 3000 chars (V4)
- **Title:** Max 100 chars (V4_5+) or 80 chars (V4/V4_5ALL)

All our example `.txt` files are under 250 characters and work with all models.
