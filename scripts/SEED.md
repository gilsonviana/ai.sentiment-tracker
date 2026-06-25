# Seed Script - Populate Database with Sample Data

This script loads journal entries from a JSON file and inserts them into your SQLite database.

## Features

- 🌱 **Batch seeding** — Load up to thousands of entries at once
- 📋 **Auto-migrations** — Creates tables if they don't exist
- ⚙️ **Optional processing** — Enqueue entries for sentiment analysis
- ✅ **Validation** — Skips invalid entries with clear feedback
- 📊 **Progress tracking** — Shows insertion progress and summary

## Usage

### Load entries without processing (view only)

```bash
make seed
# or directly:
python scripts/seed.py
```

This inserts entries with status `processed`, so they're immediately visible in the UI without waiting for analysis.

### Load entries with processing

```bash
make seed-process
# or directly:
python scripts/seed.py --process
```

This marks entries as `pending` and enqueues them in the processing queue. The worker will analyze them for sentiment, entities, and generate reflections.

### Load from custom JSON file

```bash
python scripts/seed.py path/to/custom_entries.json
python scripts/seed.py path/to/custom_entries.json --process
```

## JSON Format

The expected JSON structure is:

```json
{
  "entries": [
    {
      "content": "Your journal entry text here",
      "entry_date": "2026-04-15"
    },
    {
      "content": "Another entry",
      "entry_date": "2026-04-16"
    }
  ]
}
```

### Field Requirements

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `content` | string | ✅ Yes | 1–5000 characters |
| `entry_date` | date string (ISO 8601) | ❌ Optional | Format: `YYYY-MM-DD`. Defaults to today if omitted. |

### Example

```json
{
  "entries": [
    {
      "content": "Started the day feeling anxious about my thesis defense.",
      "entry_date": "2026-04-15"
    },
    {
      "content": "Had a productive coding session today.",
      "entry_date": "2026-04-16"
    },
    {
      "content": "Today was really rough. Couldn't focus on anything.",
      "entry_date": "2026-04-17"
    }
  ]
}
```

## What Gets Created

When you run the seed script:

1. **Database file** — `data/journal.db` (created if it doesn't exist)
2. **Tables** — `entries`, `analysis`, `queue`, `reflections`
3. **Entries** — All valid entries are inserted with a unique UUID
4. **Queue items** (optional) — If using `--process`, adds entries to the processing queue

## Processing Pipeline

### Without `--process`

```
Entries inserted → Status: processed → Ready to view immediately
```

Use this when you want to quickly populate the database for testing UI without waiting for analysis.

### With `--process`

```
Entries inserted → Status: pending → Enqueued in queue → Worker processes → Sentiment/entities/reflections
```

Use this when you want the full sentiment analysis pipeline to run.

## Output Example

```
🌱 Sentiment Tracker - Database Seeder
==================================================
📂 Loading entries from sample_entries.json...
✅  Loaded 35 entries

🔗 Connecting to database at data/journal.db...
📋 Running migrations...

🌱 Seeding database with 35 entries...
   [1/35] Entry loaded
   [2/35] Entry loaded
   [3/35] Entry loaded
   ...
   [35/35] Entry loaded

==================================================
✅  Seeding complete!
   📊 Inserted: 35 entries
   ⚙️  Status: ready to view (not processing)
==================================================

💡 Tip: Use '--process' or '-p' flag to enqueue entries for
   sentiment analysis and reflection generation.

   $ python scripts/seed.py --process
```

## Tips

### Quick workflow

```bash
# 1. Reset database
make reset-confirm

# 2. Seed with sample data
make seed

# 3. Start the app
make ui

# 4. View your data in the UI
```

### Full workflow with processing

```bash
# 1. Reset
make reset-confirm

# 2. Seed and enqueue for analysis
make seed-process

# 3. Start the API and worker in separate terminals
# Terminal 1:
make run

# Terminal 2:
make worker

# 4. Start the UI
make ui

# 5. Check UI as entries get processed
```

### Combining datasets

You can seed multiple times with different JSON files:

```bash
python scripts/seed.py data/sample_entries.json
python scripts/seed.py data/other_entries.json
python scripts/seed.py data/more_entries.json
```

All entries are appended; existing entries aren't affected.

### Validating your JSON

```bash
python -m json.tool data/sample_entries.json
```

## Troubleshooting

### "No entries found in JSON file"
- Check that your JSON has an `"entries"` array at the top level
- Verify the file isn't empty or malformed

### "Invalid JSON"
- Use `python -m json.tool file.json` to identify syntax errors
- Ensure all strings are properly quoted

### "Database error"
- Make sure `data/` directory exists and is writable
- Check that no other process is holding the database file open

### Some entries were skipped
- Check the output for skipped entries and their reasons
- Empty content, invalid dates, or other issues will be shown

## See Also

- [Reset script](RESET.md) — To clear the database
- [Sample data](../data/sample_entries.json) — The default dataset
