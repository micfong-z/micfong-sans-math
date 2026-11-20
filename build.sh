#!/bin/sh
# Rebuild the fonts from upstream, check them, and render proof/typst.pdf.
# Arguments go to fetch_sources.py, for example:
#   ./build.sh                  newest Lete Sans Math and IBM Plex releases
#   ./build.sh --lete v0.63     pin Lete to a tag
#   ./build.sh --lete master    Lete's unreleased default branch
set -eu
cd "$(dirname "$0")"

python3 -I scripts/fetch_sources.py "$@"
uv run --script scripts/patch_font.py
# System fonts are ignored so that an installed copy of the font cannot stand in for dist/.
typst compile --root . --ignore-system-fonts \
    --font-path dist --font-path build/sources/lete \
    --font-path build/sources/plex --font-path build/sources/plex-mono \
    proof/typst.typ proof/typst.pdf

version=$(sed -n 's/^VERSION = "\(.*\)"/\1/p' scripts/patch_font.py)
archive="build/MicfongSansMath-$version.zip"
rm -f "$archive"
(cd dist && zip -q -X "../$archive" MicfongSansMath.otf MicfongSansMath-Bold.otf OFL.txt)
echo "Fonts are in dist/, the release archive is $archive. Proof: proof/typst.pdf"
