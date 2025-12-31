# Batch Generation Guide

Generate multiple songs at once from a YAML file.

## Basic Usage

```bash
# From local file
suno batch songs.yaml -o ./output

# From URL
suno batch https://example.com/album.yaml -o ./output
```

## YAML Format

```yaml
songs:
  - title: "Song 1"
    lyrics: path/to/lyrics1.txt
    style: "pop, upbeat"

  - title: "Song 2"
    lyrics: |
      Verse 1:
      Inline lyrics work too
      No separate file needed
    style: path/to/style.txt
```

## Required Fields

Each song must have:
- `title` - Song title
- `lyrics` - File path or inline text
- `style` - File path or inline text

## Optional Fields

```yaml
- title: "My Song"
  lyrics: lyrics.txt
  style: "pop"

  # Optional fields
  output: ./custom-dir     # Custom output directory
  model: V5                # AI model
  gender: female           # Vocal gender
  instrumental: true       # Instrumental only

  # ID3 Tags
  artist: "My Band"
  album: "First Album"
  track: 3
  cover: cover.jpg         # Custom cover
  generate_cover: true     # Generate AI cover
```

## Modes

### Sequential (Default)

Generates songs one after another:
```bash
suno batch songs.yaml -o ./album
```

### Parallel

Starts all generations at once:
```bash
suno batch songs.yaml -o ./album --parallel
```

### Delayed Sequential

Wait N seconds between each song:
```bash
suno batch songs.yaml -o ./album --delay 10
```

## Use Cases

### 1. Complete Album

```yaml
# album.yaml
songs:
  - title: "Opening Track"
    lyrics: track1.txt
    style: "pop, energetic"
    track: 1
    album: "My Album"
    artist: "My Band"
    cover: album-cover.jpg

  - title: "Second Song"
    lyrics: track2.txt
    style: "pop, mid-tempo"
    track: 2
    album: "My Album"
    artist: "My Band"
    cover: album-cover.jpg

  - title: "Ballad"
    lyrics: track3.txt
    style: "ballad, emotional"
    track: 3
    album: "My Album"
    artist: "My Band"
    gender: female
    cover: album-cover.jpg
```

```bash
suno batch album.yaml -o ./my-album
```

### 2. Style Variations

Generate the same song in different styles:

```yaml
# variations.yaml
songs:
  - title: "Dreams - Pop Version"
    lyrics: dreams.txt
    style: "pop, upbeat, 120 BPM"

  - title: "Dreams - Rock Version"
    lyrics: dreams.txt
    style: "rock, energetic, 140 BPM"

  - title: "Dreams - Acoustic"
    lyrics: dreams.txt
    style: "acoustic, intimate, folk"
    gender: female

  - title: "Dreams - Electronic"
    lyrics: dreams.txt
    style: "electronic, EDM, 128 BPM"

  - title: "Dreams - Jazz"
    lyrics: dreams.txt
    style: "jazz, smooth, sophisticated"

  - title: "Dreams - Instrumental"
    lyrics: dreams.txt
    style: "cinematic, orchestral"
    instrumental: true
```

```bash
suno batch variations.yaml -o ./variations --parallel
```

### 3. Simple Batch

```yaml
# songs.yaml
songs:
  - title: "First Song"
    lyrics: "Verse 1: Walking down the street..."
    style: "pop, upbeat"

  - title: "Second Song"
    lyrics: "Verse 1: Stars are shining bright..."
    style: "dance pop, energetic"
    gender: female
```

```bash
suno batch songs.yaml -o ./songs
```

## Output Structure

```
output/
├── song_01/
│   ├── track_1.mp3
│   ├── track_2.mp3
│   └── metadata.json
├── song_02/
│   ├── track_1.mp3
│   ├── track_2.mp3
│   └── metadata.json
└── song_03/
    ├── track_1.mp3
    ├── track_2.mp3
    └── metadata.json
```

Or with custom output directories:
```
output/
├── track1/
├── track2/
└── track3/
```

## Examples

See `examples/` directory:
- `batch-simple.yaml` - Basic batch
- `batch-album.yaml` - Full album with 5 tracks
- `batch-variations.yaml` - Same song, 6 different styles

## Tips

1. **Parallel vs Sequential**: Use `--parallel` for faster completion, sequential for API rate limiting
2. **Album Production**: Use same `album`, `artist`, and `cover` for all tracks
3. **Variations**: Use same `lyrics` with different `style` for comparisons
4. **Output**: Specify custom `output` per song for better organization
