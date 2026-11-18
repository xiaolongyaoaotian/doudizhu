from PIL import Image, ImageDraw

S = 256  # 源图（可缩到 16px）
img = Image.new('RGBA', (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 绿毡圆角底
d.rounded_rectangle([0, 0, S-1, S-1], radius=56, fill=(13, 59, 46, 255))
d.rounded_rectangle([6, 6, S-7, S-7], radius=52, outline=(231, 199, 102, 255), width=6)

# 一张竖白卡（略右倾）
card = Image.new('RGBA', (150, 210), (0, 0, 0, 0))
cd = ImageDraw.Draw(card)
cd.rounded_rectangle([0, 0, 149, 209], radius=18, fill=(255, 254, 248, 255), outline=(216, 213, 198, 255), width=3)
# 黑桃（左上角标风格放大）
cx, cy = 75, 88
cd.polygon([(cx, cy-52), (cx-42, cy+12), (cx+42, cy+12)], fill=(35, 37, 43, 255))
cd.ellipse([cx-45, cy-38, cx+45, cy+22], fill=(35, 37, 43, 255))
cd.polygon([(cx-12, cy+8), (cx+12, cy+8), (cx+5, cy+62), (cx-5, cy+62)], fill=(35, 37, 43, 255))
# 红心（右下角标）
hx, hy = 108, 168
r = 22
cd.ellipse([hx-2*r, hy-r, hx, hy+r], fill=(179, 55, 46, 255))
cd.ellipse([hx, hy-r, hx+2*r, hy+r], fill=(179, 55, 46, 255))
cd.polygon([(hx-2*r+4, hy+int(r*0.4)), (hx+2*r-4, hy+int(r*0.4)), (hx, hy+62)], fill=(179, 55, 46, 255))
card = card.rotate(8, expand=True, resample=Image.BICUBIC)
img.alpha_composite(card, (int(S/2 - card.width/2), int(S/2 - card.height/2)))

img.save('/tmp/ddz-icon/favicon-src.png')

# 多尺寸导出
for s in (48, 32, 16):
    img.resize((s, s), Image.LANCZOS).save(f'/tmp/ddz-icon/favicon-{s}.png')
apple = Image.new('RGBA', (180, 180), (13, 59, 46, 255))
ap = img.resize((176, 176), Image.LANCZOS)
apple.alpha_composite(ap, (2, 2))
apple.save('/tmp/ddz-icon/apple-touch-icon.png')
img.resize((64, 64), Image.LANCZOS).save('/tmp/ddz-icon/favicon-64.png')
print('favicon set done')

# 同步刷新游戏图标（黑桃造型修正版）
import subprocess
src = open('/tmp/ddz-icon/draw.py').read()
src = src.replace("""        if suit == 'spade':
        col = (35, 37, 43, 255)""", """        if suit == 'spade':
        col = (35, 37, 43, 255)""")
open('/tmp/ddz-icon/draw.py', 'w').write(src)
