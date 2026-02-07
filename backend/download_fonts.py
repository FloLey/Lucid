#!/usr/bin/env python3
"""
Font Download Script for Lucid
Downloads TTF fonts from Google Fonts GitHub repository during Docker build.
"""

import os
import urllib.request
import ssl
from pathlib import Path

# Font definitions: family name -> (repo_path, list of (filename, weight))
FONTS = {
    "Inter": {
        "repo": "rsms/inter",
        "branch": "master",
        "path": "docs/font-files",
        "source_file": "InterVariable.ttf",
        "save_as": [
            ("Inter-Regular.ttf", 400),
            ("Inter-Bold.ttf", 700),
        ],
        "files": [],
    },
    "Roboto": {
        "repo": "googlefonts/roboto",
        "branch": "main",
        "path": "src/hinted",
        "files": [
            ("Roboto-Regular.ttf", 400),
            ("Roboto-Bold.ttf", 700),
        ]
    },
    "Montserrat": {
        "repo": "JulietaUla/Montserrat",
        "branch": "master",
        "path": "fonts/ttf",
        "files": [
            ("Montserrat-Regular.ttf", 400),
            ("Montserrat-Bold.ttf", 700),
        ]
    },
    "Oswald": {
        "repo": "googlefonts/OswaldFont",
        "branch": "main",
        "path": "fonts/ttf",
        "files": [
            ("Oswald-Regular.ttf", 400),
            ("Oswald-Bold.ttf", 700),
        ]
    },
    "Playfair": {
        "repo": "technext/cozastore",
        "branch": "master",
        "path": "fonts/PlayfairDisplay",
        "files": [
            ("PlayfairDisplay-Regular.ttf", 400),
            ("PlayfairDisplay-Bold.ttf", 700),
        ]
    },
}

# Fallback URLs using Google Fonts API static CDN
FALLBACK_URLS = {
    "Inter-Regular.ttf": "https://fonts.gstatic.com/s/inter/v20/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuLyfMZg.ttf",
    "Inter-Bold.ttf": "https://fonts.gstatic.com/s/inter/v20/UcCO3FwrK3iLTeHuS_nVMrMxCp50SjIw2boKoduKmMEVuFuYMZg.ttf",
    "Roboto-Regular.ttf": "https://fonts.gstatic.com/s/roboto/v30/KFOmCnqEu92Fr1Me5Q.ttf",
    "Roboto-Bold.ttf": "https://fonts.gstatic.com/s/roboto/v30/KFOlCnqEu92Fr1MmWUlvAw.ttf",
    "Montserrat-Regular.ttf": "https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCtr6Ew-.ttf",
    "Montserrat-Bold.ttf": "https://fonts.gstatic.com/s/montserrat/v26/JTUHjIg1_i6t8kCHKm4532VJOt5-QNFgpCuM70w-.ttf",
    "Oswald-Regular.ttf": "https://fonts.gstatic.com/s/oswald/v53/TK3_WkUHHAIjg75cFRf3bXL8LICs1_FvsUZiYA.ttf",
    "Oswald-Bold.ttf": "https://fonts.gstatic.com/s/oswald/v53/TK3_WkUHHAIjg75cFRf3bXL8LICs1xZosUZiYA.ttf",
    "PlayfairDisplay-Regular.ttf": "https://fonts.gstatic.com/s/playfairdisplay/v40/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKdFvUDQ.ttf",
    "PlayfairDisplay-Bold.ttf": "https://fonts.gstatic.com/s/playfairdisplay/v40/nuFvD-vYSZviVYUb_rj3ij__anPXJzDwcbmjWBN2PKeiukDQ.ttf",
}


def download_file(url: str, dest: Path, timeout: int = 30) -> bool:
    """Download a file from URL to destination path."""
    try:
        # Create SSL context that doesn't verify (for Docker build environments)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Lucid Font Downloader)'}
        )

        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            data = response.read()
            dest.write_bytes(data)
            return True
    except Exception as e:
        print(f"  Failed to download {url}: {e}")
        return False


def download_fonts():
    """Download all fonts to the fonts directory."""
    fonts_dir = Path(__file__).parent / "fonts"
    fonts_dir.mkdir(exist_ok=True)

    print("Lucid Font Downloader")
    print("=" * 50)

    downloaded = 0
    failed = 0

    for family, config in FONTS.items():
        print(f"\n[{family}]")

        # Handle variable fonts: download one source file, save as multiple
        if "source_file" in config and "save_as" in config:
            save_targets = config["save_as"]
            all_cached = all(
                (fonts_dir / fn).exists() and (fonts_dir / fn).stat().st_size > 1000
                for fn, _ in save_targets
            )
            if all_cached:
                for fn, _ in save_targets:
                    print(f"  ✓ {fn} (cached)")
                    downloaded += 1
                continue

            source = config["source_file"]
            github_url = (
                f"https://raw.githubusercontent.com/{config['repo']}/"
                f"{config['branch']}/{config['path']}/{source}"
            )
            tmp_dest = fonts_dir / source
            print(f"  Downloading {source}...")
            ok = download_file(github_url, tmp_dest)

            if ok:
                print(f"  ✓ {source}")
                data = tmp_dest.read_bytes()
                for fn, _ in save_targets:
                    (fonts_dir / fn).write_bytes(data)
                    print(f"  ✓ {fn} (from {source})")
                    downloaded += 1
                tmp_dest.unlink()
                continue

            # Variable font download failed, try individual fallbacks
            for fn, _ in save_targets:
                if fn in FALLBACK_URLS:
                    print(f"  Trying fallback for {fn}...")
                    if download_file(FALLBACK_URLS[fn], fonts_dir / fn):
                        print(f"  ✓ {fn} (fallback)")
                        downloaded += 1
                    else:
                        print(f"  ✗ {fn} - FAILED")
                        failed += 1
                else:
                    print(f"  ✗ {fn} - FAILED")
                    failed += 1
            continue

        for filename, weight in config["files"]:
            dest = fonts_dir / filename

            # Skip if already exists
            if dest.exists() and dest.stat().st_size > 1000:
                print(f"  ✓ {filename} (cached)")
                downloaded += 1
                continue

            # Try GitHub raw URL first
            github_url = (
                f"https://raw.githubusercontent.com/{config['repo']}/"
                f"{config['branch']}/{config['path']}/{filename}"
            )

            print(f"  Downloading {filename}...")

            if download_file(github_url, dest):
                print(f"  ✓ {filename}")
                downloaded += 1
                continue

            # Try fallback URL
            if filename in FALLBACK_URLS:
                print(f"  Trying fallback URL...")
                if download_file(FALLBACK_URLS[filename], dest):
                    print(f"  ✓ {filename} (fallback)")
                    downloaded += 1
                    continue

            print(f"  ✗ {filename} - FAILED")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Downloaded: {downloaded} | Failed: {failed}")

    if failed > 0:
        print("\nWARNING: Some fonts failed to download.")
        print("The app will use system fallback fonts for missing files.")

    return failed == 0


if __name__ == "__main__":
    download_fonts()
    exit(0)
