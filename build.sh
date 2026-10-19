#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Download Noto Sans Arabic at build time; do not commit font files to GitHub.
FONT_DIR="static/fonts"
mkdir -p "$FONT_DIR"
python - <<'PY'
from pathlib import Path
from urllib.request import urlopen

font_dir = Path('static/fonts')
for weight in ('Regular', 'Bold'):
    font_path = font_dir / f'NotoSansArabic-{weight}.ttf'
    url = f'https://github.com/notofonts/noto-fonts/raw/refs/heads/main/hinted/ttf/NotoSansArabic/NotoSansArabic-{weight}.ttf'
    if not font_path.exists() or font_path.stat().st_size < 100_000:
        print(f'Downloading Noto Sans Arabic {weight} font...')
        with urlopen(url, timeout=60) as response:
            data = response.read()
        if len(data) < 100_000:
            raise RuntimeError(f'Downloaded Arabic font is unexpectedly small: {font_path}')
        font_path.write_bytes(data)
    print(f'Arabic font ready: {font_path} ({font_path.stat().st_size} bytes)')
PY

python manage.py collectstatic --no-input
python manage.py migrate
