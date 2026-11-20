#!/usr/bin/env python3
"""Download the upstream fonts that patch_font.py works from.

    Lete Sans Math   github.com/abccsss/LeteSansMath   (release assets)
    IBM Plex Sans    github.com/IBM/plex               (release zip, OTF files)
    IBM Plex Mono    github.com/IBM/plex               (release zip, OTF files)

By default the newest published release of each is used, so re-running this
picks up upstream updates. Pin with --lete v0.63, --plex 1.1.0 or
--plex-mono 2.5.0. Pass --lete master to take the fonts committed to Lete's
default branch before they reach a release.

Uses the standard library only. Set GITHUB_TOKEN to avoid API rate limits.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

LETE_REPO = "abccsss/LeteSansMath"
LETE_FILES = ["LeteSansMath.otf", "LeteSansMath-Bold.otf"]
LETE_LICENSE = "LICENSE.txt"
PLEX_REPO = "IBM/plex"
# Family -> (release tag prefix, zip asset, OTF file prefix). The trailing @ in
# each tag prefix keeps the -variable packages out.
PLEX_FAMILIES = {
    "IBM Plex Sans": ("@ibm/plex-sans@", "ibm-plex-sans.zip", "IBMPlexSans-"),
    "IBM Plex Mono": ("@ibm/plex-mono@", "ibm-plex-mono.zip", "IBMPlexMono-"),
}
PLEX_OTF_DIR = "fonts/complete/otf/"


def http_get(url: str, accept: str | None = None) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "micfong-sans-math"})
    if accept:
        request.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and urllib.parse.urlparse(url).hostname == "api.github.com":
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def releases(repo: str) -> list[dict]:
    """Published releases, newest first, reading every page."""
    found: list[dict] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
        batch = json.loads(http_get(url))
        found += [r for r in batch if not r["draft"]]
        if len(batch) < 100:
            break
        page += 1
    return sorted(found, key=lambda r: r["published_at"], reverse=True)


def asset_url(release: dict, name: str) -> str:
    for asset in release["assets"]:
        if asset["name"] == name:
            return asset["browser_download_url"]
    available = [a["name"] for a in release["assets"]]
    raise SystemExit(f"{release['tag_name']}: no asset {name!r}; found {available}")


def fetch_lete(selector: str, dest: Path) -> str:
    dest.mkdir(parents=True)
    if selector == "master":
        branch = json.loads(http_get(f"https://api.github.com/repos/{LETE_REPO}"))["default_branch"]
        for name in LETE_FILES:
            (dest / name).write_bytes(
                http_get(f"https://raw.githubusercontent.com/{LETE_REPO}/{branch}/{name}")
            )
        label = f"{branch} branch"
    else:
        # Upstream flags every release as a prerelease, so that flag cannot be used to filter.
        available = releases(LETE_REPO)
        if selector != "latest":
            available = [r for r in available if r["tag_name"] == selector]
        if not available:
            raise SystemExit(f"No Lete Sans Math release matches {selector!r}")
        release = available[0]
        for name in LETE_FILES:
            (dest / name).write_bytes(http_get(asset_url(release, name)))
        label = release["tag_name"]
        branch = release["tag_name"]
    (dest / LETE_LICENSE).write_bytes(
        http_get(f"https://raw.githubusercontent.com/{LETE_REPO}/{branch}/{LETE_LICENSE}")
    )
    return label


def fetch_plex(family: str, selector: str, dest: Path, published: list[dict]) -> str:
    tag_prefix, asset, file_prefix = PLEX_FAMILIES[family]
    dest.mkdir(parents=True)
    tagged = [r for r in published if r["tag_name"].startswith(tag_prefix)]
    if selector != "latest":
        tagged = [r for r in tagged if r["tag_name"] == tag_prefix + selector]
    if not tagged:
        raise SystemExit(f"No {family} release matches {selector!r}")
    release = tagged[0]
    with zipfile.ZipFile(io.BytesIO(http_get(asset_url(release, asset)))) as archive:
        for member in archive.namelist():
            # Members are written under their base name only, so a crafted path
            # inside the archive cannot escape dest.
            base = member.rsplit("/", 1)[-1]
            if PLEX_OTF_DIR in member and (
                (base.startswith(file_prefix) and base.endswith(".otf")) or base == "license.txt"
            ):
                (dest / base).write_bytes(archive.read(member))
    if not any(dest.glob("*.otf")):
        raise SystemExit(f"{release['tag_name']}: no OTF files found under {PLEX_OTF_DIR}")
    return release["tag_name"]


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lete", default="latest", help="latest (default), a tag such as v0.63, or master")
    parser.add_argument("--plex", default="latest", help="Plex Sans: latest (default) or a version such as 1.1.0")
    parser.add_argument("--plex-mono", default="latest", help="Plex Mono: latest (default) or a version such as 2.5.0")
    parser.add_argument("--dest", type=Path, default=root / "build" / "sources")
    args = parser.parse_args()

    # Download next to the destination and swap it in at the end, so a failed
    # download leaves the previous sources in place.
    staging = args.dest.with_name(args.dest.name + ".partial")
    if staging.exists():
        shutil.rmtree(staging)
    lete = fetch_lete(args.lete, staging / "lete")
    published = releases(PLEX_REPO)
    # Separate directories: both zips ship a license.txt.
    plex = fetch_plex("IBM Plex Sans", args.plex, staging / "plex", published)
    plex_mono = fetch_plex("IBM Plex Mono", args.plex_mono, staging / "plex-mono", published)
    manifest = {"lete": lete, "plex": plex, "plex_mono": plex_mono}
    (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    if args.dest.exists():
        shutil.rmtree(args.dest)
    staging.rename(args.dest)
    print(f"Lete Sans Math: {lete}\nIBM Plex Sans:  {plex}\nIBM Plex Mono:  {plex_mono}\nSaved to {args.dest}")


if __name__ == "__main__":
    main()
