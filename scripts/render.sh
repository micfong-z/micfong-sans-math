#!/bin/sh
# Render the README images, and the sample documents from the fonts in dist/.
# Run ./build.sh first.
#
# Needs typst, and XeLaTeX and LuaLaTeX from TeX Live. The multilingual samples
# also need IBM Plex Sans SC, TC, JP, KR and Devanagari installed. Typst ignores
# other system fonts, and the LaTeX files load the math fonts by path, so an
# older installed copy of Micfong Sans Math cannot stand in for the one in dist/.
set -eu
cd "$(dirname "$0")/.."

extra=build/system-fonts
rm -rf "$extra"
mkdir -p "$extra"
for dir in "$HOME/Library/Fonts" /Library/Fonts "$HOME/.local/share/fonts" "$HOME/.fonts" \
    /usr/local/share/fonts /usr/share/fonts; do
    [ -d "$dir" ] || continue
    find "$dir" -type f \( -name 'IBMPlexSansSC-*' -o -name 'IBMPlexSansTC-*' -o -name 'IBMPlexSansJP-*' \
        -o -name 'IBMPlexSansKR-*' -o -name 'IBMPlexSansDevanagari-*' \) -exec ln -sf {} "$extra"/ \;
done

typst_render() {
    log=$(typst compile --root . --ignore-system-fonts \
        --font-path dist --font-path build/sources/plex --font-path build/sources/plex-mono \
        --font-path build/sources/lete --font-path "$extra" "$@" 2>&1) || { echo "$log" >&2; exit 1; }
    if printf '%s' "$log" | grep -q 'unknown font family'; then
        printf '%s\n' "$log" >&2
        echo "Install the fonts named above and run again." >&2
        exit 1
    fi
}

# latex_render ENGINE DIR NAME: compile DIR/NAME.tex from inside DIR, twice for references.
latex_render() {
    out="build/latex/$2"
    mkdir -p "$out"
    for _ in 1 2; do
        (cd "$2" && "$1" -interaction=nonstopmode -halt-on-error -output-directory="../$out" "$3.tex" >/dev/null) || {
            tail -30 "$out/$3.log" >&2
            exit 1
        }
    done
    cp "$out/$3.pdf" "$2/$3.pdf"
}

for image in hero multilingual alphabets advanced; do
    for theme in light dark; do
        typst_render --ppi 288 --input theme="$theme" "docs/images/$image.typ" "docs/images/$image-$theme.png"
    done
done
typst_render samples/typst.typ samples/typst.pdf
latex_render xelatex samples latex
echo "Rendered docs/images/*.png, samples/typst.pdf, samples/latex.pdf."
