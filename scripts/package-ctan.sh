#!/bin/sh
# Assemble the CTAN upload using the release fonts in dist/.
set -eu
cd "$(dirname "$0")/.."

mkdir -p build
stage=$(mktemp -d "$(pwd)/build/ctan.XXXXXXXX")
trap 'rm -rf "$stage"' EXIT

name=micfong-sans-math
package="$stage/$name"
mkdir -p "$package/source"
cp latex/README.md "latex/$name.sty" "latex/$name.tex" "$package/"
cp dist/MicfongSansMath.otf dist/MicfongSansMath-Bold.otf "$package/"
cp OFL.txt LICENSE-MIT CHANGELOG.md "$package/"
cp scripts/fetch_sources.py scripts/patch_font.py "$package/source/"

(
    cd "$package"
    lualatex -interaction=nonstopmode -halt-on-error \
        -output-directory="$stage" "$name.tex"
)
cp "$stage/$name.pdf" "$package/"

(cd "$stage" && zip -q -X -r "$name.zip" "$name")
mv -f "$stage/$name.zip" "build/$name.zip"
echo "CTAN upload archive: build/$name.zip"
