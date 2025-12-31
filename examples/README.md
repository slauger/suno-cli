# Examples

This directory contains example lyrics and style prompts to get you started with suno-cli.

## Files

- **lyrics_example.txt** - Sample song lyrics in verse-chorus structure
- **style_pop.txt** - Upbeat pop style prompt
- **style_schlager.txt** - German Schlager style (Fernando Express)
- **style_ballad.txt** - Emotional ballad style

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
