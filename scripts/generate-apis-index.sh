#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX_DIR="$REPO_ROOT/apis-index"
SOURCE_DIR="$REPO_ROOT/apis/openapi"

# Clean any existing index
rm -rf "$INDEX_DIR"

# Create bucket directories: a-z, 0-9, ~rest
for letter in {a..z}; do
    mkdir -p "$INDEX_DIR/$letter"
done
for digit in {0..9}; do
    mkdir -p "$INDEX_DIR/$digit"
done
mkdir -p "$INDEX_DIR/~rest"

# Create symlinks
for api_dir in "$SOURCE_DIR"/*/; do
    api_name="$(basename "$api_dir")"
    first_char="${api_name:0:1}"
    first_char_lower="$(echo "$first_char" | tr '[:upper:]' '[:lower:]')"

    if [[ "$first_char_lower" =~ ^[a-z]$ ]]; then
        bucket="$first_char_lower"
    elif [[ "$first_char_lower" =~ ^[0-9]$ ]]; then
        bucket="$first_char_lower"
    else
        bucket="~rest"
    fi

    ln -s "../../apis/openapi/$api_name" "$INDEX_DIR/$bucket/$api_name"
done

# Summary
total_symlinks=$(find "$INDEX_DIR" -type l | wc -l)
total_source=$(find "$SOURCE_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
echo "Created $total_symlinks symlinks for $total_source API directories"

if [ "$total_symlinks" -ne "$total_source" ]; then
    echo "WARNING: symlink count ($total_symlinks) does not match source count ($total_source)"
    exit 1
fi
