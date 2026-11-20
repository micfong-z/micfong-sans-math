# How Micfong Sans Math is made

> [!WARN]
> This document is fully AI-generated.

Micfong Sans Math is Lete Sans Math with the letters and numbers swapped for IBM Plex. Nothing is drawn by hand: `scripts/patch_font.py` copies Plex outlines into Lete's font with [fontTools](https://github.com/fonttools/fonttools), then recalculates the math metrics that depend on letter shapes. Lete keeps every symbol, its `MATH` constants and its glyph order, so formulas are laid out by Lete's rules with Plex letters in them.

## The build

`./build.sh` runs three steps:

1. `scripts/fetch_sources.py` downloads the newest releases of Lete Sans Math, IBM Plex Sans and IBM Plex Mono into `build/sources/`, or the versions passed with `--lete`, `--plex` and `--plex-mono`.
2. `scripts/patch_font.py` builds `dist/MicfongSansMath.otf` from `LeteSansMath.otf` and `dist/MicfongSansMath-Bold.otf` from `LeteSansMath-Bold.otf`, then checks both (see [Checks](#checks)).
3. Typst renders `proof/typst.pdf`, which sets the same formulas in both fonts.

The script never trusts Lete's glyph names. They would mislead: Lete calls U+03B5 `mupvarepsilon` and U+03F5 `mupepsilon`, the reverse of the Unicode names. Instead it gives each glyph a role:

- An encoded glyph gets its role from the Unicode properties of its code point: the base letter it shows, and whether it is bold, italic or monospace. 𝑎 (U+1D44E, MATHEMATICAL ITALIC SMALL A) becomes Plex Italic's `a`.
- An unencoded alternate, such as a script-size form or an old-style figure, inherits a role by following Lete's own `GSUB` from the encoded glyph.

A glyph without a role stays exactly as Lete drew it. New upstream glyphs that are ordinary letters are therefore picked up without changes to the script, and anything else is left alone.

## What comes from where

| Unicode block | From IBM Plex | Kept from Lete |
|---|---|---|
| Basic Latin | A–Z, a–z, 0–9 | punctuation and symbols |
| Latin-1 Supplement | ª º µ Ð ð ² ³ ¹ ¼ ½ ¾ | symbols such as ± × ÷ ¬ |
| Latin Extended-A and B | dotless ı ȷ | Ƶ |
| Greek and Coptic | Α–Ω, α–ω, ς, and ϑ ϕ ϵ ϶ ϴ Ϝ (see [Borrowed forms](#borrowed-forms)) | ϰ ϱ ϖ ϝ |
| Cyrillic | all 76 letters Lete has: А–Я and а–я except Й й, plus Ђ Є Ѕ Љ Њ Ћ Џ and their lower case | |
| Letterlike Symbols | ℎ ℏ, and the Ω and Å signs | ℓ ℇ Ⅎ, ℵ ℶ ℷ ℸ, and the script, black-letter and double-struck letters |
| Number Forms | vulgar fractions ⅓ ⅔ ⅕ ⅖ ⅗ ⅘ ⅙ ⅚ ⅛ ⅜ ⅝ ⅞ | |
| Mathematical Alphanumeric Symbols | bold, italic, bold italic, the four sans-serif styles, and monospace (from Plex Mono): Latin, Greek and digits | script, Fraktur and double-struck styles; ϰ ϱ ϖ in every style; ∂ and ∇ |
| Unencoded alternates | script and script-script sizes (`ssty`), old-style figures (`onum`), dotless forms (`dtls`), the `cv11` g and the `cv14` zero | all others |
| Everything else | | operators, relations, arrows, delimiters, big operators, accents |

In numbers, the regular font takes 1461 of its 4519 glyphs from Plex: 723 math alphanumerics, 222 other encoded letters and digits, and 516 unencoded alternates. 62 of them come from Plex Mono. The bold font takes 814 of 1516. It covers less because Lete Sans Math Bold does: it has no Cyrillic, monospace alphabet or vulgar fractions.

![Glyphs from IBM Plex, and glyphs kept from Lete](images/alphabets.png)

## Letterform choices

Four letterforms differ from what a straight copy would give:

- `g` is single-storey in every style, monospace included. The script tests each style's outlines and picks the one with a single counter.
- `a` and `α` keep Plex's default form for each style, so `a` is double-storey upright and single-storey italic.
- Italic `θ` is Plex's closed upright `θ`, slanted to the italic angle. Plex Italic's own `θ` is looped, so it becomes `ϑ` instead and the two stay distinct.
- `ℏ` takes Plex's `ħ`, so its bar is level rather than Lete's slash.

Plex's default `l` already has a hooked tail, and the monospace zero keeps Plex Mono's dot.

### Borrowed forms

Plex has no glyph at some Greek code points but draws the same letterform elsewhere. These are borrowed rather than left to Lete:

| Character | Plex form used |
|---|---|
| ϑ | Plex Italic's looped θ, deslanted for upright styles |
| ϕ | Cyrillic ф |
| ϵ | Cyrillic є |
| ϶ | Cyrillic э, the mirror of є |
| ϴ | Cyrillic Ө |
| Ϝ | Latin F |

Letters that Plex draws nowhere, such as ϰ ϱ ϖ ϝ Ƶ ℇ Ⅎ and the Hebrew ℵ ℶ ℷ ℸ, stay as Lete drew them.

### OpenType features

Lete's character variants still work, with these results:

- `cv01` has no visible effect: `ℏ` already has the level bar it would give.
- `cv03` to `cv10` swap a Greek letter for its variant: ϵ for ε, κ for ϰ, π for ϖ, ϕ for φ, ρ for ϱ, σ for ς, θ for ϑ, Θ for ϴ. The variants come from Plex, except ϰ ϖ ϱ, which Plex doesn't draw.
- `cv11` gives the double-storey `g`, because single-storey is now the default.
- `cv12` has no visible effect: Plex's `l` already has the tail it would add.
- `cv13` swaps `l` for Lete's `ℓ`, as it does in Lete.
- `cv14` gives Plex's slashed zero.

None of these touch the monospace alphabet. `cv02` and the stylistic sets `ss01` and `ss04` to `ss09` act on symbols and calligraphic capitals, which are Lete's, so they behave exactly as in Lete.

## Math metrics

Lete's hand-set metrics describe Lete's shapes, so the script recalculates these from the Plex outlines for every replaced glyph:

- Top-accent positions, taken from Plex's own mark anchors where it has them, and otherwise measured from the outline
- Italic corrections
- Subscript kerns, fitted to Lete's hand-set values
- Kerning between upright letters, ported from Plex

Lete's `MATH` constants, stretchy variants and `GSUB` are kept as they are. As in Lete, monospace glyphs get no `MATH` entries, so scripts and accents sit on the fixed-width cell.

In the regular font, script sizes use Plex Text and Plex Medium in place of the thickened alternates Lete draws for those sizes. The bold font uses Plex Bold at every size, because Plex has nothing heavier. The proof sheets check the result in two math engines: [`proof/typst.pdf`](../proof/typst.pdf) and [`proof/latex.pdf`](../proof/latex.pdf).

## Checks

After building each font, the script compares it with both sources. The build stops with an error if any of these fail:

- Glyph order or `cmap` differs from Lete
- Any glyph that should be unchanged has changed
- A replaced glyph doesn't match its Plex source
- `g` isn't single-storey, or `a` or `α` isn't Plex's default form
- A monospace glyph isn't from Plex Mono, or isn't Plex Mono's fixed width
- Italic `θ` isn't the closed, slanted form, or italic `ϑ` isn't distinct from it
- A borrowed form isn't used, or a letter Plex draws nowhere (such as `ϰ`) was replaced anyway
- Far fewer glyphs were replaced than expected
- A Reserved Font Name ("Plex" or "Lato") appears in the font's name
- `OFL.txt` is missing a copyright line from one of the upstream licences

To follow an upstream release, run `./build.sh` again. Settings such as the scale, the slanted letters and the borrowed forms are at the top of `scripts/patch_font.py`.
