#!/usr/bin/env python3
"""Download remote images referenced in `index.html` and create WebP variants.

Behavior:
- Parse `index.html` for `<img>` tags and their `srcset` / `src` / `onerror` attributes.
- For each referenced local `assets/media/*-<width>.webp` file that is missing,
  try to find a remote fallback URL in the same tag (commonly in `onerror`).
- Download the remote image and generate WebP files at widths: 480, 800, 1200
  using Pillow. Save files to `assets/media/` with the same filenames used
  in `index.html` (e.g. `unsplash-1522202176988-800.webp`).

This script is conservative: it only creates files for local paths already
referenced in `index.html` when they're missing and a remote fallback URL is
findable in the tag.
"""

import os
import re
import sys
import hashlib
from pathlib import Path
from io import BytesIO

try:
    import requests
    from PIL import Image
    from bs4 import BeautifulSoup
except Exception as e:
    print("Missing dependencies. Please install from requirements.txt:")
    print("  python3 -m pip install -r requirements.txt")
    raise


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = WORKSPACE_ROOT / "index.html"
ASSETS_MEDIA = WORKSPACE_ROOT / "assets" / "media"
ASSETS_MEDIA.mkdir(parents=True, exist_ok=True)

TARGET_WIDTHS = [480, 800, 1200]
DEFAULT_QUALITY = 80


def safe_filename_from_url(url: str) -> str:
    # Create a short, reproducible name using an md5 of the URL plus last path part
    last = url.split("/")[-1].split("?")[0]
    h = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    if last:
        return f"{Path(last).stem}-{h}"
    return h


def download_image(url: str) -> BytesIO:
    print(f"Downloading: {url}")
    resp = requests.get(url, stream=True, timeout=30)
    resp.raise_for_status()
    bio = BytesIO(resp.content)
    return bio


def convert_and_save(img_bytes: BytesIO, target_base: str, widths=TARGET_WIDTHS, quality=DEFAULT_QUALITY):
    img_bytes.seek(0)
    with Image.open(img_bytes) as img:
        img = img.convert("RGB")
        for w in widths:
            ratio = w / img.width
            new_h = max(1, int(img.height * ratio))
            resized = img.resize((w, new_h), Image.LANCZOS)
            filename = f"{target_base}-{w}.webp"
            out_path = ASSETS_MEDIA / filename
            resized.save(out_path, "WEBP", quality=quality, method=6)
            print(f"  wrote {out_path} ({w}w)")


def extract_remote_from_onerror(onerror: str) -> str | None:
    if not onerror:
        return None
    # common pattern: this.onerror=null;this.src='https://...'
    m = re.search(r"https?://[\w\-./?&=%#:]+", onerror)
    if m:
        return m.group(0)
    return None


def process_index():
    if not INDEX_PATH.exists():
        print(f"Cannot find {INDEX_PATH}")
        sys.exit(1)

    html = INDEX_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    imgs = soup.find_all("img")
    created = 0
    skipped = 0

    for img in imgs:
        src = img.get("src") or ""
        srcset = img.get("srcset") or ""
        onerror = img.get("onerror") or ""

        # 1) If srcset contains local assets/media references, prefer those filenames
        candidates = []
        for part in re.split(r",\s*", srcset):
            if not part:
                continue
            # part like: assets/media/unsplash-...-480.webp 480w
            path_match = re.search(r"(assets/media/[\w\-_.]+)\s*\d*w?", part)
            if path_match:
                candidates.append(path_match.group(1))

        # 2) If no srcset candidates, check if src is a local assets/media path
        if not candidates and src.startswith("assets/media/"):
            # derive a base name (may be *-800.webp); we'll create all sizes
            candidates.append(src)

        # For each candidate local path, check existence and try to recover
        for local_path in candidates:
            local_full = WORKSPACE_ROOT / local_path
            # Determine the base name without the -<width>.webp suffix
            m = re.match(r"assets/media/(.+?)-(?:\d+)\.webp$", local_path)
            if m:
                base = m.group(1)
            else:
                # fallback: strip extension
                base = Path(local_path).stem

            # Check for each target width if file already exists
            need_any = False
            missing_widths = []
            for w in TARGET_WIDTHS:
                expected = ASSETS_MEDIA / f"{base}-{w}.webp"
                if not expected.exists():
                    need_any = True
                    missing_widths.append(w)

            if not need_any:
                skipped += 1
                continue

            # find remote URL: prefer onerror fallback, otherwise maybe src (if http)
            remote = extract_remote_from_onerror(onerror)
            if not remote and src and src.startswith("http"):
                remote = src

            if not remote:
                print(f"Skipping {local_path}: no remote fallback found in tag")
                skipped += 1
                continue

            try:
                b = download_image(remote)
                # convert and save using the same base name
                convert_and_save(b, base)
                created += 1
            except Exception as exc:
                print(f"Failed to download/convert {remote}: {exc}")
                skipped += 1

    print(f"Done. Created: {created}, Skipped: {skipped}")


if __name__ == "__main__":
    process_index()
