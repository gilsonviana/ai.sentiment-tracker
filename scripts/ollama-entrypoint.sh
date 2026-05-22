#!/bin/sh
set -e

ollama serve &
OLLAMA_PID=$!

echo "[ollama] Waiting for server to be ready..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
  sleep 2
done
echo "[ollama] Server ready."

if ! ollama list | grep -q "^mistral"; then
  echo "[ollama] Pulling mistral (first run — this will take a few minutes)..."
  ollama pull mistral
  echo "[ollama] mistral pulled."
else
  echo "[ollama] mistral already present, skipping pull."
fi

wait "$OLLAMA_PID"
