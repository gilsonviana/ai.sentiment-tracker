# Reset Script - Application Data Cleanup

This directory contains scripts to completely reset the application by removing all user-generated data.

## What Gets Deleted

When you run the reset script, the following are permanently removed:

- `data/journal.db` — SQLite database containing all user journal entries
- `data/chroma/` — ChromaDB vector database containing embeddings

**Note:** Configuration files (`.env`, `.gitignore`, etc.) are preserved.

## Usage

### Option 1: Using Make (Recommended)

```bash
# See what would be deleted
make reset

# Actually perform the reset
make reset-confirm
```

### Option 2: Using Python Script

```bash
python scripts/reset.py
```

Or directly:

```bash
./scripts/reset.py
```

### Option 3: Using Shell Script

```bash
./scripts/reset.sh
```

Or directly:

```bash
bash scripts/reset.sh
```

## Confirmation

Both scripts will:
1. Show you what data will be deleted
2. Prompt you to confirm by typing `yes`
3. Only proceed if you confirm

## After Reset

Once reset is complete:
1. All application data is cleared
2. The `data/` directory structure is preserved
3. Run `make run` or `make ui` to start fresh with an empty database
4. The app will automatically recreate necessary tables and directories on first run

## Safety

- **Interactive confirmation** — You must explicitly confirm the reset
- **No automatic deletion** — The scripts require user input before proceeding
- **Reversible** — Only happens if you confirm; you can cancel anytime
