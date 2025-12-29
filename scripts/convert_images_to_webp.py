"""
Simple image conversion script: JPG/PNG -> WebP using Pillow.
Run:
  python3 -m pip install --user pillow
  python3 scripts/convert_images_to_webp.py assets/media --quality 80

This script will create .webp copies alongside originals with same base name.
"""
import sys
from pathlib import Path
try:
    from PIL import Image
except Exception as e:
    print("Pillow not installed. Run: python3 -m pip install --user pillow")
    sys.exit(1)

def convert_folder(folder: Path, quality: int = 80):
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return
    exts = ('.jpg', '.jpeg', '.png')
    for p in folder.rglob('*'):
        if p.suffix.lower() in exts:
            out = p.with_suffix('.webp')
            try:
                img = Image.open(p).convert('RGB')
                img.save(out, 'WEBP', quality=quality)
                print(f"Saved: {out}")
            except Exception as err:
                print(f"Failed {p}: {err}")

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', nargs='?', default='assets/media')
    ap.add_argument('--quality', type=int, default=80)
    args = ap.parse_args()
    convert_folder(Path(args.folder), args.quality)
