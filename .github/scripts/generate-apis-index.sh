#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INDEX_DIR="$REPO_ROOT/index/apis/openapi"
SOURCE_PREFIX="apis/openapi"

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

# Collect APIs into buckets using git ls-tree (no checkout needed)
declare -A BUCKETS
declare -A SUB_APIS
total=0

# Get all vendor directories
while IFS= read -r vendor_path; do
    api_name="$(basename "$vendor_path")"
    SUB_APIS[$api_name]=""
done < <(git -C "$REPO_ROOT" ls-tree -d --name-only HEAD "$SOURCE_PREFIX/")

# Get all sub-API directories
while IFS= read -r sub_path; do
    api_name="$(basename "$(dirname "$sub_path")")"
    sub_name="$(basename "$sub_path")"
    if [[ -n "${SUB_APIS[$api_name]:-}" ]]; then
        SUB_APIS[$api_name]+=$'\n'
    fi
    SUB_APIS[$api_name]+="$sub_name"
done < <(git -C "$REPO_ROOT" ls-tree -d --name-only HEAD "$SOURCE_PREFIX"/*/ 2>/dev/null)

# Build bucket entries (sorted for stable output)
SORTED_VENDORS=($(printf '%s\n' "${!SUB_APIS[@]}" | sort))
for api_name in "${SORTED_VENDORS[@]}"; do
    first_char="${api_name:0:1}"
    first_char_upper="$(echo "$first_char" | tr '[:lower:]' '[:upper:]')"

    if [[ "$first_char_upper" =~ ^[A-Z]$ ]]; then
        bucket="$first_char_upper"
    elif [[ "$first_char" =~ ^[0-9]$ ]]; then
        bucket="$first_char"
    else
        bucket="~rest"
    fi

    # Build sub-API links
    sub_links=""
    sub_count=0
    while IFS= read -r sub_name; do
        [[ -z "$sub_name" ]] && continue
        if [[ -n "$sub_links" ]]; then
            sub_links+=" · "
        fi
        sub_links+="[$sub_name](../../../../$SOURCE_PREFIX/$api_name/$sub_name)"
        sub_count=$((sub_count + 1))
    done < <(echo "${SUB_APIS[$api_name]}" | sort)

    if [[ "$sub_count" -gt 5 ]]; then
        apis_cell="[$sub_count APIs](../../../../$SOURCE_PREFIX/$api_name)"
    else
        apis_cell="$sub_links"
    fi

    BUCKETS[$bucket]+="| [$api_name](../../../../$SOURCE_PREFIX/$api_name) | $apis_cell |"$'\n'
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

        if [[ "$bucket" == "~rest" ]]; then
            description="$count APIs starting with non-alphanumeric characters."
        else
            description="$count APIs starting with **$bucket**."
        fi

        cat > "$readme" <<HEREDOC
# APIs — $bucket

Browsing $description

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

total_source=$(git -C "$REPO_ROOT" ls-tree -d --name-only HEAD "$SOURCE_PREFIX/" | wc -l)
echo "Created $total_links links across $(ls -d "$INDEX_DIR"/*/ | wc -l) buckets for $total_source API directories"

if [ "$total_links" -ne "$total_source" ]; then
    echo "WARNING: link count ($total_links) does not match source count ($total_source)"
    exit 1
fi
