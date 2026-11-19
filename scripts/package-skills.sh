#!/usr/bin/env bash
# Zip each skill for upload in claude.ai / the Claude desktop app (Customize > Skills > Upload a skill).
# Usage: scripts/package-skills.sh [skill-name ...]    (default: every skill) -> dist/<skill>.zip
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist
skills=("$@")
if [ ${#skills[@]} -eq 0 ]; then
  for d in skills/*/; do [ -f "$d/SKILL.md" ] && skills+=("$(basename "$d")"); done
fi
for s in "${skills[@]}"; do
  [ -f "skills/$s/SKILL.md" ] || { echo "no such skill: $s" >&2; exit 1; }
  rm -f "dist/$s.zip"
  (cd skills && zip -qr "../dist/$s.zip" "$s" \
    -x "*/node_modules/*" "*/__pycache__/*" "*.pyc" "*/.DS_Store" "*/package-lock.json")
  echo "dist/$s.zip  $(du -h "dist/$s.zip" | cut -f1)"
done
