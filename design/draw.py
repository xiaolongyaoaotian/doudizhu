from PIL import Image, ImageDraw, ImageFont
import math

S = 1024
img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角方形底：深绿毡面渐变（手动垂直插值）
grad = Image.new('RGBA', (S, S), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
top, bot = (20, 82, 62), (8, 46, 36)
for y in range(S):
    t = y / S
    c = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,)
    gd.line([(0, y), (S, y)], fill=c)
mask = Image.new('L', (S, S), 0)
md = ImageDraw.Draw(mask)
md.rounded_rectangle([0, 0, S - 1, S - 1], radius=230, fill=255)
img.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(img)

# 内侧金色描边
d.rounded_rectangle([14, 14, S - 15, S - 15], radius=218, outline=(231, 199, 102, 255), width=8)

def draw_card(base, cx, cy, w, h, angle, suit):
    card = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    cd.rounded_rectangle([0, 0, w - 1, h - 1], radius=26, fill=(255, 254, 248, 255), outline=(216, 213, 198, 255), width=3)
    if suit == 'spade':
        col = (35, 37, 43, 255)
        # 黑桃：倒三角 + 茎
        cxr, cyr = w // 2, int(h * 0.42)
        cd.polygon([(cxr, cyr - int(h * 0.20)), (cxr - int(w * 0.26), cyr + int(h * 0.10)), (cxr + int(w * 0.26), cyr + int(h * 0.10))], fill=col)
        cd.ellipse([cxr - int(w * 0.27), cyr - int(h * 0.16), cxr + int(w * 0.27), cyr + int(h * 0.18)], fill=col)
        cd.polygon([(cxr - int(w * 0.09), cyr + int(h * 0.06)), (cxr + int(w * 0.09), cyr + int(h * 0.06)), (cxr + int(w * 0.04), cyr + int(h * 0.34)), (cxr - int(w * 0.04), cyr + int(h * 0.34))], fill=col)
    else:
        col = (179, 55, 46, 255)
        # 红心：两圆 + 三角
        cxr, cyr = w // 2, int(h * 0.40)
        r = int(w * 0.19)
        cd.ellipse([cxr - 2 * r, cyr - r, cxr, cyr + r], fill=col)
        cd.ellipse([cxr, cyr - r, cxr + 2 * r, cyr + r], fill=col)
        cd.polygon([(cxr - 2 * r + 2, cyr + int(r * 0.35)), (cxr + 2 * r - 2, cyr + int(r * 0.35)), (cxr, cyr + int(h * 0.30))], fill=col)
    card = card.rotate(angle, expand=True, resample=Image.BICUBIC)
    base.alpha_composite(card, (int(cx - card.width / 2), int(cy - card.height / 2)))

CW, CH = 300, 420
# 左牌（黑桃，逆时针偏）
draw_card(img, S / 2 - 118, S / 2 - 60, CW, CH, 14, 'spade')
# 右牌（红心，顺时针偏，压在上面）
draw_card(img, S / 2 + 108, S / 2 - 40, CW, CH, -12, 'heart')

# 底部金色标题
try:
    font = ImageFont.truetype('/System/Library/Fonts/PingFang.ttc', 150, index=0)
except Exception:
    font = ImageFont.truetype('/System/Library/Fonts/Supplemental/Songti.ttc', 150)
text = '斗地主'
tb = d.textbbox((0, 0), text, font=font)
tw = tb[2] - tb[0]
# 文字阴影 + 金字
tx, ty = (S - tw) // 2, S - 268
d.text((tx + 5, ty + 6), text, font=font, fill=(0, 0, 0, 140))
d.text((tx, ty), text, font=font, fill=(255, 215, 110, 255))

img.save('/tmp/ddz-icon/icon_1024.png')
print('icon_1024.png done')
