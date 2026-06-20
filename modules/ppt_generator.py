"""
答辩PPT生成模块 + 竞品对标分析
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple


class PPTGenerator:
    """答辩PPT生成器——专业风格"""

    def __init__(self):
        self.C = {"pri": "0A2F5A", "acc": "FF6B35", "wht": "FFFFFF",
                  "bg": "F5F7FA", "txt": "1A1A2E", "gry": "4A5568"}

    def generate_ppt(self, full_text: str, project_name: str, output_path: Path) -> Path:
        try:
            from pptx import Presentation
            from pptx.util import Inches, Pt, Emu
            from pptx.dml.color import RGBColor
            from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
        except ImportError:
            return None

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        W, H = 13.333, 7.5

        # Parse content into structured sections
        chapters = self._parse(full_text)
        # Extract key numbers
        numbers = re.findall(r'(\d+\.?\d*\s*[%％亿万千]?\s*(?:元|美元|项|篇)?)', full_text)
        key_nums = numbers[:6] if numbers else []

        # Slide 1: Cover
        self._cover(prs, project_name, "竞赛答辩汇报")
        # Slide 2: Problem/Background
        bg_text = self._get_section(chapters, "背景")
        self._section_slide(prs, "项目背景与行业痛点", bg_text, "为什么做这个项目？")
        # Slide 3: Solution/Tech
        tech_text = self._get_section(chapters, "技术")
        self._section_slide(prs, "核心技术原理与创新", tech_text, "我们是怎么做的？")
        # Slide 4: Key data highlight
        if key_nums:
            self._data_slide(prs, "关键数据", key_nums)
        # Slide 5: Product
        prod_text = self._get_section(chapters, "产品")
        if prod_text:
            self._section_slide(prs, "产品设计与应用", prod_text, "")
        # Slide 6: Market
        mkt_text = self._get_section(chapters, "市场")
        if mkt_text:
            self._section_slide(prs, "市场分析与商业模式", mkt_text, "")
        # Slide 7: Team
        team_text = self._get_section(chapters, "团队")
        if team_text:
            self._team_slide(prs, team_text)
        # Slide 8: Thank you
        self._thanks(prs)

        prs.save(str(output_path))
        return output_path

    def _parse(self, text: str) -> dict:
        """Parse markdown into chapter sections"""
        chapters = {}
        current = None
        for line in text.split('\n'):
            m = re.match(r'^## (.+)', line)
            if m:
                current = m.group(1)
                chapters[current] = []
            elif current and line.strip():
                chapters[current].append(line.strip())
        return chapters

    def _get_section(self, chapters: dict, keyword: str) -> str:
        for k, v in chapters.items():
            if keyword in k:
                # Take key bullet points (lines that start with - or contain key info)
                bullets = []
                for line in v:
                    clean = re.sub(r'^[-*#>\s]+', '', line).strip()
                    if len(clean) > 10:
                        bullets.append(clean[:100])
                return '\n'.join(bullets[:8])
        return ""

    def _cover(self, prs, title, subtitle):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Dark bg
        bg = slide.background; fill = bg.fill; fill.solid()
        fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
        # Title
        tb = slide.shapes.add_textbox(Inches(1.5), Inches(2), Inches(10), Inches(2))
        tf = tb.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = title; p.font.size = Pt(38)
        p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); p.alignment = PP_ALIGN.CENTER
        # Subtitle
        tb2 = slide.shapes.add_textbox(Inches(1.5), Inches(4.2), Inches(10), Inches(1))
        tf2 = tb2.text_frame
        p2 = tf2.paragraphs[0]; p2.text = subtitle
        p2.font.size = Pt(20); p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35); p2.alignment = PP_ALIGN.CENTER
        # Accent line
        shape = slide.shapes.add_shape(1, Inches(5), Inches(5.5), Inches(3.333), Inches(0.04))
        shape.fill.solid(); shape.fill.fore_color.rgb = RGBColor(0xFF, 0x6B, 0x35)
        shape.line.fill.background()

    def _section_slide(self, prs, title, content, subtitle=""):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Title bar
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.3))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A); bar.line.fill.background()
        tf = bar.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = title; p.font.size = Pt(28)
        p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.LEFT; tf.margin_left = Inches(1)
        # Subtitle if any
        if subtitle:
            tb = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(11), Inches(0.5))
            p2 = tb.text_frame.paragraphs[0]; p2.text = subtitle
            p2.font.size = Pt(14); p2.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
        # Content as bullet points
        tb2 = slide.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(11), Inches(5))
        tf2 = tb2.text_frame; tf2.word_wrap = True
        lines = content.split('\n')[:8]
        for i, line in enumerate(lines):
            clean = re.sub(r'^[-*#>\s]+', '', line).strip()
            if len(clean) > 8:
                if i == 0:
                    p3 = tf2.paragraphs[0]
                else:
                    p3 = tf2.add_paragraph()
                p3.text = f"▸ {clean[:120]}"
                p3.font.size = Pt(14)
                p3.font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
                p3.space_after = Pt(10)

    def _data_slide(self, prs, title, numbers):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.3))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A); bar.line.fill.background()
        p = bar.text_frame.paragraphs[0]; p.text = title; p.font.size = Pt(28)
        p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        bar.text_frame.margin_left = Inches(1)

        # Grid of number cards
        for i, num in enumerate(numbers[:6]):
            col = i % 3; row = i // 3
            x = 1.2 + col * 3.8; y = 2.2 + row * 2.3
            # Card background
            card = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(3.4), Inches(1.8))
            card.fill.solid(); card.fill.fore_color.rgb = RGBColor(0xF5, 0xF7, 0xFA)
            card.line.color.rgb = RGBColor(0xE5, 0xE7, 0xEB); card.line.width = Pt(1)
            # Number
            tb = slide.shapes.add_textbox(Inches(x+0.3), Inches(y+0.3), Inches(2.8), Inches(0.8))
            p2 = tb.text_frame.paragraphs[0]; p2.text = num; p2.font.size = Pt(28)
            p2.font.bold = True; p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35); p2.alignment = PP_ALIGN.CENTER

    def _team_slide(self, prs, team_text):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(13.333), Inches(1.3))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A); bar.line.fill.background()
        p = bar.text_frame.paragraphs[0]; p.text = "团队介绍与核心优势"
        p.font.size = Pt(28); p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        bar.text_frame.margin_left = Inches(1)

        # Team members as cards
        members = []
        for line in team_text.split('\n'):
            clean = re.sub(r'^[-*#>\s]+', '', line).strip()
            if len(clean) > 10 and ('博士' in clean or '硕士' in clean or '负责人' in clean or '教授' in clean or '导师' in clean):
                members.append(clean[:80])
        for i, m in enumerate(members[:6]):
            col = i % 3; row = i // 3
            x = 1.2 + col * 3.8; y = 2 + row * 2.5
            card = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(3.4), Inches(2))
            card.fill.solid(); card.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            card.line.color.rgb = RGBColor(0xE5, 0xE7, 0xEB); card.line.width = Pt(1)
            tb = slide.shapes.add_textbox(Inches(x+0.3), Inches(y+0.5), Inches(2.8), Inches(1))
            p2 = tb.text_frame.paragraphs[0]; p2.text = m
            p2.font.size = Pt(11); p2.font.color.rgb = RGBColor(0x1F, 0x29, 0x37); p2.alignment = PP_ALIGN.CENTER

    def _thanks(self, prs):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.background; fill = bg.fill; fill.solid()
        fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)
        tb = slide.shapes.add_textbox(Inches(2), Inches(2.5), Inches(9), Inches(2))
        p = tb.text_frame.paragraphs[0]; p.text = "感谢聆听"
        p.font.size = Pt(48); p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER
        tb2 = slide.shapes.add_textbox(Inches(2), Inches(4.5), Inches(9), Inches(1))
        p2 = tb2.text_frame.paragraphs[0]; p2.text = "恳请各位评委老师批评指正"
        p2.font.size = Pt(20); p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35); p2.alignment = PP_ALIGN.CENTER

    def analyze_competitors(self, full_text: str, market_data: str = "") -> List:
        from dataclasses import dataclass
        @dataclass
        class CompetitorInfo:
            name: str; key_params: dict = None
        competitors = []
        known = ["英飞凌","Navitas","Nortek","Vertiv","西门子","ABB","华为","中兴","Sigma-Aldrich"]
        seen = set()
        for name in known:
            if name in full_text and name not in seen:
                seen.add(name); competitors.append(CompetitorInfo(name=name, key_params={}))
        return competitors[:8]

    def format_competitor_table(self, competitors: List) -> str:
        if not competitors: return ""
        lines = ["## 竞品对标分析", "", "| 竞品 | 说明 |", "|------|------|"]
        for c in competitors:
            lines.append(f"| {c.name} | 主要竞争对手 |")
        return "\n".join(lines)
