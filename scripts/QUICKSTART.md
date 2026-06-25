# Quick Start with Sample Data

Get the sentiment tracker up and running with realistic sample data in 3 commands.

## Prerequisites

```bash
# From the project root directory
make setup
make install
```

## Option 1: Load Sample Data (View Only)

Fastest way to see the app working with data:

```bash
# Load 35 sample journal entries
make seed

# Start the UI
make ui
```

That's it! Navigate to `http://localhost:8501` and explore the sample entries.

**Time to first data:** ~5 seconds  
**Entries included:** 35  
**Status:** Ready to view (not analyzing)

## Option 2: Seed Data with Full Processing

To see sentiment analysis, entity extraction, and reflections:

```bash
# Terminal 1: Start the API
make run

# Terminal 2: Start the worker (in a new terminal)
# Ensure you have a worker command - check your Makefile
cd /Volumes/KINGSTON/Programming/portfolio/ai.sentiment-tracker
.venv/bin/python -m app.core.worker

# Terminal 3: Seed data and enqueue for processing
make seed-process

# Terminal 4: Start the UI
make ui
```

The worker will process entries in the background. Watch the UI as entries get analyzed.

**Time to first data:** ~10-30 seconds per entry (depends on your hardware)  
**Entries included:** 35  
**Status:** Processing sentiment analysis, generating reflections

## Option 3: Start Fresh (Complete Reset)

To wipe everything and start over:

```bash
# Reset the database
make reset-confirm

# Seed fresh data
make seed

# Start the app
make ui
```

## What's in the Sample Data?

The sample dataset (`data/sample_entries.json`) contains 35 realistic journal entries from a computer science graduate student during their final year:

- **Dates:** April 15 - May 19, 2026 (1 month)
- **Themes:**
  - Thesis defense anxiety and preparation
  - Blood pressure concerns and health monitoring
  - Job search stress and interview preparation
  - Career transition and offers
  - Therapy sessions and coping strategies
  - Academic breakthroughs and research accomplishments
  - Personal relationships and support systems
  - Emotional ups and downs throughout the journey

**Sentiment spread:**
- 12 entries with positive/excited tone
- 10 entries with anxious/stressed tone
- 8 entries with neutral/reflective tone
- 5 entries with negative/difficult tone

## Quick Reference

| Command | Does What |
|---------|-----------|
| `make seed` | Load 35 sample entries (view only) |
| `make seed-process` | Load 35 entries and enqueue for analysis |
| `make reset-confirm` | Wipe all data |
| `make run` | Start the API |
| `make ui` | Start the Streamlit UI |
| `make worker` | Start the background worker (if available) |
| `make test` | Run tests |

## Troubleshooting

**"entries.db not found"**
→ Run `make seed` first

**"Can't connect to http://localhost:8501"**
→ Make sure you ran `make ui` and wait 5 seconds for it to start

**"Entries show as 'pending' but never process"**
→ The worker isn't running. Check Terminal 2 (worker) is active

**"Want to load different sample data"**
→ `python scripts/seed.py path/to/custom_entries.json`

## Next Steps

Once you're comfortable with the UI:

1. **Explore the data** — Check out sentiment trends, mood reports
2. **Review the API** — Visit `http://localhost:8000/docs`
3. **Add your own entries** — Start journaling!
4. **Customize the UI** — Edit `ui/app.py`
5. **Read the code** — Check out `app/core/pipeline.py` for sentiment analysis

## Files Created

When you run the seed script, these are created/updated:

```
data/
├── journal.db          # SQLite database with entries
├── chroma/             # Vector database (if processing)
└── sample_entries.json # The sample dataset
```

## See Also

- [SEED.md](SEED.md) — Full seeding documentation
- [RESET.md](RESET.md) — How to reset the database
- [../README.md](../README.md) — Full project documentation
