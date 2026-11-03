#!/usr/bin/env python3
"""Normalize a generated cover, then optionally composite an original border."""
import argparse
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFilter
from statistics import median

BORDERS = {
    'news-handdrawn': '资讯类文章（手绘边框）.png',
    'news-minimal': '资讯类文章（极简边框）.png',
    'review': '实测类文章边框.png',
}


def background_color(image):
    """Use robust perimeter samples to continue a quiet source background."""
    rgb = image.convert('RGB')
    samples = []
    for i in range(20):
        x = round(i * (rgb.width - 1) / 19)
        y = round(i * (rgb.height - 1) / 19)
        samples.extend([rgb.getpixel((x, 0)), rgb.getpixel((x, rgb.height-1)),
                        rgb.getpixel((0, y)), rgb.getpixel((rgb.width-1, y))])
    return tuple(round(median(c)) for c in zip(*samples)) + (255,)


def border_opening(overlay):
    """Select the enclosed transparent opening, excluding the outer margin."""
    regions = overlay.getchannel('A').point(lambda x: 255 if x >= 128 else 0)
    center = (overlay.width//2, overlay.height//2)
    if regions.getpixel(center) != 0:
        raise ValueError('Border center must be transparent')
    ImageDraw.floodfill(regions, center, 128)
    mask = regions.point(lambda x: 255 if x == 128 else 0)
    box = mask.getbbox()
    if not box or box[0] == 0 or box[1] == 0 or box[2] == overlay.width or box[3] == overlay.height:
        raise ValueError('Border has no enclosed opening')
    return mask, box


def safe_content_box(mask, image_size):
    """Find a rectangle inside the opening, clear of badges and corner ornaments."""
    small = mask.resize((max(1, mask.width//8), max(1, mask.height//8)), Image.Resampling.BOX)
    small = small.point(lambda value: 255 if value == 255 else 0).filter(ImageFilter.MinFilter(3))
    heights = [0] * (small.width + 1)
    best_score, best = -1, None
    for y in range(small.height):
        for x in range(small.width):
            heights[x] = heights[x]+1 if small.getpixel((x,y)) else 0
        stack = []
        for x in range(small.width+1):
            start = x
            while stack and stack[-1][1] > heights[x]:
                left, height = stack.pop()
                half_width = min(small.width/2-left, x-small.width/2)
                if half_width <= 0:
                    start = left
                    continue
                centered_left = int(small.width/2-half_width)
                centered_right = int(small.width/2+half_width)
                scale = min((centered_right-centered_left)*mask.width/small.width/image_size[0],
                            height*mask.height/small.height/image_size[1])
                if scale > best_score:
                    best_score = scale
                    best = (centered_left, y-height+1, centered_right, y+1)
                start = left
            if not stack or stack[-1][1] < heights[x]:
                stack.append((start, heights[x]))
    if best is None:
        raise ValueError('Border opening is too small')
    return tuple(round(v * (mask.width/small.width if i%2 == 0 else mask.height/small.height))
                 for i,v in enumerate(best))


def fit_image(image, size, fit, background, focus_x, focus_y):
    if fit == 'cover':
        return ImageOps.fit(image, size, Image.Resampling.LANCZOS,
                            centering=(focus_x, focus_y))
    if fit != 'contain':
        raise ValueError('fit must be cover or contain')
    canvas = Image.new('RGBA', size, background)
    fitted = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, ((size[0]-fitted.width)//2, (size[1]-fitted.height)//2))
    return canvas


def compose(source, output, width=1880, height=800, border=None,
            fit=None, focus_x=0.5, focus_y=0.5, plain_output=None):
    source, output = Path(source), Path(output)
    if width <= 0 or height <= 0 or width * 20 != height * 47:
        raise ValueError('Dimensions must be positive and exactly 2.35:1 (e.g. 1880x800)')
    if not 0 <= focus_x <= 1 or not 0 <= focus_y <= 1:
        raise ValueError('Focus coordinates must be between 0 and 1')
    targets = [output] + ([Path(plain_output)] if plain_output else [])
    if len({target.resolve() for target in targets}) != len(targets):
        raise ValueError('Output paths must be different')
    for target in targets:
        if source.resolve() == target.resolve():
            raise ValueError('Use a new output path to preserve the source image')
        if target.exists():
            raise ValueError('Output already exists; choose a new output path')
    if border and border not in BORDERS:
        raise ValueError('Unknown border')
    with Image.open(source) as image:
        image = ImageOps.exif_transpose(image).convert('RGBA')
    background = background_color(image)
    plain = fit_image(image, (width, height), fit or 'cover', background, focus_x, focus_y)
    canvas = plain
    if border:
        border_path = Path(__file__).resolve().parents[1] / 'assets' / 'borders' / BORDERS[border]
        with Image.open(border_path) as original:
            resized = ImageOps.contain(original.convert('RGBA'), (width, height), Image.Resampling.LANCZOS)
        overlay = Image.new('RGBA', (width, height))
        overlay.alpha_composite(resized, ((width-resized.width)//2, (height-resized.height)//2))
        mask, _ = border_opening(overlay)
        box = safe_content_box(mask, image.size)
        # Keep artwork off the antialiased inner edge; original border pixels stay intact.
        padding = max(2, round(min(width, height) * 0.01))
        left, top, right, bottom = box
        inner_size = (right-left-2*padding, bottom-top-2*padding)
        if min(inner_size) <= 0:
            raise ValueError('Output too small for border opening')
        fitted = fit_image(image, inner_size, fit or 'contain', background, focus_x, focus_y)
        artwork = Image.new('RGBA', (width, height), background)
        artwork.alpha_composite(fitted, (left+padding, top+padding))
        canvas = Image.new('RGBA', (width, height), background)
        canvas.paste(artwork, (0, 0), mask)
        canvas.alpha_composite(overlay)
    if plain_output:
        target = Path(plain_output)
        target.parent.mkdir(parents=True, exist_ok=True)
        plain.save(target, format='PNG')
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
    parser.add_argument('--fit', choices=('cover', 'contain'), help='Default: contain inside a border, cover without a border')
    parser.add_argument('--plain-output', type=Path, help='Also save a normalized borderless copy in the same run')
    parser.add_argument('--focus-x', type=float, default=0.5)
    parser.add_argument('--focus-y', type=float, default=0.5)
    args = parser.parse_args()
    try:
        result = compose(args.input, args.output, args.width, args.height,
                         args.border, args.fit, args.focus_x, args.focus_y, args.plain_output)
    except (ValueError, OSError) as error:
        parser.exit(2, f'Error: {error}\n')
    print(result)


if __name__ == '__main__':
    main()
