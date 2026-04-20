#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX_DIR="$REPO_ROOT/apis-index"
SOURCE_DIR="$REPO_ROOT/apis/openapi"

# Clean any existing index
rm -rf "$INDEX_DIR"

# Create bucket directories: A-Z, 0-9, ~rest
for letter in {A..Z}; do
    mkdir -p "$INDEX_DIR/$letter"
done
for digit in {0..9}; do
    mkdir -p "$INDEX_DIR/$digit"
done
mkdir -p "$INDEX_DIR/~rest"

# Collect APIs into buckets
declare -A BUCKETS
total=0

for api_dir in "$SOURCE_DIR"/*/; do
    api_name="$(basename "$api_dir")"
    first_char="${api_name:0:1}"
    first_char_upper="$(echo "$first_char" | tr '[:lower:]' '[:upper:]')"

    if [[ "$first_char_upper" =~ ^[A-Z]$ ]]; then
        bucket="$first_char_upper"
    elif [[ "$first_char" =~ ^[0-9]$ ]]; then
        bucket="$first_char"
    else
        bucket="~rest"
    fi

    BUCKETS[$bucket]+="- [$api_name](../../apis/openapi/$api_name)"$'\n'
    total=$((total + 1))
done

# Generate README.md for each bucket
total_links=0
for bucket_dir in "$INDEX_DIR"/*/; do
    bucket="$(basename "$bucket_dir")"
    readme="$bucket_dir/README.md"

    if [[ -n "${BUCKETS[$bucket]:-}" ]]; then
        count=$(echo -n "${BUCKETS[$bucket]}" | grep -c '^')
        total_links=$((total_links + count))

        if [[ "$bucket" == "~rest" ]]; then
            description="$count APIs starting with non-alphanumeric characters."
        else
            description="$count APIs starting with \`$bucket\`."
        fi

        cat > "$readme" <<HEREDOC
# APIs: $bucket

$description

${BUCKETS[$bucket]}
HEREDOC
    else
        cat > "$readme" <<HEREDOC
# APIs: $bucket

No APIs currently start with \`$bucket\`.
HEREDOC
    fi
done

total_source=$(find "$SOURCE_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
echo "Created $total_links links across $(ls -d "$INDEX_DIR"/*/ | wc -l) buckets for $total_source API directories"

if [ "$total_links" -ne "$total_source" ]; then
    echo "WARNING: link count ($total_links) does not match source count ($total_source)"
    exit 1
fi
