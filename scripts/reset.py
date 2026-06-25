#!/usr/bin/env python3
"""Reset script to wipe all user data from the sentiment tracker application."""

import os
import shutil
import sys
from pathlib import Path

def reset_app():
    """Remove all user-generated data from the application."""
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"

    # Define what needs to be cleaned
    items_to_remove = [
        data_dir / "journal.db",
        data_dir / "chroma",
    ]

    print("🔄 Sentiment Tracker - Reset Application Data")
    print("=" * 50)

    # Check what exists
    existing_items = [item for item in items_to_remove if item.exists()]

    if not existing_items:
        print("✅  No user data found. Application is already clean.")
        return 0

    print("\n📋 Items to be removed:")
    for item in existing_items:
        size_info = ""
        if item.is_dir():
            size_info = f" ({sum(f.stat().st_size for f in item.rglob('*') if f.is_file())} bytes)"
        else:
            size_info = f" ({item.stat().st_size} bytes)"
        print(f"   - {item.relative_to(project_root)}{size_info}")

    # Confirm deletion
    print("\n⚠️  This will permanently delete all user data (journals, embeddings, etc).")
    response = input("Are you sure you want to continue? (yes/no): ").strip().lower()

    if response != "yes":
        print("❌  Reset cancelled.")
        return 1

    # Remove items
    print("\n🗑️  Removing data...")
    try:
        for item in existing_items:
            if item.is_dir():
                shutil.rmtree(item)
                print(f"   ✓ Removed directory: {item.relative_to(project_root)}")
            else:
                item.unlink()
                print(f"   ✓ Removed file: {item.relative_to(project_root)}")
    except Exception as e:
        print(f"\n❌  Error during reset: {e}")
        return 1

    # Ensure data directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    print("\n✅  Reset complete! All user data has been cleared.")
    print("   Start the app to initialize a fresh database.")
    return 0

if __name__ == "__main__":
    sys.exit(reset_app())
