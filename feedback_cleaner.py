"""
feedback_cleaner.py

Recursively finds all 'feedback.json' files and removes the keys 'llm_prompt' and 'llm_response' from all nested locations.

Usage:
    python feedback_cleaner.py <root_directory>
"""
import os
import sys
import json
from typing import Any, Dict, List

FEEDBACK_FILENAME = "feedback.json"
REMOVE_KEYS = {"llm_prompt", "llm_response"}

def clean_feedback_file(filepath: str) -> None:
    """Remove specified keys from all repair entries in a feedback.json file."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    changed = False
    if isinstance(data, list):
        for entry in data:
            repairs = entry.get("repairs")
            if isinstance(repairs, list):
                for repair in repairs:
                    for key in REMOVE_KEYS:
                        if key in repair:
                            del repair[key]
                            changed = True
    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"Cleaned: {filepath}")
    else:
        print(f"No changes needed: {filepath}")

def find_feedback_files(root_dir: str) -> List[str]:
    """Recursively find all feedback.json files under root_dir."""
    feedback_files: List[str] = []
    for dirpath, _, filenames in os.walk(root_dir):
        if FEEDBACK_FILENAME in filenames:
            feedback_files.append(os.path.join(dirpath, FEEDBACK_FILENAME))
    return feedback_files

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python feedback_cleaner.py <root_directory>")
        sys.exit(1)
    root_dir = sys.argv[1]
    feedback_files = find_feedback_files(root_dir)
    if not feedback_files:
        print("No feedback.json files found.")
        return
    for filepath in feedback_files:
        clean_feedback_file(filepath)

if __name__ == "__main__":
    main()
