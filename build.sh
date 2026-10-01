#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# ReportLab does not ship with an Arabic font. Download Noto Sans Arabic
# during the build so Arabic glyphs are embedded in generated PDFs on Linux.
FONT_DIR="static/fonts"
FONT_FILE="$FONT_DIR/NotoSansArabic-Regular.ttf"
mkdir -p "$FONT_DIR"

python - <<'PY'
from pathlib import Path
from urllib.request import urlopen

font_path = Path('static/fonts/NotoSansArabic-Regular.ttf')
url = 'https://github.com/notofonts/noto-fonts/raw/refs/heads/main/hinted/ttf/NotoSansArabic/NotoSansArabic-Regular.ttf'

if not font_path.exists() or font_path.stat().st_size < 100_000:
    print('Downloading Noto Sans Arabic font...')
    with urlopen(url, timeout=60) as response:
        data = response.read()
    if len(data) < 100_000:
        raise RuntimeError('Downloaded Arabic font is unexpectedly small.')
    font_path.write_bytes(data)

print(f'Arabic font ready: {font_path} ({font_path.stat().st_size} bytes)')
PY

python manage.py collectstatic --no-input
python manage.py migrate
