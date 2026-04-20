#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX_DIR="$REPO_ROOT/index/apis/openapi"
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

    # Collect sub-API links
    sub_links=""
    sub_count=0
    for sub_dir in "$api_dir"/*/; do
        [ -d "$sub_dir" ] || continue
        sub_name="$(basename "$sub_dir")"
        if [[ -n "$sub_links" ]]; then
            sub_links+=" · "
        fi
        sub_links+="[$sub_name](../../../../apis/openapi/$api_name/$sub_name)"
        sub_count=$((sub_count + 1))
    done

    if [[ "$sub_count" -gt 5 ]]; then
        apis_cell="[$sub_count APIs](../../../../apis/openapi/$api_name)"
    else
        apis_cell="$sub_links"
    fi

    BUCKETS[$bucket]+="| [$api_name](../../../../apis/openapi/$api_name) | $apis_cell |"$'\n'
    total=$((total + 1))
done

# Build ordered list of all buckets
ALL_BUCKETS=()
for digit in {0..9}; do ALL_BUCKETS+=("$digit"); done
for letter in {A..Z}; do ALL_BUCKETS+=("$letter"); done
ALL_BUCKETS+=("~rest")

# Build navigation bar
build_nav() {
    local current="$1"
    local nav=""
    for b in "${ALL_BUCKETS[@]}"; do
        if [[ -n "$nav" ]]; then
            nav+=" · "
        fi
        if [[ "$b" == "$current" ]]; then
            nav+="**$b**"
        else
            nav+="[$b](../$b)"
        fi
    done
    echo "$nav"
}

# Generate README.md for each bucket
total_links=0
for bucket_dir in "$INDEX_DIR"/*/; do
    bucket="$(basename "$bucket_dir")"
    readme="$bucket_dir/README.md"
    nav="$(build_nav "$bucket")"

    if [[ -n "${BUCKETS[$bucket]:-}" ]]; then
        count=$(echo -n "${BUCKETS[$bucket]}" | grep -c '^')
        total_links=$((total_links + count))

        cat > "$readme" <<HEREDOC
# APIs — $bucket

Browsing $count APIs starting with **$bucket**.

$nav

| Vendor | APIs |
|--------|------|
${BUCKETS[$bucket]}
HEREDOC
    else
        cat > "$readme" <<HEREDOC
# APIs — $bucket

No APIs currently start with **$bucket**.

$nav
HEREDOC
    fi
done

total_source=$(find "$SOURCE_DIR" -maxdepth 1 -mindepth 1 -type d | wc -l)
echo "Created $total_links links across $(ls -d "$INDEX_DIR"/*/ | wc -l) buckets for $total_source API directories"

if [ "$total_links" -ne "$total_source" ]; then
    echo "WARNING: link count ($total_links) does not match source count ($total_source)"
    exit 1
fi
