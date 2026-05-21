#!/bin/sh
set -eu

# Validate that every SKILL.md has required YAML frontmatter fields:
# name, description, version, validate_prompt

root="${1:-.}"
errors=0

skill_files=$(find "$root/skills" -name SKILL.md -not -path '*/_*' | sort)

for file in $skill_files; do
	# Extract frontmatter line numbers
	fm_lines=$(grep -n '^---$' "$file" | head -2)
	fm_start=$(echo "$fm_lines" | head -1 | cut -d: -f1)
	fm_end=$(echo "$fm_lines" | tail -1 | cut -d: -f1)

	if [ -z "$fm_start" ] || [ -z "$fm_end" ] || [ "$fm_start" = "$fm_end" ]; then
		echo "ERROR: $file — no YAML frontmatter block found" >&2
		errors=$((errors + 1))
		continue
	fi

	# Check each required field within frontmatter range
	for field in name description version validate_prompt; do
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
done

if [ "$errors" -gt 0 ]; then
	exit 1
fi

skill_count=$(echo "$skill_files" | grep -c .)
echo "OK: $skill_count SKILL.md files have required frontmatter (name, description, version, validate_prompt)"
