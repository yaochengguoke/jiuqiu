"""检查HTML中图片匹配是否正确"""
import re, os, glob

# 找最新的输出目录
dirs = sorted(glob.glob('outputs/芯光*/'), reverse=True)
if not dirs:
    print('No output found')
    exit()
latest = dirs[0]
html_path = latest + 'final_plan.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 分离图片和占位符
imgs = re.findall(r'alt="([^"]+)"', html)
phs = re.findall(r'figure-placeholder[^>]*>.*?\[Chart\] ([^<]+)<', html)

print(f'嵌入 {len(imgs)} 张:')
for i, img in enumerate(imgs, 1):
    print(f'  {i}. {img}')

print(f'占位 {len(phs)} 个:')
for i, ph in enumerate(phs, 1):
    print(f'  {i}. {ph}')

# 写入验证文件
with open('outputs/current/image_check.txt', 'w', encoding='utf-8') as f:
    f.write(f'嵌入: {imgs}\n占位: {phs}\n')
print('\nOK - check outputs/current/image_check.txt')
