# Installation Guide

## Requirements

- Python 3.8+
- pip
- git

## Install

```bash
# Clone repository
git clone https://github.com/slauger/suno-cli.git
cd suno-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install package
pip install -e .
```

## Setup API Key

Get your API key from [sunoapi.org](https://sunoapi.org).

**Option 1: Config File (Recommended)**
```bash
suno init-config
nano ~/.suno-cli/config.yaml  # Add your API key
```

**Option 2: Environment Variable**
```bash
export SUNO_API_KEY=your-key-here

# Make it permanent
echo 'export SUNO_API_KEY=your-key-here' >> ~/.zshrc
source ~/.zshrc
```

## Verify Installation

```bash
suno --version
suno --help
```

## Platform-Specific

### macOS
```bash
# Install Python (if needed)
brew install python3

# Then follow standard install steps above
```

### Linux
```bash
# Install Python
sudo apt update
sudo apt install python3 python3-pip python3-venv

# Then follow standard install steps above
```

### Windows
```powershell
# Install Python from python.org (check "Add to PATH")

# Then in PowerShell:
python -m venv venv
venv\Scripts\activate
pip install -e .
```

## Troubleshooting

**Command not found:**
```bash
# Make sure venv is activated
source venv/bin/activate

# Reinstall
pip uninstall suno-cli
pip install -e .
```

**Old pip version:**
```bash
pip install --upgrade pip
pip install -e .
```

## Next Steps

See [Usage Guide](docs/USAGE.md) for examples.
