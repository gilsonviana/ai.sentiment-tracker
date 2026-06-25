#!/bin/bash
# Reset script to wipe all user data from the sentiment tracker application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$PROJECT_ROOT/data"

echo "🔄 Sentiment Tracker - Reset Application Data"
echo "=================================================="

# Check if data exists
if [ ! -d "$DATA_DIR" ] || ([ ! -f "$DATA_DIR/journal.db" ] && [ ! -d "$DATA_DIR/chroma" ]); then
    echo "✅  No user data found. Application is already clean."
    exit 0
fi

echo ""
echo "📋 Items to be removed:"

if [ -f "$DATA_DIR/journal.db" ]; then
    size=$(stat -f%z "$DATA_DIR/journal.db" 2>/dev/null || stat -c%s "$DATA_DIR/journal.db" 2>/dev/null || echo "?")
    echo "   - data/journal.db ($size bytes)"
fi

if [ -d "$DATA_DIR/chroma" ]; then
    echo "   - data/chroma/ (vector database)"
fi

echo ""
echo "⚠️  This will permanently delete all user data (journals, embeddings, etc)."
read -p "Are you sure you want to continue? (yes/no): " response

if [ "$response" != "yes" ]; then
    echo "❌  Reset cancelled."
    exit 1
fi

echo ""
echo "🗑️  Removing data..."

# Remove database file
if [ -f "$DATA_DIR/journal.db" ]; then
    rm -f "$DATA_DIR/journal.db"
    echo "   ✓ Removed file: data/journal.db"
fi

# Remove chroma directory
if [ -d "$DATA_DIR/chroma" ]; then
    rm -rf "$DATA_DIR/chroma"
    echo "   ✓ Removed directory: data/chroma"
fi

# Ensure data directory exists
mkdir -p "$DATA_DIR"

echo ""
echo "✅  Reset complete! All user data has been cleared."
echo "   Start the app to initialize a fresh database."
