# suno-cli

> CLI tool for generating music with Suno AI

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/slauger/suno-cli.svg)](LICENSE)

## Features

- 🎵 Generate songs from lyrics + style prompts
- 🎼 Batch generation (perfect for albums)
- 🏷️ Automatic ID3 tags with cover art
- 📝 Config file for defaults
- ⚡ Multiple AI models (V5, V4.5-All, etc.)

## Quick Start

```bash
# Install
git clone https://github.com/slauger/suno-cli.git
cd suno-cli
python3 -m pip install -e .

# Setup
suno init-config
# Edit ~/.suno-cli/config.yaml and add your API key from https://sunoapi.org

# Generate a song
suno generate -p lyrics.txt -t "My Song" -s "pop, upbeat" -o ./output

# Generate multiple songs
suno batch songs.yaml -o ./album
```

## Commands

```bash
suno generate -p <lyrics> -t "Title" -s "style" -o <output>  # Single song
suno batch <yaml-file> -o <output>                            # Multiple songs
suno status <task-id>                                         # Check status
suno download <task-id> -o <output>                           # Download song
suno init-config                                              # Create config
```

## Documentation

- [Installation Guide](INSTALL.md)
- [Usage Examples](docs/USAGE.md)
- [Configuration](docs/CONFIG.md)
- [Batch Generation](docs/BATCH.md)

## Examples

**Single Song:**
```bash
suno generate -p lyrics.txt -t "Summer Vibes" -s "pop, upbeat, 120 BPM" -o ./output
```

**Album (Batch):**
```yaml
# songs.yaml
songs:
  - title: "Track 1"
    lyrics: track1.txt
    style: "pop, energetic"
  - title: "Track 2"
    lyrics: track2.txt
    style: "ballad, emotional"
```

```bash
suno batch songs.yaml -o ./my-album --parallel
```

## License

MIT - See [LICENSE](LICENSE) for details

## Links

- [Suno API](https://sunoapi.org)
- [Issues](https://github.com/slauger/suno-cli/issues)
