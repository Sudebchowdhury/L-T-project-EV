"""Creates icon.ico (teal rounded square with three bars). Run once."""
from PIL import Image, ImageDraw

size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, size - 8, size - 8), radius=52, fill="#0F766E")
for i, (h, c) in enumerate(((120, "#FFFFFF"), (90, "#FFFFFF"), (60, "#86EFAC"))):
    x = 52 + i * 60
    d.rounded_rectangle((x, 200 - h, x + 40, 200), radius=8, fill=c)
img.save("icon.ico", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
