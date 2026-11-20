#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["fonttools>=4.50"]
# ///
"""Rebuild Lete Sans Math with IBM Plex Sans letters and numbers, and IBM Plex Mono
for the monospace alphabet.

Glyph selection never relies on Lete's glyph names. They would be a poor guide:
Lete calls U+03B5 "mupvarepsilon" and U+03F5 "mupepsilon", the reverse of the
Unicode names. Instead:

1. Encoded glyphs get a role from Unicode properties of their code point: which
   base character they show, and whether it is bold or italic.
2. Unencoded alternates (script sizes, old-style numerals, cv/dtls variants) get
   a role by following Lete's own GSUB from the encoded glyphs.

Anything without a role stays byte-for-byte as Lete drew it. New upstream glyphs
are therefore handled automatically when they are ordinary letters, and left
alone otherwise. verify() compares the result against both sources and exits
non-zero if the patch did not do what it should.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import sys
import unicodedata as ud
from dataclasses import dataclass, replace
from pathlib import Path

from fontTools.misc.roundTools import otRound
from fontTools.otlLib import builder as otl
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables as ot

# ---------------------------------------------------------------- configuration

FAMILY = "Micfong Sans Math"  # OFL: must not contain the reserved names "Plex" or "Lato".
PS_FAMILY = FAMILY.replace(" ", "")
VERSION = "0.10"
COPYRIGHT = "Copyright (c) 2026 Zixuan Zhang."
LICENSE_URL = "https://openfontlicense.org"

# Input font -> output font. Bold output draws every letter from Plex Bold.
OUTPUTS = {
    "LeteSansMath.otf": (f"{PS_FAMILY}.otf", "Regular", False),
    "LeteSansMath-Bold.otf": (f"{PS_FAMILY}-Bold.otf", "Bold", True),
}

# Multiplier applied to Plex outlines and advances. Plex's measured heights
# (x 516, cap 698) already sit close to Lete's (x 506, cap 716), so none is needed.
SCALE = 1.0

# Plex files by (mono, bold, italic), indexed by optical tier: text, script,
# scriptscript. Lete thickens script sizes by 14% and 25%; Plex Text and Medium
# are +16% and +36%. Plex has nothing heavier than Bold, so bold styles stay put.
# Lete has no script-size monospace glyphs today; the mono tiers are a safeguard.
PLEX_FILES = {
    (False, False, False): ["IBMPlexSans-Regular", "IBMPlexSans-Text", "IBMPlexSans-Medium"],
    (False, False, True): ["IBMPlexSans-Italic", "IBMPlexSans-TextItalic", "IBMPlexSans-MediumItalic"],
    (False, True, False): ["IBMPlexSans-Bold"] * 3,
    (False, True, True): ["IBMPlexSans-BoldItalic"] * 3,
    (True, False, False): ["IBMPlexMono-Regular", "IBMPlexMono-Text", "IBMPlexMono-Medium"],
    (True, True, False): ["IBMPlexMono-Bold"] * 3,
}
# Directory under the sources folder holding each family's files.
PLEX_DIRS = {"IBMPlexSans": "plex", "IBMPlexMono": "plex-mono"}

# g is drawn single-storey in every style, selected glyph by glyph. Every other
# letter, including a and alpha, keeps Plex's default form for its style.
SINGLE_STOREY_G_IN_MONO = True  # Plex Mono's default g is binocular, like Plex Sans's.

# Italic styles draw these from the upright file, skewed to Plex's italic angle.
# Plex Italic's theta is looped, which makes it nearly identical to U+03D1.
SLANTED_FROM_UPRIGHT = {0x3B8}

# Plex has no glyph at these code points but draws the same letterform at another
# one: borrow it rather than fall back to Lete. "italic" takes the italic file's
# glyph in every style, deslanted for upright ones; "same" uses the target's style.
BORROWED = {
    0x03D1: (0x03B8, "italic"),  # ϑ: Plex Italic's own theta is the looped form.
    0x03D5: (0x0444, "same"),  # ϕ: Cyrillic ef has the straight-stemmed phi.
    0x03F5: (0x0454, "same"),  # ϵ: Cyrillic Ukrainian ie is a lunate epsilon.
    0x03F6: (0x044D, "same"),  # ϶: Cyrillic e is its mirror, as ϶ is ϵ's.
    0x03F4: (0x04E8, "same"),  # ϴ: Cyrillic barred O is theta with the bar joined.
    0x03DC: (0x0046, "same"),  # Ϝ: Latin F.
}

# Subscript pull-in, as a share of the gap between the advance and the outline's
# lower right edge. Fitted to Lete's hand-set values, with the same limit.
SUBSCRIPT_KERN_FACTOR = 0.33
SUBSCRIPT_KERN_LIMIT = 120
SUBSCRIPT_BAND_TOP = 200  # Outline above this height does not obstruct a subscript.

# Fails the build if far fewer glyphs than this are replaced: a sign that an
# upstream change has broken role detection rather than a genuine shrinkage.
MIN_REPLACED = {"Regular": 1200, "Bold": 700}


# ------------------------------------------------------------------- roles

@dataclass(frozen=True)
class Role:
    """Where a Lete glyph's replacement comes from."""

    glyph: str  # Plex glyph name.
    bold: bool
    italic: bool
    tier: int = 0
    base: int = 0  # Base code point, for features that depend on the character.
    mono: bool = False  # Drawn from IBM Plex Mono rather than IBM Plex Sans.
    # +1: italic style drawn by slanting the upright glyph.
    # -1: upright style drawn by deslanting the italic glyph.
    skew: int = 0
    borrowed: int = 0  # Code point the form was borrowed from, if not base itself.


def style_of(cp: int) -> tuple[int, bool, bool, bool] | None:
    """(base code point, bold, italic, mono) if cp should come from Plex, else None."""
    char = chr(cp)
    category = ud.category(char)
    if 0x2100 <= cp < 0x2150:  # Letterlike Symbols.
        name = ud.name(char, "")
        if category[0] != "L" or any(word in name for word in ("SCRIPT", "BLACK-LETTER", "DOUBLE-STRUCK")):
            return None
        # Follow <font> variants (ℎ is italic h, ℏ italic ħ) and canonical singletons
        # (Ω and Å signs), never <compat>: that would also fold ϰ into κ elsewhere.
        parts = ud.decomposition(char).split()
        base = int(parts[-1], 16) if len(parts) == 1 or (len(parts) == 2 and parts[0] == "<font>") else cp
        # PLANCK CONSTANT is math italic h; U+1D455 is deliberately unassigned.
        return base, False, name.startswith("PLANCK CONSTANT"), False
    if cp >= 0x1D400:
        name = ud.name(char, "")
        if not name.startswith("MATHEMATICAL ") or any(
            word in name for word in ("SCRIPT", "FRAKTUR", "DOUBLE-STRUCK")
        ):
            return None
        decomposition = ud.decomposition(char).split()
        if len(decomposition) != 2 or decomposition[0] != "<font>":
            return None
        # One step only: full NFKC would fold variants such as U+03F5 into U+03B5.
        base = int(decomposition[1], 16)
        if ud.category(chr(base))[0] != "L" and ud.category(chr(base)) != "Nd":
            return None  # Bold nabla and partial are symbols.
        return base, "BOLD" in name, "ITALIC" in name, "MONOSPACE" in name
    # ϶ is classed as a math symbol, but it is the mirror of ϵ: take it with its pair.
    if cp < 0x500 and (category[0] == "L" or category in ("Nd", "No") or cp in BORROWED):
        return cp, False, False, False
    if 0x2150 <= cp <= 0x218F and category == "No":  # Number Forms: vulgar fractions.
        return cp, False, False, False
    return None


def gsub_features(font: TTFont) -> dict[str, list[tuple[str, list[str]]]]:
    """Each GSUB feature as (source, targets) pairs, in lookup order."""
    table = font["GSUB"].table
    lookups: dict[str, set[int]] = {}
    for record in table.FeatureList.FeatureRecord:
        lookups.setdefault(record.FeatureTag, set()).update(record.Feature.LookupListIndex)
    features: dict[str, list[tuple[str, list[str]]]] = {}
    for tag, indices in lookups.items():
        pairs = features.setdefault(tag, [])
        for index in sorted(indices):
            for subtable in table.LookupList.Lookup[index].SubTable:
                subtable = getattr(subtable, "ExtSubTable", subtable)
                if isinstance(subtable, ot.SingleSubst):
                    pairs += [(src, [dst]) for src, dst in subtable.mapping.items()]
                elif isinstance(subtable, ot.AlternateSubst):
                    pairs += [(src, list(dst)) for src, dst in subtable.alternates.items()]
    return features


class Plex:
    """The Plex fonts, opened on demand, with the features this script consults."""

    def __init__(self, sources: Path):
        self.sources = sources
        self.fonts: dict[str, TTFont] = {}
        self.anchors: dict[str, dict[str, tuple[int, int]]] = {}

    def file(self, role: Role) -> str:
        source_italic = role.italic if role.skew == 0 else role.skew < 0
        return PLEX_FILES[(role.mono, role.bold, source_italic)][role.tier]

    def font(self, role: Role) -> TTFont:
        return self.named(self.file(role))

    def matrix(self, role: Role) -> tuple[float, float, float, float, float, float]:
        """TransformPen matrix from the role's source outline to the patched glyph."""
        if not role.skew:
            return (SCALE, 0, 0, SCALE, 0, 0)
        italic_file = PLEX_FILES[(role.mono, role.bold, True)][role.tier]
        angle = math.radians(abs(self.named(italic_file)["post"].italicAngle))
        skew = role.skew * math.tan(angle)
        bounds = BoundsPen(None)
        self.font(role).getGlyphSet()[role.glyph].draw(bounds)
        # Pivot at mid-height so the glyph stays centred on its advance.
        middle = (bounds.bounds[1] + bounds.bounds[3]) / 2
        return (SCALE, 0, skew * SCALE, SCALE, -skew * middle * SCALE, 0)

    def named(self, name: str) -> TTFont:
        """A Plex font by file stem, such as IBMPlexSans-Regular."""
        if name not in self.fonts:
            path = self.sources / PLEX_DIRS[name.split("-")[0]] / f"{name}.otf"
            if not path.exists():
                raise SystemExit(f"Missing {path}; run fetch_sources.py first")
            self.fonts[name] = TTFont(path)
        return self.fonts[name]

    def feature(self, name: str, tag: str) -> dict[str, str]:
        pairs = gsub_features(self.named(name)).get(tag, [])
        return {src: dst[0] for src, dst in pairs}

    def top_anchors(self, name: str) -> dict[str, tuple[int, int]]:
        """Top-accent anchors. The "above" lookup is the one placing a's mark highest."""
        if name in self.anchors:
            return self.anchors[name]
        table = self.named(name)["GPOS"].table
        indices = {
            i
            for record in table.FeatureList.FeatureRecord
            if record.FeatureTag == "mark"
            for i in record.Feature.LookupListIndex
        }
        best: tuple[int, dict[str, tuple[int, int]]] | None = None
        for index in sorted(indices):
            anchors: dict[str, tuple[int, int]] = {}
            for subtable in table.LookupList.Lookup[index].SubTable:
                subtable = getattr(subtable, "ExtSubTable", subtable)
                if not isinstance(subtable, ot.MarkBasePos):
                    continue
                for glyph, record in zip(subtable.BaseCoverage.glyphs, subtable.BaseArray.BaseRecord):
                    for anchor in record.BaseAnchor:
                        if anchor is not None:
                            anchors[glyph] = (anchor.XCoordinate, anchor.YCoordinate)
            if "a" in anchors and (best is None or anchors["a"][1] > best[0]):
                best = (anchors["a"][1], anchors)
        self.anchors[name] = best[1] if best else {}
        return self.anchors[name]


# ----------------------------------------------------------- outline analysis

def contours(font: TTFont, glyph: str, steps: int = 16) -> list[list[tuple[float, float]]]:
    """The glyph as closed polylines, with curves flattened."""
    pen = RecordingPen()
    font.getGlyphSet()[glyph].draw(pen)
    result: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    for op, args in pen.value:
        if op == "moveTo":
            current = [args[0]]
            result.append(current)
        elif op == "lineTo":
            current.append(args[0])
        elif op == "curveTo":
            p0, p1, p2, p3 = current[-1], *args
            for i in range(1, steps + 1):
                t = i / steps
                u = 1 - t
                current.append(
                    tuple(
                        u**3 * p0[k] + 3 * u**2 * t * p1[k] + 3 * u * t**2 * p2[k] + t**3 * p3[k]
                        for k in (0, 1)
                    )
                )
    return result


def right_edge(polylines, low: float, high: float) -> float | None:
    """Largest x of the outline within low <= y <= high, including edge crossings."""
    best = None
    for line in polylines:
        for (x0, y0), (x1, y1) in zip(line, line[1:] + line[:1]):
            candidates = [(x, y) for x, y in ((x0, y0), (x1, y1)) if low <= y <= high]
            if y0 != y1:
                for y in (low, high):
                    if min(y0, y1) < y < max(y0, y1):
                        candidates.append((x0 + (x1 - x0) * (y - y0) / (y1 - y0), y))
            for x, _ in candidates:
                best = x if best is None else max(best, x)
    return best


def is_single_storey_g(font: TTFont, glyph: str) -> bool:
    return len(contours(font, glyph)) == 2  # Binocular g has two counters plus the outline.


def single_storey_g(plex: Plex, name: str) -> str:
    font = plex.named(name)
    default = font.getBestCmap()[ord("g")]
    alternate = plex.feature(name, "ss02").get(default)
    for glyph in filter(None, (default, alternate)):
        if is_single_storey_g(font, glyph):
            return glyph
    raise SystemExit(f"Plex {name}: no single-storey g among {default!r}, {alternate!r}")


# --------------------------------------------------------------- role assignment

def plex_form(plex: Plex, base: int, bold: bool, italic: bool, mono: bool) -> Role | None:
    """The Plex glyph for base in this style: its own if Plex has one, else a borrowed form."""
    skew = 1 if italic and base in SLANTED_FROM_UPRIGHT else 0
    role = Role("", bold, italic, base=base, mono=mono, skew=skew)
    glyph = plex.font(role).getBestCmap().get(base)
    if glyph is not None:
        if base == ord("g") and (SINGLE_STOREY_G_IN_MONO or not mono):
            glyph = single_storey_g(plex, plex.file(role))
        return replace(role, glyph=glyph)
    if base not in BORROWED:
        return None
    source, form = BORROWED[base]
    skew = -1 if form == "italic" and not italic else 0
    role = Role("", bold, italic, base=base, mono=mono, skew=skew, borrowed=source)
    glyph = plex.font(role).getBestCmap().get(source)
    return replace(role, glyph=glyph) if glyph is not None else None


def assign_roles(lete: TTFont, plex: Plex, force_bold: bool) -> tuple[dict[str, Role], list[str]]:
    roles: dict[str, Role] = {}
    warnings: list[str] = []

    for cp, name in sorted(lete.getBestCmap().items()):
        style = style_of(cp)
        if style is None:
            continue
        base, bold, italic, mono = style
        role = plex_form(plex, base, bold or force_bold, italic, mono)
        if role is None:
            continue  # Plex draws this form nowhere (e.g. ϰ, ϱ, ϖ): Lete's stays.
        # Upright and sans code points share a glyph in some fonts: first one wins.
        roles.setdefault(name, role)

    features = gsub_features(lete)
    # Lete gives nearly every alternate a Private Use code point, which says nothing
    # about what it shows. Only a real code point makes a glyph independently encoded.
    encoded = {
        name
        for cp, name in lete.getBestCmap().items()
        if ud.category(chr(cp)) != "Co"
    }

    def alternate_role(tag: str, source: Role) -> Role | None:
        file = plex.file(replace(source, tier=0))
        if tag == "onum":
            target = plex.feature(file, "onum").get(source.glyph)
        elif tag == "dtls":
            dotless = {ord("i"): 0x131, ord("j"): 0x237}.get(source.base)
            target = plex.named(file).getBestCmap().get(dotless) if dotless else None
        elif source.base == ord("g"):
            # Lete's "other g" feature (cv11) now gives the binocular form.
            default = plex.named(file).getBestCmap()[ord("g")]
            alternate = plex.feature(file, "ss02").get(default)
            target = alternate if source.glyph == default else default
        elif source.base == ord("0"):
            target = plex.feature(file, "ss03").get(source.glyph)  # Slashed, as in Lete's cv14.
        elif source.base == ord("l"):
            target = source.glyph  # Plex's l already has the tail Lete's cv12 would add.
        elif source.base == 0x127:
            target = source.glyph  # Plex's ħ already has the level bar Lete's cv01 gives ℏ.
        else:
            return None
        return replace(source, glyph=target) if target else None

    changed = True
    while changed:
        changed = False
        for tag, pairs in features.items():
            for src, targets in pairs:
                role = roles.get(src)
                if role is None:
                    continue
                for index, target in enumerate(targets):
                    if target in roles or target in encoded:
                        continue  # cv03 and the like swap between encoded glyphs.
                    if tag == "ssty":
                        derived = replace(role, tier=min(index + 1, 2))
                    else:
                        derived = alternate_role(tag, role)
                        if derived is None:
                            warnings.append(f"{tag}: no Plex form for {target}; kept Lete's")
                            continue
                    roles[target] = derived
                    changed = True
    return roles, sorted(set(warnings))


# ------------------------------------------------------------------ glyph transfer

def draw_role(plex: Plex, role: Role, pen) -> None:
    plex.font(role).getGlyphSet()[role.glyph].draw(TransformPen(pen, plex.matrix(role)))


def transfer_glyphs(target: TTFont, roles: dict[str, Role], plex: Plex) -> None:
    cff = target["CFF "].cff
    top = cff.topDictIndex[0]
    if hasattr(top, "FDArray"):
        raise SystemExit("Lete has become a CID-keyed CFF font; transfer_glyphs needs extending")
    private = top.Private
    nominal = getattr(private, "nominalWidthX", 0) or 0
    hmtx = target["hmtx"]
    for name, role in roles.items():
        source = plex.font(role)
        if role.glyph not in source.getGlyphSet():
            raise SystemExit(f"Plex lacks {role.glyph} needed for {name}")
        advance = otRound(source["hmtx"][role.glyph][0] * SCALE)
        pen = T2CharStringPen(advance - nominal, None)
        draw_role(plex, role, pen)
        top.CharStrings[name] = pen.getCharString(private=private, globalSubrs=cff.GlobalSubrs)
        bounds = BoundsPen(None)
        draw_role(plex, role, bounds)
        hmtx[name] = (advance, otRound(bounds.bounds[0]) if bounds.bounds else 0)


# ------------------------------------------------------------------- MATH table

def math_value(value: int) -> ot.MathValueRecord:
    record = ot.MathValueRecord()
    record.Value = otRound(value)
    record.DeviceTable = None
    return record


def constant_kern(value: int) -> ot.MathKern:
    kern = ot.MathKern()
    kern.HeightCount = 0
    kern.CorrectionHeight = []
    kern.KernValue = [math_value(value)]
    return kern


def top_accent(role: Role, plex: Plex, polylines, height: float, bounds) -> int:
    # A skewed glyph has moved away from its upright anchor, so measure it instead.
    anchor = None if role.skew else plex.top_anchors(plex.file(role)).get(role.glyph)
    if anchor is not None and anchor[1] >= height * 0.6:
        return otRound(anchor[0] * SCALE)
    if role.italic:
        # Follow the slant: centre on the outline's extent near the top.
        sliced = []
        for line in polylines:
            sliced += [x for x, y in line if y >= height * 0.85]
        if sliced:
            return otRound((min(sliced) + max(sliced)) / 2)
    return otRound((bounds[0] + bounds[2]) / 2)


def patch_math(target: TTFont, roles: dict[str, Role], plex: Plex) -> None:
    math_table = target["MATH"].table
    info = math_table.MathGlyphInfo
    order = {name: index for index, name in enumerate(target.getGlyphOrder())}

    italics = info.MathItalicsCorrectionInfo
    corrections = dict(zip(italics.Coverage.glyphs, italics.ItalicsCorrection))
    accents_table = info.MathTopAccentAttachment
    accents = dict(zip(accents_table.TopAccentCoverage.glyphs, accents_table.TopAccentAttachment))
    kerns_table = info.MathKernInfo
    kerns = dict(zip(kerns_table.MathKernCoverage.glyphs, kerns_table.MathKernInfoRecords))

    for name, role in roles.items():
        # Lete's values describe Lete's shapes, so none carry over.
        corrections.pop(name, None)
        accents.pop(name, None)
        kerns.pop(name, None)
        if role.mono:
            # Like Lete, give monospace glyphs no entries: scripts and accents then
            # sit on the fixed-pitch cell, and the cell's centre is the accent point.
            continue

        source = plex.font(role)
        xx, xy, yx, yy, dx, dy = plex.matrix(role)
        polylines = [
            [(xx * x + yx * y + dx, xy * x + yy * y + dy) for x, y in line]
            for line in contours(source, role.glyph)
        ]
        if not polylines:
            continue
        advance = source["hmtx"][role.glyph][0] * SCALE
        xs = [x for line in polylines for x, _ in line]
        ys = [y for line in polylines for _, y in line]
        height = max(ys)
        bounds = (min(xs), min(ys), max(xs), height)

        accents[name] = math_value(top_accent(role, plex, polylines, height, bounds))

        if role.italic:
            upper = right_edge(polylines, height * 0.5, height + 1) or 0
            correction = upper - advance
            if correction >= 1:
                corrections[name] = math_value(correction)

        lower = right_edge(polylines, -10_000, SUBSCRIPT_BAND_TOP)
        if lower is not None:
            kern = min(max(0, advance - lower) * SUBSCRIPT_KERN_FACTOR, SUBSCRIPT_KERN_LIMIT)
            kern = round(kern / 10) * 10
            if kern:
                record = ot.MathKernInfoRecord()
                record.TopRightMathKern = None
                record.TopLeftMathKern = None
                record.BottomRightMathKern = constant_kern(-kern)
                record.BottomLeftMathKern = None
                kerns[name] = record

    glyphs = sorted(corrections, key=order.__getitem__)
    italics.Coverage.glyphs = glyphs
    italics.ItalicsCorrection = [corrections[g] for g in glyphs]
    italics.ItalicsCorrectionCount = len(glyphs)

    glyphs = sorted(accents, key=order.__getitem__)
    accents_table.TopAccentCoverage.glyphs = glyphs
    accents_table.TopAccentAttachment = [accents[g] for g in glyphs]
    accents_table.TopAccentAttachmentCount = len(glyphs)

    glyphs = sorted(kerns, key=order.__getitem__)
    kerns_table.MathKernCoverage.glyphs = glyphs
    kerns_table.MathKernInfoRecords = [kerns[g] for g in glyphs]
    kerns_table.MathKernCount = len(glyphs)


# ----------------------------------------------------------------------- kerning

def plex_kerning(font: TTFont, glyphs: set[str]) -> dict[tuple[str, str], int]:
    """Plex's kern values between the given glyphs, following OpenType subtable order."""
    table = font["GPOS"].table
    indices = sorted(
        {
            i
            for record in table.FeatureList.FeatureRecord
            if record.FeatureTag == "kern"
            for i in record.Feature.LookupListIndex
        }
    )
    pairs: dict[tuple[str, str], int] = {}
    for index in indices:
        subtables = [getattr(s, "ExtSubTable", s) for s in table.LookupList.Lookup[index].SubTable]
        subtables = [s for s in subtables if isinstance(s, ot.PairPos)]
        for first in glyphs:
            for second in glyphs:
                if (first, second) in pairs:
                    continue  # Script-specific lookups can repeat a pair: do not add twice.
                for subtable in subtables:
                    if first not in subtable.Coverage.glyphs:
                        continue
                    if subtable.Format == 1:
                        pair_set = subtable.PairSet[subtable.Coverage.glyphs.index(first)]
                        match = next(
                            (r for r in pair_set.PairValueRecord if r.SecondGlyph == second), None
                        )
                        if match is None:
                            continue
                        value = match.Value1
                    else:
                        class1 = subtable.ClassDef1.classDefs.get(first, 0)
                        class2 = subtable.ClassDef2.classDefs.get(second, 0)
                        value = subtable.Class1Record[class1].Class2Record[class2].Value1
                    amount = getattr(value, "XAdvance", 0) or 0
                    if amount:
                        pairs[(first, second)] = otRound(amount * SCALE)
                    break  # OpenType: the first subtable covering the pair decides.
    return pairs


def patch_kerning(target: TTFont, roles: dict[str, Role], plex: Plex) -> int:
    """Swap Lete's kern pairs involving replaced glyphs for Plex's. Returns pairs added."""
    table = target["GPOS"].table
    lookups = [
        table.LookupList.Lookup[i]
        for record in table.FeatureList.FeatureRecord
        if record.FeatureTag == "kern"
        for i in record.Feature.LookupListIndex
    ]
    if not lookups:
        return 0  # Lete Bold has no kerning, so there is nothing to bring into line.
    lookup = lookups[0]

    order = target.getReverseGlyphMap()
    kept: dict[tuple[str, str], tuple] = {}
    for subtable in lookup.SubTable:
        subtable = getattr(subtable, "ExtSubTable", subtable)
        if not isinstance(subtable, ot.PairPos) or subtable.Format != 1:
            raise SystemExit("Lete's kern lookup changed format; patch_kerning needs extending")
        for first, pair_set in zip(subtable.Coverage.glyphs, subtable.PairSet):
            for record in pair_set.PairValueRecord:
                if first not in roles and record.SecondGlyph not in roles:
                    kept[(first, record.SecondGlyph)] = (record.Value1, record.Value2)

    # Only upright text-size letters. Math italics are separate variables, not words.
    # Borrowed and skewed forms are left out: they share a Plex glyph name with a
    # letter that is its own source (Ϝ with F), which would take that letter's kerning.
    cmap = target.getBestCmap()
    upright: dict[str, str] = {}
    for cp, name in cmap.items():
        role = roles.get(name)
        if role and cp < 0x500 and role.tier == 0 and not (role.italic or role.borrowed or role.skew):
            if role.glyph in upright:
                print(f"  warning: {name} and {upright[role.glyph]} share Plex {role.glyph}; "
                      f"only {upright[role.glyph]} gets its kerning")
                continue
            upright[role.glyph] = name
    source = plex.named(PLEX_FILES[(False, roles[cmap[ord("a")]].bold, False)][0])
    added = plex_kerning(source, set(upright))

    pairs = dict(kept)
    for (first, second), amount in added.items():
        pairs[(upright[first], upright[second])] = (otl.buildValue({"XAdvance": amount}), None)
    subtable = otl.buildPairPosGlyphsSubtable(pairs, order)
    lookup.SubTable = [subtable]
    lookup.SubTableCount = 1
    lookup.LookupType = 2
    return len(added)


# ---------------------------------------------------------------------- naming

def rename(target: TTFont, style: str, plex: Plex, uses_mono: bool) -> None:
    name_table = target["name"]
    # Lete's notice reads "Lete Sans Math (c) 2024-2026 Chenjing Bu, Daniel Flipo."
    lete_notice = (name_table.getDebugName(0) or "Lete Sans Math").rstrip(".")
    lete_version = (name_table.getDebugName(5) or "").replace("Version ", "")
    is_regular = style == "Regular"
    full = FAMILY if is_regular else f"{FAMILY} {style}"
    postscript = PS_FAMILY if is_regular else f"{PS_FAMILY}-{style}"

    def plex_version(stem: str) -> str:
        return plex.named(stem)["name"].getDebugName(5).replace("Version ", "")

    version = f"Version {VERSION}; Lete Sans Math {lete_version}; IBM Plex Sans {plex_version('IBMPlexSans-Regular')}"
    sources = "IBM Plex Sans"
    if uses_mono:
        version += f"; IBM Plex Mono {plex_version('IBMPlexMono-Regular')}"
        sources = "IBM Plex Sans and IBM Plex Mono"
    notice = (
        f"{COPYRIGHT} Based on {lete_notice}, and {sources} (c) 2017 IBM Corp. "
        f"with Reserved Font Name \"Plex\"."
    )
    values = {
        0: notice,
        1: FAMILY,
        2: style,
        3: f"{VERSION};{postscript}",
        4: full,
        5: version,
        6: postscript,
        10: f"Lete Sans Math with its letters and numbers drawn from {sources}.",
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1. "
        f"This license is available with a FAQ at: {LICENSE_URL}",
        14: LICENSE_URL,
    }
    platforms = {(r.platformID, r.platEncID, r.langID) for r in name_table.names if r.nameID == 1}
    for name_id, string in values.items():
        for platform in platforms:
            name_table.setName(string, name_id, *platform)
    target["head"].fontRevision = float(VERSION)

    cff = target["CFF "].cff
    cff.fontNames = [postscript]
    top = cff.topDictIndex[0]
    top.FamilyName = FAMILY
    top.FullName = full
    top.version = VERSION
    top.Notice = notice
    if hasattr(top, "Copyright"):
        top.Copyright = notice


def update_metrics(target: TTFont, plex: Plex, bold: bool) -> None:
    # Lete's values (450, 662) are out of date, and Plex's are true for the new letters.
    source = plex.named("IBMPlexSans-Bold" if bold else "IBMPlexSans-Regular")["OS/2"]
    target["OS/2"].sxHeight = otRound(source.sxHeight * SCALE)
    target["OS/2"].sCapHeight = otRound(source.sCapHeight * SCALE)


# ------------------------------------------------------------------ verification

def outline(font: TTFont, glyph: str):
    pen = RecordingPen()
    font.getGlyphSet()[glyph].draw(pen)
    return pen.value


def verify(path: Path, lete_path: Path, roles: dict[str, Role], plex: Plex, style: str) -> None:
    built, lete = TTFont(path), TTFont(lete_path)
    errors: list[str] = []

    if built.getGlyphOrder() != lete.getGlyphOrder():
        errors.append("glyph order differs from Lete")
    if built.getBestCmap() != lete.getBestCmap():
        errors.append("cmap differs from Lete")
    if len(roles) < MIN_REPLACED[style]:
        errors.append(f"only {len(roles)} glyphs replaced (expected at least {MIN_REPLACED[style]})")
    for name in ("Plex", "Lato"):
        for id_ in (1, 4, 6):
            if name in (built["name"].getDebugName(id_) or ""):
                errors.append(f"reserved font name {name} appears in name ID {id_}")

    changed_symbols = [
        glyph
        for glyph in lete.getGlyphOrder()
        if glyph not in roles
        and (
            outline(built, glyph) != outline(lete, glyph)
            or built["hmtx"][glyph][0] != lete["hmtx"][glyph][0]
        )
    ]
    if changed_symbols:
        errors.append(f"{len(changed_symbols)} non-letter glyphs changed: {changed_symbols[:8]}")

    wrong = []
    for glyph, role in roles.items():
        expected = RecordingPen()
        draw_role(plex, role, expected)
        got = outline(built, glyph)
        rounded = [
            (op, tuple((otRound(x), otRound(y)) for x, y in args)) for op, args in expected.value
        ]
        # The pen merges straight runs and drops zero-length segments, so compare key points.
        points = {p for _, args in rounded for p in args}
        got_points = {(otRound(x), otRound(y)) for _, args in got for x, y in args}
        if not got_points <= points:
            wrong.append(glyph)
    if wrong:
        errors.append(f"{len(wrong)} glyphs do not match their Plex source: {wrong[:8]}")

    # The chosen letterforms: single-storey g, default a and alpha, closed italic theta.
    cmap = built.getBestCmap()
    for cp, label in ((ord("g"), "upright"), (0x1D454, "italic"), (0x1D420, "bold"), (0x1D488, "bold italic")):
        if not is_single_storey_g(built, cmap[cp]):
            errors.append(f"{label} g is not single-storey")
    for cp in (ord("a"), 0x1D44E, 0x1D41A, 0x1D482):
        role = roles.get(cmap[cp])
        if role is None or role.glyph != plex.font(role).getBestCmap()[ord("a")]:
            errors.append(f"U+{cp:04X} should use Plex's default a, got {role}")
    for cp in (0x3B1, 0x1D6FC, 0x1D6C2, 0x1D736):
        role = roles.get(cmap[cp])
        if role is None or role.glyph != "alpha":
            errors.append(f"U+{cp:04X} should use Plex's default alpha, got {role}")
    for style_name in ("ITALIC", "BOLD ITALIC", "SANS-SERIF BOLD ITALIC"):
        theta = cmap[ord(ud.lookup(f"MATHEMATICAL {style_name} SMALL THETA"))]
        role = roles.get(theta)
        if role is None or role.skew != 1 or len(contours(built, theta)) != 3:
            errors.append(f"{style_name} theta should be the closed upright form, slanted; got {role}")
        # The theta symbol must be Plex Italic's own looped theta, not the slanted one.
        symbol = cmap.get(ord(ud.lookup(f"MATHEMATICAL {style_name} THETA SYMBOL")))
        role = roles.get(symbol)
        if symbol and (role is None or role.skew or outline(built, symbol) == outline(built, theta)):
            errors.append(f"{style_name} theta symbol should be Plex Italic's looped theta; got {role}")

    # Each borrowed form is used wherever the input has its code point, and forms
    # Plex draws nowhere stay Lete's (a looser rule would fold ϰ into κ, say).
    unborrowed = [
        f"U+{cp:04X}"
        for cp, name in cmap.items()
        if (style := style_of(cp)) and style[0] in BORROWED and not getattr(roles.get(name), "borrowed", 0)
    ]
    if unborrowed:
        errors.append(f"{len(unborrowed)} glyphs should borrow a Plex form: {sorted(unborrowed)[:8]}")
    for cp in (0x03F0, 0x03F1, 0x03D6, 0x2113):  # ϰ ϱ ϖ ℓ
        if cp in cmap and cmap[cp] in roles:
            errors.append(f"U+{cp:04X} has no Plex form but was replaced by {roles[cmap[cp]]}")

    # Monospace, where the input has it (Lete Bold has none). The width test is
    # independent of the roles: Plex Sans widths vary, Plex Mono's never do.
    mono_cps = [cp for cp in (*range(0x1D670, 0x1D6A4), *range(0x1D7F6, 0x1D800)) if cp in cmap]
    if mono_cps:
        plex_mono = plex.named(PLEX_FILES[(True, False, False)][0])
        pitch = plex_mono["hmtx"][plex_mono.getBestCmap()[ord("a")]][0] * SCALE
        off_pitch = [f"U+{cp:04X}" for cp in mono_cps if built["hmtx"][cmap[cp]][0] != otRound(pitch)]
        if off_pitch:
            errors.append(f"{len(off_pitch)} monospace glyphs are not {otRound(pitch)} wide: {off_pitch[:8]}")
        not_mono = [f"U+{cp:04X}" for cp in mono_cps if not getattr(roles.get(cmap[cp]), "mono", False)]
        if not_mono:
            errors.append(f"{len(not_mono)} monospace glyphs not drawn from Plex Mono: {not_mono[:8]}")
        mono_a, mono_g = 0x1D68A, 0x1D690
        if mono_a in cmap and roles[cmap[mono_a]].glyph != plex_mono.getBestCmap()[ord("a")]:
            errors.append("monospace a should be Plex Mono's default a")
        if mono_g in cmap and SINGLE_STOREY_G_IN_MONO and not is_single_storey_g(built, cmap[mono_g]):
            errors.append("monospace g is not single-storey")

    if errors:
        print(f"VERIFY FAILED for {path.name}:", *errors, sep="\n  ", file=sys.stderr)
        raise SystemExit(1)
    print(f"  verified: {len(roles)} glyphs from Plex, {len(lete.getGlyphOrder()) - len(roles)} unchanged")


# -------------------------------------------------------------------------- main

def build(lete_path: Path, output: Path, style: str, bold: bool, plex: Plex) -> None:
    reference = TTFont(lete_path)  # Read-only: keeps GSUB unparsed in the output font.
    roles, warnings = assign_roles(reference, plex, bold)
    target = TTFont(lete_path)
    transfer_glyphs(target, roles, plex)
    patch_math(target, roles, plex)
    added = patch_kerning(target, roles, plex)
    update_metrics(target, plex, bold)
    mono = sum(role.mono for role in roles.values())
    rename(target, style, plex, uses_mono=mono > 0)
    output.parent.mkdir(parents=True, exist_ok=True)
    target.save(output)
    print(f"{output.name}: {len(roles)} glyphs replaced ({mono} from Plex Mono), {added} kern pairs from Plex")
    if not mono:
        print("  no monospace glyphs in this Lete font, so none from Plex Mono")
    for warning in warnings:
        print(f"  warning: {warning}")
    kept = [cp for cp, name in reference.getBestCmap().items() if style_of(cp) and name not in roles]
    bases = "".join(sorted({chr(style_of(cp)[0]) for cp in kept}))
    print(f"  letters Plex draws nowhere, kept from Lete: {len(kept)} glyphs of {bases}")
    borrowed = sorted({(r.base, r.borrowed) for r in roles.values() if r.borrowed})
    print("  borrowed forms: " + ", ".join(f"{chr(b)} from {chr(s)}" for b, s in borrowed))
    verify(output, lete_path, roles, plex, style)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="Patch Lete Sans Math with IBM Plex Sans letters.")
    parser.add_argument("--sources", type=Path, default=root / "build" / "sources")
    parser.add_argument("--output", type=Path, default=root / "dist")
    args = parser.parse_args()

    plex = Plex(args.sources)
    for input_name, (output_name, style, bold) in OUTPUTS.items():
        lete_path = args.sources / "lete" / input_name
        if not lete_path.exists():
            raise SystemExit(f"Missing {lete_path}; run fetch_sources.py first")
        build(lete_path, args.output / output_name, style, bold, plex)
    copy_licence(root / "OFL.txt", args.sources, args.output)


def copy_licence(licence: Path, sources: Path, output: Path) -> None:
    """Ship OFL.txt beside the fonts, once it is known to keep every upstream copyright line."""
    ours = " ".join(licence.read_text(encoding="utf-8").split())
    upstream = [sources / "lete" / "LICENSE.txt"]
    upstream += [sources / directory / "license.txt" for directory in PLEX_DIRS.values()]
    missing = []
    for path in upstream:
        header = path.read_text(encoding="utf-8").split("This Font Software is licensed")[0]
        for statement in re.split(r"(?=Copyright)", " ".join(header.split())):
            if statement.strip() and statement.strip() not in ours:
                missing.append(f"{path.parent.name}: {statement.strip()}")
    if missing:
        print(f"{licence.name} is missing upstream copyright lines:", *missing, sep="\n  ", file=sys.stderr)
        raise SystemExit(1)
    shutil.copyfile(licence, output / "OFL.txt")


if __name__ == "__main__":
    main()
