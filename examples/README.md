# Examples

This directory contains example lyrics and style prompts to get you started with suno-cli.

## Files

### Lyrics
- **lyrics_example.txt** - Sample song lyrics in verse-chorus structure

### Style Prompts

**Quick Style Prompts (.txt)** - Short, one-line prompts for quick generation:

**Pop & Ballad:**
- **style_pop.txt** - Upbeat pop style prompt
- **style_ballad.txt** - Emotional ballad style

**Schlager & Party:**
- **style_schlager.txt** - Classic German Schlager style
- **style_schlager_modern.txt** - Modern German Schlager with Discofox beat
- **style_malle_party.txt** - Mallorca party music (Ballermann style)
- **style_austropop_party.txt** - Austrian party Schlager with Alpine vibes
- **style_austropop_folk.txt** - Austrian folk-pop, storytelling style

**Metal:**
- **style_metalcore.txt** - Aggressive metalcore with breakdowns
- **style_death_metal.txt** - Brutal death metal

---

**Detailed Style Guides (.md)** - Comprehensive guides with production tips, references, and examples:

- **style_malle_party.md** - Complete Ballermann/Malle party music guide
- **style_austropop_folk.md** - Austrian folk-pop guide (STS style)
- **style_metalcore.md** - Metalcore production and vocal guide

> **Note:** The .txt files contain just the style prompt string for quick use. The .md files are detailed reference guides that include the same prompt plus production tips, vocal styles, instrumentation details, and more.

## Quick Start

Generate a pop song:

```bash
suno generate lyrics_example.txt -t "Dancing Tonight" -s style_pop.txt -o ../output_pop
```

Generate a schlager song:

```bash
suno generate lyrics_example.txt -t "Tanz mit mir" -s style_schlager.txt -o ../output_schlager --gender male
```

Generate a ballad:

```bash
suno generate lyrics_example.txt -t "When You're Gone" -s style_ballad.txt -o ../output_ballad --gender female
```

## Tips for Writing Style Prompts

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

## API Character Limits

Be aware of API limits when creating prompts (automatically validated by suno-cli):

- **Style:** Max 1000 chars (V4_5+) or 200 chars (V4)
- **Lyrics:** Max 5000 chars (V4_5+) or 3000 chars (V4)
- **Title:** Max 100 chars (V4_5+) or 80 chars (V4/V4_5ALL)

All our example `.txt` files are under 250 characters and work with all models.
