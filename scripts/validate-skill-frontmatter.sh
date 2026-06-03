#!/bin/sh
set -eu

# Validate skill frontmatter contracts:
# - root SKILL.md marketplace summary: name, description, version
# - public skills under skills/: name, description, version, validate_prompt

root="${1:-.}"
errors=0

check_frontmatter_fields() {
	file="$1"
	shift
	fields="$*"

	# Extract frontmatter line numbers
	fm_lines=$(grep -n '^---$' "$file" | head -2)
	fm_start=$(echo "$fm_lines" | head -1 | cut -d: -f1)
	fm_end=$(echo "$fm_lines" | tail -1 | cut -d: -f1)

	if [ -z "$fm_start" ] || [ -z "$fm_end" ] || [ "$fm_start" = "$fm_end" ]; then
		echo "ERROR: $file — no YAML frontmatter block found" >&2
		errors=$((errors + 1))
		return
	fi

	duplicate_keys=$(sed -n "$((fm_start + 1)),$((fm_end - 1))p" "$file" | grep -E '^[^[:space:]#][^:]*:' | cut -d: -f1 | sort | uniq -d || true)
	if [ -n "$duplicate_keys" ]; then
		echo "ERROR: $file — duplicate top-level frontmatter keys:" >&2
		echo "$duplicate_keys" | sed 's/^/  - /' >&2
		errors=$((errors + 1))
	fi

	# Check each required field within frontmatter range
	for field in $fields; do
		line=$(sed -n "$((fm_start + 1)),$((fm_end - 1))p" "$file" | grep "^${field}:" || true)
		if [ -z "$line" ]; then
			echo "ERROR: $file — missing required field '$field'" >&2
			errors=$((errors + 1))
			continue
		fi
		val=$(echo "$line" | sed "s/^${field}:[[:space:]]*//" | sed "s/^[\"']//;s/[\"']$//")
		if [ -z "$val" ]; then
			echo "ERROR: $file — field '$field' is empty" >&2
			errors=$((errors + 1))
		fi
	done
}

check_frontmatter_fields "$root/SKILL.md" name description version

skill_files=$(find "$root/skills" -name SKILL.md -not -path '*/_*' | sort)

for file in $skill_files; do
	check_frontmatter_fields "$file" name description version validate_prompt
done

if [ "$errors" -gt 0 ]; then
	exit 1
fi

skill_count=$(echo "$skill_files" | grep -c .)
echo "OK: root SKILL.md and $skill_count public skill SKILL.md files have required frontmatter"
