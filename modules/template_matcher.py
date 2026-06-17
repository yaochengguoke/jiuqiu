"""
模块2：模板匹配
- 根据赛事组别匹配对应的国奖模板
- 加载四层模板数据（骨架+话术+视觉+图元）
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TEMPLATES_DIR, RHETORIC_DIR, VISUAL_DIR, GRAPHIC_DIR


@dataclass
class MatchedTemplate:
    """匹配到的完整模板包"""
    competition_name: str
    template_meta: Dict[str, Any]
    # L1: 骨架层
    skeleton: Dict[str, Any]
    chapters: List[Dict[str, Any]]
    # L2: 话术层
    rhetoric_data: Dict[str, Dict[str, Any]]
    # L3: 视觉层
    visual_style: Dict[str, Any]
    # L4: 图元层
    graphic_components: Dict[str, Any]

    match_confidence: float = 1.0
    fallback_used: bool = False


class TemplateMatcher:
    """
    模板匹配模块

    职责：
    1. 根据赛事组别名称定位对应的结构化模板
    2. 加载四层模板数据
    3. 无精确匹配时，使用最相似模板作为fallback
    """

    def __init__(self):
        self.index = self._load_index()
        self._template_cache: Dict[str, MatchedTemplate] = {}

    def _load_index(self) -> dict:
        """加载模板索引"""
        index_path = TEMPLATES_DIR / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"模板索引文件不存在: {index_path}")
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def match_template(self, competition_name: str) -> MatchedTemplate:
        """
        根据赛事组别匹配模板

        Args:
            competition_name: 赛事组别名称，如"互联网+高教主赛道"

        Returns:
            MatchedTemplate: 包含完整四层模板数据的对象
        """
        # 检查缓存
        if competition_name in self._template_cache:
            return self._template_cache[competition_name]

        competitions = self.index.get("competitions", {})

        # 精确匹配
        if competition_name in competitions:
            template = self._load_full_template(competition_name, competitions[competition_name])
            self._template_cache[competition_name] = template
            return template

        # 模糊匹配
        best_match = self._fuzzy_match(competition_name, competitions)
        if best_match:
            name, config = best_match
            template = self._load_full_template(name, config)
            template.match_confidence = 0.7
            template.fallback_used = True
            self._template_cache[competition_name] = template
            return template

        # 最终兜底：使用互联网+高教主赛道模板
        fallback_name = "互联网+高教主赛道"
        if fallback_name in competitions:
            template = self._load_full_template(fallback_name, competitions[fallback_name])
            template.match_confidence = 0.5
            template.fallback_used = True
            self._template_cache[competition_name] = template
            return template

        raise ValueError(f"无法匹配赛事组别: {competition_name}，且无可用fallback模板")

    def _fuzzy_match(self, query: str, competitions: dict) -> Optional[tuple]:
        """模糊匹配：基于关键词重叠度"""
        query_keywords = set(query.replace("+", " ").replace("、", " ").split())

        best_score = 0
        best_match = None

        for name, config in competitions.items():
            name_keywords = set(name.replace("+", " ").replace("、", " ").split())
            config_keywords = set(config.get("keywords", []))

            all_keywords = name_keywords | config_keywords
            overlap = len(query_keywords & all_keywords)

            if overlap > best_score:
                best_score = overlap
                best_match = (name, config)

        return best_match if best_score >= 1 else None

    def _load_full_template(self, name: str, config: dict) -> MatchedTemplate:
        """加载完整的四层模板数据"""
        template_file = config.get("template_file", "")
        template_path = TEMPLATES_DIR / template_file

        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template_data = json.load(f)

        # L1: 骨架层
        skeleton = template_data.get("L1_skeleton", {})
        chapters = skeleton.get("chapters", [])

        # L2: 话术层
        rhetoric_mapping = template_data.get("L2_rhetoric", {}).get("rhetoric_lib_mapping", {})
        rhetoric_data = self._load_rhetoric_libs(rhetoric_mapping)

        # L3: 视觉层
        visual_style_id = config.get("visual_style", "deep_blue")
        visual_style = self._load_visual_style(visual_style_id)

        # L4: 图元层
        graphic_components = self._load_graphic_components(template_data)

        return MatchedTemplate(
            competition_name=name,
            template_meta=template_data.get("meta", {}),
            skeleton=skeleton,
            chapters=chapters,
            rhetoric_data=rhetoric_data,
            visual_style=visual_style,
            graphic_components=graphic_components,
            match_confidence=1.0,
            fallback_used=False,
        )

    def _load_rhetoric_libs(self, mapping: dict) -> Dict[str, dict]:
        """加载话术库"""
        rhetoric_data = {}
        for chapter_key, filename in mapping.items():
            filepath = RHETORIC_DIR / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    rhetoric_data[chapter_key] = json.load(f)
        return rhetoric_data

    def _load_visual_style(self, style_id: str) -> dict:
        """加载视觉风格"""
        # 映射表
        style_files = {
            "deep_blue": "visual_deep_blue.json",
            "dark_tech": "visual_dark_tech.json",
            "academic_red": "visual_academic_red.json",
            "fresh_green": "visual_fresh_green.json",
        }

        filename = style_files.get(style_id, "visual_deep_blue.json")
        filepath = VISUAL_DIR / filename

        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

        # fallback
        with open(VISUAL_DIR / "visual_deep_blue.json", "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_graphic_components(self, template_data: dict) -> dict:
        """加载图元组件"""
        components = {}
        graphic_mapping = template_data.get("L4_graphic", {}).get("component_library", {})

        for comp_type, filename in graphic_mapping.items():
            filepath = GRAPHIC_DIR / filename
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    components[comp_type] = json.load(f)

        return components

    def get_chapter_config(self, template: MatchedTemplate, chapter_id: str) -> Optional[dict]:
        """获取特定章节的配置"""
        for chapter in template.chapters:
            if chapter.get("id") == chapter_id:
                return chapter
        return None

    def get_rhetoric_for_chapter(self, template: MatchedTemplate, chapter_id: str) -> dict:
        """获取特定章节的话术模板"""
        return template.rhetoric_data.get(chapter_id, {})

    def list_available_competitions(self) -> List[str]:
        """列出所有可用的赛事模板"""
        return list(self.index.get("competitions", {}).keys())
