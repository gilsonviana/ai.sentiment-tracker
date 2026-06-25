# AI Journal

Sentiment-aware personal journal with a fully local, zero-cost ML pipeline.

## Requirements

| Requirement | Version |
|---|---|
| Python | 3.12.x |
| pip | 24+ |
| Ollama | latest |
| OS | macOS, Linux, Windows (WSL2) |

> **Why Python 3.12?** Several ML packages (`pydantic-core`, `thinc`)
> ship pre-built wheels for 3.12. Python 3.13 broke binary ABI compatibility
> for many of these libraries. Until the ecosystem catches up, 3.12 is the
> stable target.

---

## 1. Install Python 3.12

Check your version first:

```bash
python3 --version   # must show 3.12.x
```

If you have a different version, use `pyenv` to install 3.12 alongside it
without affecting your system Python:

```bash
brew install pyenv
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

pyenv install 3.12
# The .python-version file in this repo tells pyenv to use 3.12 automatically
```

---

## 2. Install Ollama

Ollama runs the local LLM (`mistral:7b`) that generates weekly journal
reflections. It must be installed and running before you start the app.

```bash
# macOS — install via Homebrew
brew install ollama

# Or download the native app from https://ollama.com
```

After installing, pull the model and start the server:

```bash
# Download the model weights (~4.1 GB, one-time)
ollama pull mistral

# Start the Ollama server (must be running when the app is running)
ollama serve
```

Ollama runs at `http://localhost:11434`. Your app calls it from Python —
you never interact with it directly after setup.

> **RAM requirement:** mistral:7b needs ~8 GB of available RAM.
> On Apple Silicon it runs on the Neural Engine and is fast (~30–40 tok/s).
> On Intel Mac or Linux it runs on CPU — functional but slower.

---

## 3. Set up the project

```bash
# Clone the repo
git clone https://github.com/gilsonviana/ai.sentiment-tracker.git
cd ai-journal

# Create .venv with Python 3.12, copy .env, create data/
make setup

# Install all dependencies
# Uses requirements.lock if present (reproducible)
# Falls back to requirements.txt if not
make install
```

---

## 4. Run

```bash
# In one terminal — keep this running
ollama serve

# In another terminal
make run
# → http://localhost:8000/docs
```

---

## 5. Streamlit UI

A lightweight testing harness for exploring the full API before building the production React frontend.

```bash
# API must be running first (in a separate terminal)
# Launch the UI
make ui         # Terminal 2 → http://localhost:8501
```
---

## Stack

| Layer | Tool |
|---|---|
| API | FastAPI + uvicorn |
| Validation | Pydantic v2 |
| Raw storage | SQLite (aiosqlite) |
| Sentiment | VADER + RoBERTa (cardiffnlp) |
| Embeddings | all-MiniLM-L6-v2 |
| Vector store | Chroma (local persistent) |
| LLM reflection | Ollama (mistral:7b) |
| Frontend | Streamlit |

---

## API

- `POST /entries` — submit a journal entry (202, async processing)
- `GET /entries` — list all entries
- `GET /entries/{id}` — poll processing status
- `GET /entries/{id}/analysis` — fetch sentiment scores and entities (once processed)
- `GET /health` — liveness check
- `GET /docs` — interactive OpenAPI UI

---

## Testing

```bash
make test
```

---

## Resetting Application Data

To completely wipe all user-generated data (journal entries, embeddings, database), use the reset script:

```bash
# Preview what will be deleted
make reset

# Actually perform the reset (requires confirmation)
make reset-confirm
```

Or run directly:

```bash
./scripts/reset.py    # Python version (recommended)
./scripts/reset.sh    # Shell script version
```

**What gets deleted:**
- `data/journal.db` — All user journal entries
- `data/chroma/` — All vector embeddings

**What's preserved:**
- Configuration files (`.env`, source code, etc.)
- Project structure

After reset, the app will recreate a fresh database on next run.

See [scripts/RESET.md](scripts/RESET.md) for more details.
