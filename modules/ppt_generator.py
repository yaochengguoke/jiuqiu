"""
答辩PPT生成模块 + 竞品对标分析
- 从策划书内容自动生成答辩PPT
- 提取竞品数据生成对比表格
"""

import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class CompetitorInfo:
    name: str
    market_share: str = ""
    strengths: List[str] = None
    weaknesses: List[str] = None
    key_params: Dict[str, str] = None


class PPTGenerator:
    """答辩PPT生成器"""

    # 幻灯片配色
    COLORS = {
        "primary": "0A2F5A",
        "accent": "FF6B35",
        "white": "FFFFFF",
        "light_bg": "F5F7FA",
        "dark_text": "1A1A2E",
        "gray_text": "4A5568",
    }

    def __init__(self):
        self.slides_data = []

    def generate_ppt(self, full_text: str, project_name: str, output_path: Path) -> Path:
        """生成答辩PPT"""
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt, Emu
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN
        except ImportError:
            print("[PPT] python-pptx 未安装")
            return None

        prs = Presentation()
        prs.slide_width = Inches(13.333)  # 16:9
        prs.slide_height = Inches(7.5)

        # 提取章节内容
        chapters = {}
        current = None
        for line in full_text.split('\n'):
            if line.startswith('## '):
                current = line[3:].strip()
                chapters[current] = []
            elif current and line.startswith('### '):
                chapters[current].append(('h3', line[4:].strip()))
            elif current:
                chapters[current].append(('p', line.strip()))

        # Slide 1: 封面
        self._add_cover_slide(prs, project_name)
        # Slide 2: 目录
        self._add_toc_slide(prs, list(chapters.keys()))
        # Slide 3+: 每章一页
        for title, content in chapters.items():
            if title in ["执行摘要", "作品摘要"]:
                self._add_summary_slide(prs, title, content)
            else:
                self._add_content_slide(prs, title, content)
        # 最后: 致谢
        self._add_thanks_slide(prs)

        prs.save(str(output_path))
        return output_path

    def _add_cover_slide(self, prs, project_name):
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)

        # Title
        txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(2))
        tf = txBox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = project_name
        p.font.size = Pt(40)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER

        # Subtitle
        txBox2 = slide.shapes.add_textbox(Inches(1), Inches(4.5), Inches(11), Inches(1))
        tf2 = txBox2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = "竞赛答辩汇报"
        p2.font.size = Pt(24)
        p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35)
        p2.alignment = PP_ALIGN.CENTER

    def _add_toc_slide(self, prs, chapters):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        txBox = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(11), Inches(0.8))
        p = txBox.text_frame.paragraphs[0]
        p.text = "汇报目录"
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
        p.alignment = PP_ALIGN.LEFT

        txBox2 = slide.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10), Inches(5))
        tf = txBox2.text_frame
        for i, ch in enumerate(chapters[:8], 1):
            p = tf.add_paragraph()
            p.text = f"{i:02d}  {ch}"
            p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(0x1A, 0x1A, 0x2E)
            p.space_after = Pt(12)

    def _add_summary_slide(self, prs, title, content):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Title bar
        shape = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
        shape.line.fill.background()
        tf = shape.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.LEFT

        # Key points
        txBox = slide.shapes.add_textbox(Inches(1), Inches(1.8), Inches(11), Inches(5))
        tf2 = txBox.text_frame
        tf2.word_wrap = True
        for item_type, text in content[:8]:
            if item_type == 'h3':
                p = tf2.add_paragraph()
                p.text = f"▸ {text}"
                p.font.size = Pt(16)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
                p.space_after = Pt(6)
            elif item_type == 'p' and text.strip() and len(text) > 20:
                p = tf2.add_paragraph()
                p.text = text[:120]
                p.font.size = Pt(12)
                p.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
                p.space_after = Pt(8)

    def _add_content_slide(self, prs, title, content):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        shape = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.2))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
        shape.line.fill.background()
        tf = shape.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        txBox = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(5.5))
        tf2 = txBox.text_frame
        tf2.word_wrap = True
        count = 0
        for item_type, text in content:
            if count >= 12:
                break
            if item_type == 'h3' and text.strip():
                p = tf2.add_paragraph()
                p.text = f"▸ {text}"
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35)
                p.space_after = Pt(4)
                count += 1
            elif item_type == 'p' and text.strip() and len(text) > 15:
                p = tf2.add_paragraph()
                p.text = text[:100]
                p.font.size = Pt(11)
                p.font.color.rgb = RGBColor(0x4A, 0x55, 0x68)
                p.space_after = Pt(6)
                count += 1

    def _add_thanks_slide(self, prs):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN

        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)

        txBox = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(2))
        p = txBox.text_frame.paragraphs[0]
        p.text = "感谢聆听"
        p.font.size = Pt(48)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER

        txBox2 = slide.shapes.add_textbox(Inches(1), Inches(4.5), Inches(11), Inches(1))
        p2 = txBox2.text_frame.paragraphs[0]
        p2.text = "恳请各位评委老师批评指正"
        p2.font.size = Pt(20)
        p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35)
        p2.alignment = PP_ALIGN.CENTER

    def analyze_competitors(self, full_text: str, market_data: str = "") -> List[CompetitorInfo]:
        """竞品对标分析"""
        competitors = []
        # 提取竞品名
        names = re.findall(r'(?:英飞凌|Navitas|Nortek|Vertiv|西门子|ABB|华为|中兴|'
                          r'[一-鿿]{2,4}(?:科技|半导体|电子|光电|材料))', full_text)
        seen = set()
        for name in names:
            if name not in seen:
                seen.add(name)
                # 提取竞品相关参数
                params = {}
                param_pattern = rf'{re.escape(name)}[^。]*?(\w+\s*[:：]?\s*[\d.]+[%％]?\s*\w*)'
                for m in re.finditer(param_pattern, full_text):
                    params[str(len(params))] = m.group(1)[:30]

                competitors.append(CompetitorInfo(
                    name=name,
                    key_params=params if params else {}
                ))
        return competitors[:8]

    def format_competitor_table(self, competitors: List[CompetitorInfo]) -> str:
        """竞品对标 Markdown 表格"""
        if not competitors:
            return ""
        lines = ["## 竞品对标分析", "", "| 竞品 | 关键特征 |", "|------|----------|"]
        for c in competitors:
            params_str = "；".join(f"{k}:{v}" for k, v in list(c.key_params.items())[:2]) if c.key_params else "—"
            lines.append(f"| {c.name} | {params_str} |")
        return "\n".join(lines)
