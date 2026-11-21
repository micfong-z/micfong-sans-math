# Micfong Sans Math for LaTeX

Version 0.10. Maintained by Zixuan Zhang.

Micfong Sans Math is an OpenType math font designed to pair with IBM Plex Sans. It derives from Lete Sans Math by Chenjing Bu and Daniel Flipo and uses letters and numbers from IBM Plex Sans and IBM Plex Mono.

## Installation and use

Install `micfong-sans-math` through your TeX distribution's package manager when it becomes available. To try the archive in one project, copy `micfong-sans-math.sty`, `MicfongSansMath.otf`, and `MicfongSansMath-Bold.otf` next to the main `.tex` file. The fonts are in `dist/` when working from the source repository.

Add this line to the preamble and compile with LuaLaTeX or XeLaTeX.

```latex
\usepackage{micfong-sans-math}
```

The package requires `unicode-math` and `iftex`. It sets the math font and lets you choose the document's text fonts independently. The bold math font has a smaller character set than the regular font. The archive includes a [short manual](micfong-sans-math.pdf) and its [LaTeX source](micfong-sans-math.tex).

## Font sources

The release uses Lete Sans Math v0.63, IBM Plex Sans 1.1.0, and IBM Plex Mono 2.5.0. From the root of the unpacked archive, run the following commands with Python 3 and `uv`. The first downloads the upstream fonts. The second builds the two faces into `dist/`.

```sh
python3 -I source/fetch_sources.py --lete v0.63 --plex 1.1.0 --plex-mono 2.5.0
uv run --script source/patch_font.py
```

## License and support

The fonts use the SIL Open Font License 1.1 (`OFL.txt`). The LaTeX package, documentation, and build scripts use the MIT License (`LICENSE-MIT`).

[Project repository](https://github.com/micfong-z/micfong-sans-math) · [Issue tracker](https://github.com/micfong-z/micfong-sans-math/issues)
