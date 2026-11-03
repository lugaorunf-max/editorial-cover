#!/usr/bin/env python3
"""Normalize a generated cover, then optionally composite an original border."""
import argparse
from pathlib import Path
from PIL import Image, ImageOps

BORDERS = {
    'news-handdrawn': '资讯类文章（手绘边框）.png',
    'news-minimal': '资讯类文章（极简边框）.png',
    'review': '实测类文章边框.png',
}


def compose(source, output, width=1880, height=800, border=None,
            fit='cover', focus_x=0.5, focus_y=0.5):
    source, output = Path(source), Path(output)
    if width <= 0 or height <= 0 or width * 20 != height * 47:
        raise ValueError('Dimensions must be positive and exactly 2.35:1 (e.g. 1880x800)')
    if not 0 <= focus_x <= 1 or not 0 <= focus_y <= 1:
        raise ValueError('Focus coordinates must be between 0 and 1')
    if source.resolve() == output.resolve():
        raise ValueError('Use a new output path to preserve the source image')
    if output.exists():
        raise ValueError('Output already exists; choose a new output path')
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
        if fit == 'cover':
            canvas = ImageOps.fit(image, (width, height), Image.Resampling.LANCZOS,
                                  centering=(focus_x, focus_y))
        elif fit == 'contain':
            canvas = Image.new('RGBA', (width, height), 'white')
            image = ImageOps.contain(image, (width, height), Image.Resampling.LANCZOS)
            canvas.alpha_composite(image, ((width-image.width)//2, (height-image.height)//2))
        else:
            raise ValueError('fit must be cover or contain')
    if border:
        border_path = Path(__file__).resolve().parents[1] / 'assets' / 'borders' / BORDERS[border]
        with Image.open(border_path) as overlay:
            overlay = ImageOps.contain(overlay.convert('RGBA'), (width, height), Image.Resampling.LANCZOS)
            canvas.alpha_composite(overlay, ((width-overlay.width)//2, (height-overlay.height)//2))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, format='PNG')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--border', choices=BORDERS)
    parser.add_argument('--width', type=int, default=1880)
    parser.add_argument('--height', type=int, default=800)
    parser.add_argument('--fit', choices=('cover', 'contain'), default='cover')
    parser.add_argument('--focus-x', type=float, default=0.5)
    parser.add_argument('--focus-y', type=float, default=0.5)
    args = parser.parse_args()
    try:
        result = compose(args.input, args.output, args.width, args.height,
                         args.border, args.fit, args.focus_x, args.focus_y)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Error: {error}\n')
    print(result)


if __name__ == '__main__':
    main()
