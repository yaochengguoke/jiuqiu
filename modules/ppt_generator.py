"""
答辩PPT生成模块
完整框架：封面→目录→背景→技术→产品→商业模式→团队→规划→致谢
"""

import re, os, io
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    HAS_PPTX = True
except ImportError:
    HAS_PPTX = False


class PPTGenerator:
    """专业答辩PPT生成器"""

    def __init__(self):
        self.W = 13.333  # 16:9
        self.H = 7.5
        self.slide_num = 0

    def generate_ppt(self, full_text: str, project_name: str, output_path: Path) -> Optional[Path]:
        if not HAS_PPTX:
            return None
        prs = Presentation()
        prs.slide_width = Inches(self.W)
        prs.slide_height = Inches(self.H)

        chapters = self._parse(full_text)
        nums = re.findall(r'(\d+\.?\d*\s*[%％亿万千]?\s*(?:元|美元|项|篇|倍))', full_text)
        innovations = re.findall(r'(?:创新点|核心创新)[：:\s]*([^\n]{10,60})', full_text)

        # 1. 封面
        self._cover(prs, project_name)
        # 2. 目录
        toc = ["项目背景与痛点", "核心技术原理与创新", "产品设计与应用场景",
               "市场分析与商业模式", "团队介绍与核心优势", "发展规划与融资需求"]
        self._toc(prs, toc)
        # 3. 项目背景 (1-2p)
        self._content_slide(prs, "项目背景与行业痛点",
            self._extract_bullets(chapters, ["背景", "行业"]),
            "市场痛点、政策机遇、行业趋势", nums[:2])
        # 4. 核心技术 (2-3p)
        self._content_slide(prs, "核心技术原理与创新",
            self._extract_bullets(chapters, ["技术", "创新", "原理"]),
            "技术路线、创新突破、竞品对比", nums[2:5] if len(nums) > 2 else [])
        # 5. 产品/解决方案
        prod = self._extract_bullets(chapters, ["产品", "应用", "场景", "设计"])
        if prod:
            self._content_slide(prs, "产品设计与应用场景", prod, "产品形态、应用落地", [])
        # 6. 商业模式
        mkt = self._extract_bullets(chapters, ["市场", "商业", "模式"])
        if mkt:
            self._content_slide(prs, "市场分析与商业模式", mkt, "商业模式、盈利路径、市场空间", nums[4:6] if len(nums) > 4 else [])
        # 7. 团队
        team = self._extract_bullets(chapters, ["团队", "成员", "介绍"])
        if team:
            self._team_slide(prs, team)
        # 8. 发展规划
        plan = self._extract_bullets(chapters, ["规划", "发展", "未来", "财务", "融资"])
        if plan:
            self._content_slide(prs, "发展规划与融资需求", plan, "技术路线、市场拓展、资金用途", [])
        # 9. 致谢
        self._thanks(prs)

        prs.save(str(output_path))
        return output_path

    def _parse(self, text: str) -> dict:
        chapters = {}; current = None
        for line in text.split('\n'):
            m = re.match(r'^## (.+)', line)
            if m: current = m.group(1); chapters[current] = []
            elif current and line.strip(): chapters[current].append(line.strip())
        return chapters

    def _extract_bullets(self, chapters: dict, keywords: List[str], max_items: int = 6) -> list:
        items = []
        for k, v in chapters.items():
            if any(kw in k for kw in keywords):
                for line in v:
                    # 彻底过滤标记行
                    if '【待补充】' in line or '【来源】' in line:
                        continue
                    clean = re.sub(r'^[-*#>\d\.\s【】]+', '', line).strip()
                    # 过滤太短或纯标记
                    if len(clean) < 10 or clean.startswith('【') or clean.startswith('>'):
                        continue
                    items.append(clean[:130])
        # 去重
        seen = set(); result = []
        for item in items:
            key = item[:25]
            if key not in seen: seen.add(key); result.append(item)
        # 返回更完整的列表
        return result[:max_items]

    def _add_slide_number(self, slide):
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        self.slide_num += 1
        tb = slide.shapes.add_textbox(Inches(12.2), Inches(7.05), Inches(1), Inches(0.35))
        p = tb.text_frame.paragraphs[0]
        p.text = str(self.slide_num); p.font.size = Pt(9)
        p.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF); p.alignment = PP_ALIGN.RIGHT

    def _cover(self, prs, project_name):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.background; fill = bg.fill; fill.solid()
        fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A)

        # Title
        tb = slide.shapes.add_textbox(Inches(1.2), Inches(2.2), Inches(10.9), Inches(2))
        tf = tb.text_frame; tf.word_wrap = True
        p = tf.paragraphs[0]; p.text = project_name; p.font.size = Pt(40)
        p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); p.alignment = PP_ALIGN.CENTER

        # Subtitle
        tb2 = slide.shapes.add_textbox(Inches(1.2), Inches(4.3), Inches(10.9), Inches(0.6))
        p2 = tb2.text_frame.paragraphs[0]; p2.text = "竞赛答辩汇报"
        p2.font.size = Pt(22); p2.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35); p2.alignment = PP_ALIGN.CENTER

        # Accent line
        line = slide.shapes.add_shape(1, Inches(5), Inches(5.3), Inches(3.333), Inches(0.04))
        line.fill.solid(); line.fill.fore_color.rgb = RGBColor(0xFF, 0x6B, 0x35); line.line.fill.background()

    def _toc(self, prs, items):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # Title bar
        self._title_bar(slide, "汇报目录")
        # Numbered items
        tb = slide.shapes.add_textbox(Inches(2), Inches(2), Inches(9), Inches(5))
        tf = tb.text_frame; tf.word_wrap = True
        for i, item in enumerate(items, 1):
            p = tf.add_paragraph() if i > 1 else tf.paragraphs[0]
            p.text = f"{i:02d}   {item}"; p.font.size = Pt(18)
            p.font.color.rgb = RGBColor(0x1F, 0x29, 0x37); p.space_after = Pt(14)
        self._add_slide_number(slide)

    def _title_bar(self, slide, title):
        bar = slide.shapes.add_shape(1, Inches(0), Inches(0), Inches(self.W), Inches(1.25))
        bar.fill.solid(); bar.fill.fore_color.rgb = RGBColor(0x0A, 0x2F, 0x5A); bar.line.fill.background()
        tf = bar.text_frame; tf.word_wrap = True; tf.margin_left = Inches(1)
        p = tf.paragraphs[0]; p.text = title; p.font.size = Pt(26)
        p.font.bold = True; p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    def _content_slide(self, prs, title, bullets, subtitle="", highlight_nums=None):
        # 跳过无内容的页
        if not bullets:
            return
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._title_bar(slide, title)

        y = 1.8
        # Subtitle
        if subtitle:
            tb = slide.shapes.add_textbox(Inches(1), Inches(y), Inches(11), Inches(0.4))
            p = tb.text_frame.paragraphs[0]; p.text = subtitle
            p.font.size = Pt(13); p.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)
            y += 0.6

        # Bullet points - 更多、更紧凑
        if bullets:
            tb2 = slide.shapes.add_textbox(Inches(1.2), Inches(y), Inches(11.3), Inches(5.5 - (y - 1.8)))
            tf2 = tb2.text_frame; tf2.word_wrap = True
            for i, b in enumerate(bullets[:8]):
                p = tf2.add_paragraph() if i > 0 else tf2.paragraphs[0]
                p.text = f"▸ {b[:140]}"; p.font.size = Pt(15)
                p.font.color.rgb = RGBColor(0x1F, 0x29, 0x37); p.space_after = Pt(10)

        # Highlight numbers at the bottom
        if highlight_nums:
            y_bot = 6.3
            for i, num in enumerate(highlight_nums[:4]):
                x = 1.2 + i * 3
                card = slide.shapes.add_shape(1, Inches(x), Inches(y_bot), Inches(2.7), Inches(0.9))
                card.fill.solid(); card.fill.fore_color.rgb = RGBColor(0xF5, 0xF7, 0xFA)
                card.line.color.rgb = RGBColor(0xE5, 0xE7, 0xEB)
                tb3 = slide.shapes.add_textbox(Inches(x+0.2), Inches(y_bot+0.15), Inches(2.3), Inches(0.6))
                p3 = tb3.text_frame.paragraphs[0]; p3.text = num
                p3.font.size = Pt(18); p3.font.bold = True
                p3.font.color.rgb = RGBColor(0xFF, 0x6B, 0x35); p3.alignment = PP_ALIGN.CENTER

        # Speaker notes
        notes_text = f"【演讲提示】\n- {title}：共{len(bullets)}个要点\n- 建议时长：1.5-2分钟\n- 重点强调数据对比和差异化优势"
        slide.notes_slide.notes_text_frame.text = notes_text
        self._add_slide_number(slide)

    def _team_slide(self, prs, team_items):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        self._title_bar(slide, "团队介绍与核心优势")

        members = []
        for item in team_items:
            if any(kw in item for kw in ['博士', '硕士', '教授', '导师', '负责人', '指导', '成员']):
                # 按逗号拆成多行显示
                parts = [p.strip() for p in item.split(',') if p.strip()]
                members.append(parts[:4])  # 最多4行
        members = members[:6]

        for i, parts in enumerate(members):
            col, row = i % 3, i // 3
            x, y = 1.2 + col * 3.8, 2.2 + row * 2.5
            card = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(3.4), Inches(2))
            card.fill.solid(); card.fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            card.line.color.rgb = RGBColor(0xE5, 0xE7, 0xEB)
            accent = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(3.4), Inches(0.06))
            accent.fill.solid(); accent.fill.fore_color.rgb = RGBColor(0xFF, 0x6B, 0x35)
            accent.line.fill.background()
            tb = slide.shapes.add_textbox(Inches(x+0.2), Inches(y+0.3), Inches(3), Inches(1.5))
            tf = tb.text_frame; tf.word_wrap = True
            for j, part in enumerate(parts):
                p = tf.add_paragraph() if j > 0 else tf.paragraphs[0]
                p.text = part[:40]
                p.font.size = Pt(10) if j > 0 else Pt(11)
                p.font.bold = (j == 0)
                p.font.color.rgb = RGBColor(0x1F, 0x29, 0x37) if j == 0 else RGBColor(0x6B, 0x72, 0x80)
                p.alignment = PP_ALIGN.CENTER
                p.space_after = Pt(2)

        slide.notes_slide.notes_text_frame.text = "【演讲提示】\n- 强调团队互补性和技术积累\n- 突出指导老师的行业影响力"
        self._add_slide_number(slide)

    def _thanks(self, prs):
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
        slide.notes_slide.notes_text_frame.text = "【演讲提示】\n- 最后感谢评委\n- 留出Q&A时间"
        self._add_slide_number(slide)

    def analyze_competitors(self, full_text: str, market_data: str = "") -> List:
        @dataclass
        class C: name: str; key_params: dict = None
        known = ["英飞凌","Navitas","Nortek","Vertiv","西门子","ABB","华为","中兴","Sigma-Aldrich"]
        result = []
        for n in known:
            if n in full_text: result.append(C(name=n))
        return result[:8]

    def format_competitor_table(self, competitors: List) -> str:
        if not competitors: return ""
        lines = ["## 竞品对标分析", "", "| 竞品 | 说明 |", "|------|------|"]
        for c in competitors: lines.append(f"| {c.name} | 主要竞争对手 |")
        return "\n".join(lines)
