#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Pre-download the rembg model to prevent timeout on first run
python -c "from rembg import remove; from PIL import Image; remove(Image.new('RGB', (1,1)))"
