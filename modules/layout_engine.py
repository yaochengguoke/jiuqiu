"""
模块7：排版美化引擎
- 套用视觉风格参数（配色/字体/间距/页边距）
- Markdown → HTML 转换（带完整CSS样式）
- 全文统一格式、图文对齐
- 支持4套风格滤镜一键切换
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VISUAL_DIR, OUTPUT_DIR, SUPPORTED_THEMES
from utils.helpers import ensure_dir, write_text_file


class LayoutEngine:
    """
    排版美化引擎

    职责：
    1. 将Markdown内容转换为带CSS样式的HTML
    2. 套用视觉风格配置（来自L3视觉参数库）
    3. 图文对齐、封面、页眉页脚统一
    4. 支持多种风格滤镜切换
    """

    def __init__(self, visual_style: Dict[str, Any]):
        """
        Args:
            visual_style: 视觉风格配置字典
        """
        self.style = visual_style
        self.colors = visual_style.get("colors", {})
        self.typography = visual_style.get("typography", {})
        self.layout_config = visual_style.get("layout", {})
        self.table_style = visual_style.get("table_style", {})

    @classmethod
    def from_style_name(cls, style_name: str) -> "LayoutEngine":
        """根据风格名称创建引擎"""
        style_files = {
            "deep_blue": "visual_deep_blue.json",
            "dark_tech": "visual_dark_tech.json",
            "academic_red": "visual_academic_red.json",
            "fresh_green": "visual_fresh_green.json",
        }

        filename = style_files.get(style_name, "visual_deep_blue.json")
        filepath = VISUAL_DIR / filename

        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                style_data = json.load(f)
        else:
            # 默认深蓝风格
            with open(VISUAL_DIR / "visual_deep_blue.json", "r", encoding="utf-8") as f:
                style_data = json.load(f)

        return cls(style_data)

    def render_html(
        self,
        markdown_content: str,
        project_name: str,
        competition_name: str,
        image_dir: str = None,
    ) -> str:
        """
        将Markdown内容渲染为HTML文档，自动嵌入图片

        Args:
            markdown_content: Markdown格式的完整策划书
            project_name: 项目名称
            competition_name: 赛事名称
            image_dir: 图片目录路径，用于自动嵌入生成的图表

        Returns:
            完整的HTML文档字符串
        """
        body_html = self._markdown_to_html(markdown_content, image_dir=image_dir)
        html = self._build_html_document(
            body=body_html,
            project_name=project_name,
            competition_name=competition_name,
        )
        return html

    def render_pdf_ready_html(
        self,
        markdown_content: str,
        project_name: str,
        competition_name: str,
    ) -> str:
        """渲染为PDF就绪的HTML（带分页控制）"""
        body_html = self._markdown_to_html(markdown_content)

        # PDF特有样式：分页控制
        html = self._build_html_document(
            body=body_html,
            project_name=project_name,
            competition_name=competition_name,
            extra_css=self._get_pdf_css(),
        )

        return html

    def generate_css(self) -> str:
        """生成完整的CSS样式表"""
        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")
        secondary = self.colors.get("secondary", "#1E5A99")
        accent = self.colors.get("accent", "#FF6B35")
        bg = self.colors.get("background", "#F5F7FA")
        text_primary = self.colors.get("text_primary", "#1A1A2E")
        text_secondary = self.colors.get("text_secondary", "#4A5568")
        border_light = self.colors.get("border_light", "#E2E8F0")
        table_header_bg = self.colors.get("table_header_bg", "#0A2F5A")
        table_header_text = self.colors.get("table_header_text", "#FFFFFF")

        chapter_title = self.typography.get("chapter_title", {})
        section_title = self.typography.get("section_title", {})
        body_text = self.typography.get("body_text", {})

        body_font = body_text.get("font", "微软雅黑")
        body_size = body_text.get("size", "12pt")
        body_line_height = body_text.get("line_height", 1.5)
        body_color = body_text.get("color", "#1A1A2E")

        margin_top = self.layout_config.get("page_margin_top", "3.5cm")
        margin_bottom = self.layout_config.get("page_margin_bottom", "3.2cm")
        margin_left = self.layout_config.get("page_margin_left", "3.2cm")
        margin_right = self.layout_config.get("page_margin_right", "3.2cm")

        css = f"""
/* ===== 全自动竞赛策划智能体 - 自动生成样式表 ===== */
/* 风格：{self.style.get('name', '默认')} */

@page {{
    size: A4;
    margin-top: {margin_top};
    margin-bottom: {margin_bottom};
    margin-left: {margin_left};
    margin-right: {margin_right};

    @top-center {{
        content: "{self.layout_config.get('header_content', '{project_name}')}";
        font-family: "{body_font}";
        font-size: 9pt;
        color: #A0AEC0;
    }}

    @bottom-center {{
        content: counter(page);
        font-family: "{body_font}";
        font-size: 9pt;
        color: #A0AEC0;
    }}
}}

body {{
    font-family: "{body_font}", -apple-system, sans-serif;
    font-size: {body_size};
    line-height: {body_line_height};
    color: {body_color};
    background: white;
    max-width: 100%;
}}

/* 封面样式 */
.cover-page {{
    background: linear-gradient(135deg, {primary}, {primary_light});
    color: white;
    text-align: center;
    padding: 4cm 2cm;
    break-after: page;
}}

.cover-page h1 {{
    font-family: "{chapter_title.get('font', '黑体')}";
    font-size: {chapter_title.get('size', '32pt')};
    color: white;
    margin-bottom: 1.5cm;
}}

.cover-page .subtitle {{
    font-size: 18pt;
    color: {border_light};
    margin-bottom: 2cm;
}}

.cover-page .competition {{
    font-size: 22pt;
    color: {primary_light};
    font-weight: bold;
    margin-bottom: 2.5cm;
}}

.cover-page .meta {{
    font-size: 11pt;
    color: #8899AA;
    position: absolute;
    bottom: 2cm;
    width: 100%;
}}

/* 目录样式 */
.toc {{
    break-after: page;
    padding: 2cm 0;
}}

.toc h2 {{
    font-family: "{chapter_title.get('font', '黑体')}";
    color: {primary};
    font-size: 24pt;
    text-align: center;
    margin-bottom: 1.5cm;
    padding-bottom: 0.5cm;
    border-bottom: 3px solid {primary};
}}

.toc-item {{
    display: flex;
    justify-content: space-between;
    padding: 0.3cm 0;
    font-size: 11pt;
    border-bottom: 1px dotted {border_light};
}}

.toc-item.chapter {{
    font-weight: bold;
    color: {primary};
    font-size: 12pt;
}}

/* 章节标题 */
h2 {{
    font-family: "{chapter_title.get('font', '黑体')}";
    color: {primary};
    font-size: {chapter_title.get('size', '22pt')};
    text-align: {chapter_title.get('align', 'center')};
    margin-top: 1cm;
    margin-bottom: 0.8cm;
    padding-bottom: 0.3cm;
    border-bottom: 2px solid {primary};
    break-before: page;
}}

h3 {{
    font-family: "{section_title.get('font', '黑体')}";
    color: {secondary};
    font-size: {section_title.get('size', '16pt')};
    text-align: left;
    margin-top: 0.8cm;
    margin-bottom: 0.4cm;
    padding-left: 0.3cm;
    border-left: 4px solid {primary_light};
}}

h4 {{
    font-family: "{section_title.get('font', '黑体')}";
    color: {primary_light};
    font-size: 14pt;
    margin-top: 0.5cm;
    margin-bottom: 0.3cm;
}}

/* 段落 */
p {{
    text-indent: 2em;
    margin-bottom: 0.3cm;
    text-align: justify;
}}

/* 加粗 */
strong {{
    color: {primary};
}}

/* 引用块 */
blockquote {{
    background: {bg};
    border-left: 4px solid {primary_light};
    margin: 0.5cm 0;
    padding: 0.5cm 1cm;
    color: {text_secondary};
    font-style: italic;
}}

blockquote p {{
    text-indent: 0;
}}

/* 表格 */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 0.5cm 0;
    font-size: 10pt;
}}

thead th {{
    background-color: {table_header_bg};
    color: {table_header_text};
    padding: 8px 12px;
    text-align: center;
    font-weight: bold;
    border: 1px solid {table_header_bg};
}}

tbody td {{
    padding: 6px 10px;
    border: 1px solid {border_light};
    text-align: center;
}}

tbody tr:nth-child(even) {{
    background-color: {bg};
}}

/* 列表 */
ul, ol {{
    margin: 0.3cm 0;
    padding-left: 1.5cm;
}}

li {{
    margin-bottom: 0.15cm;
}}

/* 图片 */
img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 0.5cm auto;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

.figure-caption {{
    text-align: center;
    font-size: 9pt;
    color: {text_secondary};
    margin-top: 0.1cm;
}}

/* 待补充标记 */
.missing-marker {{
    display: inline-block;
    background: #FFF3CD;
    border: 1px solid #FFC107;
    color: #856404;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 10pt;
}}

/* 数据来源 */
.data-source {{
    font-size: 8pt;
    color: #A0AEC0;
    font-style: italic;
}}

/* 页眉页脚 */
.header {{
    font-family: "{self.typography.get('header_footer', {}).get('font', '微软雅黑')}";
    font-size: 9pt;
    color: #A0AEC0;
    text-align: center;
}}

.footer {{
    font-family: "{self.typography.get('header_footer', {}).get('font', '微软雅黑')}";
    font-size: 9pt;
    color: #A0AEC0;
    text-align: center;
}}

/* 装饰元素 */
.accent-bar {{
    width: 100%;
    height: 4px;
    background: linear-gradient(90deg, {primary}, {primary_light}, transparent);
    margin: 0.3cm 0 0.8cm 0;
}}

.accent-dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    background: {accent};
    border-radius: 50%;
    margin-right: 8px;
}}
"""
        return css

    def _build_html_document(
        self,
        body: str,
        project_name: str,
        competition_name: str,
        extra_css: str = "",
    ) -> str:
        """构建完整的HTML文档"""
        css = self.generate_css() + "\n" + extra_css

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="generator" content="全自动竞赛策划智能体">
    <meta name="project" content="{project_name}">
    <meta name="competition" content="{competition_name}">
    <title>{project_name} - 竞赛策划书</title>
    <style>
{css}
    </style>
</head>
<body>

{body}

<footer class="footer">
    <hr>
    <p style="text-align:center; color:#A0AEC0; font-size:9pt;">
        {project_name} | {competition_name} | 由全自动竞赛策划智能体生成 | {datetime.now().strftime('%Y-%m-%d')}
    </p>
</footer>

</body>
</html>"""
        return html

    def _markdown_to_html(self, md_text: str, image_dir: str = None) -> str:
        """简易Markdown→HTML转换，支持自动嵌入图片"""
        import base64
        from pathlib import Path

        # 预建图片索引
        image_index = {}
        if image_dir:
            img_path = Path(image_dir)
            if img_path.exists():
                for f in img_path.glob("*.png"):
                    image_index[f.stem.lower()] = f

        lines = md_text.split('\n')
        html_lines = []
        in_table = False
        in_list = False
        table_rows = []

        for line in lines:
            stripped = line.strip()

            # 空行
            if not stripped:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                if in_table:
                    html_lines.append('</tbody></table>')
                    in_table = False
                html_lines.append('')
                continue

            # 标题
            if stripped.startswith('# '):
                html_lines.append(f'<h1 class="cover-title">{stripped[2:]}</h1>')
            elif stripped.startswith('## '):
                html_lines.append(f'<h2>{stripped[3:]}</h2>')
                html_lines.append('<div class="accent-bar"></div>')
            elif stripped.startswith('### '):
                html_lines.append(f'<h3>{stripped[4:]}</h3>')
            elif stripped.startswith('#### '):
                html_lines.append(f'<h4>{stripped[5:]}</h4>')

            # 水平线
            elif stripped == '---':
                html_lines.append('<hr>')

            # 引用
            elif stripped.startswith('> '):
                html_lines.append(f'<blockquote><p>{stripped[2:]}</p></blockquote>')

            # 表格
            elif '|' in stripped and stripped.startswith('|'):
                if not in_table:
                    html_lines.append('<table><thead>')
                    in_table = True
                    table_rows = []

                if stripped.replace('|', '').replace('-', '').replace(' ', '').strip() == '':
                    # 分隔行，跳过
                    if table_rows:
                        html_lines.append('<tr>' + ''.join(
                            f'<th>{cell.strip()}</th>' for cell in table_rows[-1].split('|')[1:-1]
                        ) + '</tr>')
                        html_lines.append('</thead><tbody>')
                    table_rows = []
                    continue

                table_rows.append(stripped)

            elif in_table and table_rows:
                html_lines.append('<tr>' + ''.join(
                    f'<td>{cell.strip()}</td>' for cell in stripped.split('|')[1:-1]
                ) + '</tr>')

            # 无序列表
            elif stripped.startswith('- ') or stripped.startswith('* '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                content = stripped[2:]
                # 处理加粗
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                html_lines.append(f'<li>{content}</li>')

            # 有序列表
            elif re.match(r'^\d+\.\s', stripped):
                if not in_list:
                    html_lines.append('<ol>')
                    in_list = True
                content = re.sub(r'^\d+\.\s', '', stripped)
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
                html_lines.append(f'<li>{content}</li>')

            # 图片占位 → 自动匹配嵌入真实图片
            elif stripped.startswith('【此处插入：') and stripped.endswith('】'):
                img_desc = stripped[6:-1]
                matched_img = None

                # 在图片索引中搜索匹配
                if image_dir and image_index:
                    keywords = {
                        "封面": ["cover"],
                        "架构": ["arch"],
                        "流程": ["flow"],
                        "新闻": ["news"],
                        "配图": ["news"],
                        "画布": ["biz", "canvas"],
                        "商业": ["biz", "canvas"],
                        "路线": ["timeline"],
                        "时间轴": ["timeline"],
                        "雷达": ["news"],
                    }
                    for kw, patterns in keywords.items():
                        if kw in img_desc:
                            for p in patterns:
                                for stem, path in image_index.items():
                                    if p in stem:
                                        matched_img = path
                                        break
                                if matched_img:
                                    break
                        if matched_img:
                            break

                if matched_img:
                    with open(matched_img, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode()
                    ext = matched_img.suffix.lower().replace(".", "")
                    html_lines.append(
                        f'<div class="figure-container" style="text-align:center; margin:0.8cm 0;">'
                        f'<img src="data:image/{ext};base64,{b64}" '
                        f'style="max-width:100%; height:auto; border-radius:6px; '
                        f'box-shadow:0 4px 16px rgba(0,0,0,0.1);" '
                        f'alt="{img_desc}">'
                        f'<p class="figure-caption">图：{img_desc}</p>'
                        f'</div>'
                    )
                else:
                    html_lines.append(
                        f'<div class="figure-placeholder" style="border:2px dashed {self.colors.get("border_light", "#ddd")}; '
                        f'padding:1cm; text-align:center; margin:0.5cm 0; border-radius:8px;">'
                        f'<p style="color:{self.colors.get("text_secondary", "#888")}; font-size:10pt;">[Chart] {img_desc}</p>'
                        f'</div>'
                    )

            # 待补充标记
            elif '【待补充' in stripped:
                content = re.sub(
                    r'(【待补充[：:][^】]+】)',
                    r'<span class="missing-marker">\1</span>',
                    stripped
                )
                html_lines.append(f'<p>{content}</p>')

            # 数据来源
            elif '【来源' in stripped:
                content = re.sub(
                    r'(【来源[：:][^】]+】)',
                    r'<span class="data-source">\1</span>',
                    stripped
                )
                html_lines.append(f'<p>{content}</p>')

            # 普通段落
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', stripped)
                html_lines.append(f'<p>{content}</p>')

        # 关闭未闭合的标签
        if in_list:
            html_lines.append('</ul>')
        if in_table:
            html_lines.append('</tbody></table>')

        return '\n'.join(html_lines)

    def _get_pdf_css(self) -> str:
        """PDF专用CSS（分页控制）"""
        return """
        @media print {
            h2 {
                break-before: page;
            }

            .cover-page {
                break-after: page;
            }

            .toc {
                break-after: page;
            }

            img {
                max-height: 15cm;
                object-fit: contain;
            }

            .no-break {
                break-inside: avoid;
            }

            @page {
                @footnotes {
                    margin-top: 1cm;
                }
            }
        }
        """

    def save_html(self, html_content: str, output_path: Path) -> Path:
        """保存HTML文件"""
        ensure_dir(output_path.parent)
        write_text_file(output_path, html_content)
        return output_path
