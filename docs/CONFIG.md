# Configuration Guide

## Create Config File

```bash
suno init-config
```

Creates `~/.suno-cli/config.yaml` with default settings.

## Config File Location

- Default: `~/.suno-cli/config.yaml`
- Custom: `suno --config /path/to/config.yaml <command>`

## Config Format

```yaml
# AI Model (V5, V4_5PLUS, V4_5ALL, V4_5, V4)
default_model: V4_5ALL

# Vocal gender (male, female)
default_gender: male

# Default output directory
default_output_dir: ~/Music/suno-generated

# ID3 Tags
default_artist: Suno AI
default_album: My Album  # Optional

# API Settings
api_key: ${SUNO_API_KEY}  # Use env var
callback_url: https://example.com/callback  # Optional

# Polling
poll_interval: 10  # Seconds between status checks
max_wait: 600      # Maximum wait time in seconds
```

## Environment Variables

Config files support variable substitution:

```yaml
api_key: ${SUNO_API_KEY}
default_output_dir: ${HOME}/Music/suno
```

## Priority Order

Settings are applied in this order (highest first):

1. **Command-line arguments**
   ```bash
   suno generate --model V5 --output ./custom
   ```

2. **Config file**
   ```yaml
   default_model: V4_5ALL
   default_output_dir: ~/Music
   ```

3. **Environment variables**
   ```bash
   export SUNO_API_KEY=abc123
   ```

## API Key Setup

### Option 1: Config File (Recommended)

```bash
suno init-config
# Edit ~/.suno-cli/config.yaml
```

```yaml
api_key: ${SUNO_API_KEY}  # Reference env var
# or
api_key: your-actual-key   # Direct (less secure)
```

### Option 2: Environment Variable

```bash
export SUNO_API_KEY=your-key-here

# Persist in shell profile
echo 'export SUNO_API_KEY=your-key-here' >> ~/.zshrc
source ~/.zshrc
```

### Option 3: Command Line

```bash
suno generate --api-key your-key-here ...
```

## Example Configs

### Minimal

```yaml
api_key: ${SUNO_API_KEY}
default_output_dir: ~/Music/suno
```

### Album Production

```yaml
default_model: V4_5ALL
default_gender: male
default_output_dir: ~/Music/albums
default_artist: My Band
default_album: Greatest Hits
api_key: ${SUNO_API_KEY}
poll_interval: 10
max_wait: 600
```

### Quick Experiments

```yaml
default_model: V5
default_output_dir: ~/Music/experiments
api_key: ${SUNO_API_KEY}
poll_interval: 5
max_wait: 300
```

## Get API Key

1. Visit [sunoapi.org](https://sunoapi.org)
2. Sign up and get your API key
3. Add to config or environment variable
