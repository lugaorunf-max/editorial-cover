import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('compose_cover', ROOT/'scripts/compose_cover.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CompositionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory/'source.png'
        image = Image.new('RGB', (1880,800), '#eee1cd')
        draw = ImageDraw.Draw(image)
        draw.rectangle((0,0,1879,799), outline='red', width=30)
        draw.rectangle((700,200,1180,600), fill='#1234ab')
        image.save(self.source)

    def test_all_borders_keep_art_inside_and_save_plain(self):
        for name, filename in m.BORDERS.items():
            with self.subTest(border=name):
                output, plain = self.directory/(name+'.png'), self.directory/(name+'-plain.png')
                m.compose(self.source, output, border=name, plain_output=plain)
                result = Image.open(output)
                self.assertEqual(result.size, (1880,800))
                self.assertEqual(Image.open(plain).convert('RGB').tobytes(), Image.open(self.source).tobytes())
                # Visible source edge markers remain after cover cropping.
                self.assertGreater(sum(1 for r,g,b,a in result.getdata() if r>230 and g<40 and b<40), 1000)
                overlay = m.prepare_border(Image.open(ROOT/'assets/borders'/filename),1880,800)
                mask, box = m.border_opening(overlay)
                expected = Image.new('RGBA',(1880,800),'white')
                expected.alpha_composite(overlay)
                # No artwork outside the inner opening, including transparent outer margins.
                exterior = mask.point(lambda value:255-value)
                self.assertEqual(Image.composite(result, expected, exterior).tobytes(), expected.tobytes())
                # Completely opaque frame and badge pixels are unchanged.
                opaque = overlay.getchannel('A').point(lambda value:255 if value==255 else 0)
                self.assertEqual(Image.composite(result, overlay, opaque).tobytes(), overlay.tobytes())

    def test_default_fills_opening_without_added_side_bands(self):
        # A contrasting center and background reveal any newly introduced padding.
        image = Image.new('RGB', (1880,800), '#1234ab')
        ImageDraw.Draw(image).rectangle((0,0,1879,799), outline='#eee1cd', width=1)
        image.save(self.source)
        for name, filename in m.BORDERS.items():
            output = self.directory/(name+'-filled.png')
            m.compose(self.source, output, border=name)
            result = Image.open(output)
            overlay = m.prepare_border(Image.open(ROOT/'assets/borders'/filename),1880,800)
            mask, box = m.border_opening(overlay)
            left, top, right, bottom = box
            expected = Image.new('RGBA',(1880,800),'#1234ab')
            expected.alpha_composite(overlay)
            for x in (left+10, right-11):
                point = (x, (top+bottom)//2)
                self.assertEqual(mask.getpixel(point), 255)
                self.assertEqual(result.getpixel(point), expected.getpixel(point))

    def test_colored_artwork_leaves_transparent_exterior_white(self):
        for color in ('#ed2b7b', '#2266cc', '#1f8a49'):
            Image.new('RGB',(1880,800),color).save(self.source)
            output = self.directory/(color[1:]+'.png')
            m.compose(self.source,output)
            result = Image.open(output)
            overlay = m.prepare_border(Image.open(ROOT/'assets/borders'/m.BORDERS['news-handdrawn']),1880,800)
            mask, _ = m.border_opening(overlay)
            # Transparent pixels outside the frame must be exactly white.
            count = 0
            for y in range(0,800,7):
                for x in range(0,1880,7):
                    if mask.getpixel((x,y)) == 0 and overlay.getpixel((x,y))[3] == 0:
                        self.assertEqual(result.getpixel((x,y)),(255,255,255,255))
                        count += 1
            self.assertGreater(count,100)
            self.assertEqual(result.getpixel((940,400)),Image.new('RGBA',(1,1),color).getpixel((0,0)))

    def test_outer_margins_are_tight_without_losing_badge(self):
        for filename in m.BORDERS.values():
            original = Image.open(ROOT/'assets/borders'/filename)
            overlay = m.prepare_border(original,1880,800)
            bounds = overlay.getchannel('A').point(lambda value:255 if value>=128 else 0).getbbox()
            self.assertEqual(overlay.size,(1880,800))
            self.assertLessEqual(bounds[0],6)
            self.assertLessEqual(bounds[1],6)
            self.assertLessEqual(1880-bounds[2],6)
            self.assertLessEqual(800-bounds[3],6)

    def test_rejects_overwrite_before_writing_either_output(self):
        output = self.directory/'output.png'
        with self.assertRaises(ValueError):
            m.compose(self.source, output, border='news-handdrawn', plain_output=self.source)
        self.assertFalse(output.exists())
        with self.assertRaises(ValueError):
            m.compose(self.source, output, plain_output=output)
        with self.assertRaises(ValueError):
            m.compose(self.source, output, width=100, height=100)


if __name__ == '__main__':
    unittest.main()
