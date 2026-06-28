"""
全自动竞赛策划智能体 - 全局配置
"""

import os
import json
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent
KNOWLEDGE_BASE_DIR = ROOT_DIR / "knowledge_base"
TEMPLATES_DIR = KNOWLEDGE_BASE_DIR / "templates"
RHETORIC_DIR = KNOWLEDGE_BASE_DIR / "rhetoric_lib"
VISUAL_DIR = KNOWLEDGE_BASE_DIR / "visual_styles"
GRAPHIC_DIR = KNOWLEDGE_BASE_DIR / "graphic_components"
DATA_POOL_DIR = ROOT_DIR / "data_pool" / "current_project"
OUTPUT_DIR = ROOT_DIR / "outputs"

# LLM API 配置
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")  # anthropic / openai
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# 内容生成配置
MAX_WORDS_PER_CHAPTER = {
    "executive_summary": 1000,
    "background": 4000,
    "technology": 5500,
    "product_design": 3000,
    "market_analysis": 4500,
    "team_intro": 2000,
    "financial": 1500,
    "future_plan": 1500,
}

# 章节页数配比（按80页标准）
PAGE_ALLOCATION = {
    "executive_summary": {"pages": "3-4", "ratio": 0.05},
    "background": {"pages": "12-15", "ratio": 0.15},
    "technology": {"pages": "18-22", "ratio": 0.25},
    "product_design": {"pages": "10-12", "ratio": 0.15},
    "market_analysis": {"pages": "14-18", "ratio": 0.20},
    "team_intro": {"pages": "6-8", "ratio": 0.10},
    "financial": {"pages": "4-6", "ratio": 0.05},
    "future_plan": {"pages": "4-6", "ratio": 0.05},
}

# 资料完整度阈值
COMPLETENESS_THRESHOLD_FULL = 0.80   # ≥80% 直接执行
COMPLETENESS_THRESHOLD_PARTIAL = 0.50  # 50-80% 引导补全
# <50% 暂缓执行

# 输出配置
DEFAULT_OUTPUT_FORMATS = ["html", "md", "docx"]  # 默认输出格式
IMAGE_DPI = 300
IMAGE_ASPECT_RATIO_BG = (20, 10)  # 背景新闻配图比例

# 隐私与安全
DATA_RETENTION_DAYS = 7  # 任务交付后N天自动清除客户数据
ENABLE_AI_JUDGE = True   # 是否启用AI评审官
PLAGIARISM_THRESHOLD = 0.30  # 查重率阈值

# 支持的赛事组别 (从模板索引动态加载)
def _load_competitions():
    """从 templates/index.json 动态加载赛事列表"""
    index_path = ROOT_DIR / "knowledge_base" / "templates" / "index.json"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return list(data.get("competitions", {}).keys())
    except Exception:
        # fallback: 扫描templates目录
        import glob
        templates = glob.glob(str(TEMPLATES_DIR / "*.json"))
        names = []
        for t in templates:
            try:
                with open(t, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    if "competition_name" in d:
                        names.append(d["competition_name"])
            except: pass
        return names if names else ["互联网+高教主赛道"]  # 保底

SUPPORTED_COMPETITIONS = _load_competitions()

# 支持的配色方案
SUPPORTED_THEMES = {
    "deep_blue": "深科技蓝",
    "dark_tech": "科技炫酷黑",
    "fresh_green": "清新环保绿",
    "academic_red": "沉稳学术红",
    "warm_orange": "活力橙",
    "elegant_gold": "典雅金",
}

# 加载赛事详细元数据 (模板文件/页数/风格等)
def get_competition_metadata():
    """返回 {赛事名: {template_file, typical_pages, visual_style, ...}}"""
    index_path = ROOT_DIR / "knowledge_base" / "templates" / "index.json"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("competitions", {})
    except Exception:
        return {}

# 日志配置
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
