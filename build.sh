#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python -c "from rembg import remove; from PIL import Image; remove(Image.new('RGB', (1,1)))"
