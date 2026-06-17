#!/usr/bin/env python3
"""
全自动竞赛策划智能体 - 主入口

智能体核心循环：
客户提交 → 匹配模板 → 解析素材 → 检查完整度
→ 生成内容 → 自动制图 → 排版美化 → 质量检查 → 输出成品

用法：
    python main.py                          # 交互式CLI模式
    python main.py --demo                   # 演示模式（不需要API密钥）
    python main.py --config config.json     # 从配置文件加载客户数据
    python main.py --streamlit              # 启动Web界面（如已安装streamlit）
"""

import sys
import json
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 确保项目根目录在路径中
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ROOT_DIR, OUTPUT_DIR, DATA_POOL_DIR, VISUAL_DIR,
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    SUPPORTED_COMPETITIONS, SUPPORTED_THEMES,
    ENABLE_AI_JUDGE, COMPLETENESS_THRESHOLD_FULL,
)
from utils.llm_client import LLMClient
from modules.input_processor import InputProcessor, CompletenessLevel
from modules.template_matcher import TemplateMatcher
from modules.material_parser import MaterialParser
from modules.completeness_checker import CompletenessChecker
from modules.content_generator import ContentGenerator
from modules.diagram_generator import DiagramGenerator
from modules.layout_engine import LayoutEngine
from modules.quality_checker import QualityChecker
from modules.defense_prep import DefensePrep
from modules.output_exporter import OutputExporter


# ===== 智能体核心类 =====

class CompetitionAgent:
    """
    全自动竞赛策划智能体

    这是一个完整的Agent循环，按照PRD定义的10步工作流执行：
    1. 识别 → 2. 匹配 → 3. 建库 → 4. 检漏 → 5. 写作
    → 6. 制图 → 7. 美化 → 8. 校对 → 9. 输出 → 10. 反馈
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        初始化智能体

        Args:
            api_key: Anthropic API密钥（None则使用环境变量或演示模式）
            model: 模型名称
        """
        # 初始化LLM客户端
        self.llm_client = LLMClient(
            api_key=api_key or ANTHROPIC_API_KEY,
            model=model or ANTHROPIC_MODEL,
        )

        self.use_ai = self.llm_client.is_available

        if self.use_ai:
            print("[OK] LLM API已连接，将使用AI生成国奖级内容")
        else:
            print("[WARN]  演示模式：将使用模板化规则生成内容")
            print("   要启用AI生成，请设置环境变量 ANTHROPIC_API_KEY")
            print()

        # 初始化各模块
        self.input_processor = InputProcessor()
        self.template_matcher = TemplateMatcher()
        self.material_parser = MaterialParser()
        self.completeness_checker = CompletenessChecker(
            llm_client=self.llm_client if self.use_ai else None
        )
        self.content_generator = ContentGenerator(
            llm_client=self.llm_client if self.use_ai else None
        )

        # 延迟初始化的模块（需要模板和样式信息）
        self.diagram_generator: Optional[DiagramGenerator] = None
        self.layout_engine: Optional[LayoutEngine] = None
        self.quality_checker: Optional[QualityChecker] = None
        self.output_exporter: Optional[OutputExporter] = None

        # 运行状态
        self.current_template = None
        self.current_data_pool = None
        self.current_document = None
        self.current_export = None

    def _load_visual_style(self, style_id: str) -> dict:
        """根据风格ID加载视觉风格文件（支持用户主题切换）"""
        import json
        style_files = {
            "deep_blue": "visual_deep_blue.json",
            "dark_tech": "visual_dark_tech.json",
            "academic_red": "visual_academic_red.json",
            "fresh_green": "visual_fresh_green.json",
            "warm_orange": "visual_warm_orange.json",
            "elegant_gold": "visual_elegant_gold.json",
        }
        filename = style_files.get(style_id, "visual_deep_blue.json")
        filepath = VISUAL_DIR / filename
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        # fallback
        with open(VISUAL_DIR / "visual_deep_blue.json", "r", encoding="utf-8") as f:
            return json.load(f)
        self.current_export = None

    def run(
        self,
        raw_submission: Dict[str, Any],
        verbose: bool = True,
        auto_confirm: bool = False,
    ) -> bool:
        """
        运行完整的智能体流水线

        Args:
            raw_submission: 客户提交的原始数据（5类必填资料）
            verbose: 是否详细输出进度
            auto_confirm: 是否自动确认（跳过用户交互）

        Returns:
            bool: 是否成功完成
        """
        print("=" * 70)
        print("  [Award] 全自动竞赛策划智能体 - 开始运行")
        print("=" * 70)
        print()

        # ===== 阶段1：输入处理 =====
        self._print_stage(1, "输入处理与校验")
        submission, completeness = self.input_processor.process_submission(raw_submission)

        if verbose:
            print(f"  赛事组别：{submission.competition_info.competition_name}")
            print(f"  项目名称：{submission.project_material.project_name}")
            print(f"  资料完整度：{completeness.score:.0%}")
            print(f"  分级响应：{completeness.level}")
            print()

        # 资料严重缺失 → 终止并引导
        if completeness.level == CompletenessLevel.INSUFFICIENT:
            print(completeness.recommendation)
            if not auto_confirm:
                input("\n按Enter键退出...")
            return False

        # ===== 阶段2：模板匹配 =====
        self._print_stage(2, "模板匹配")
        self.current_template = self.template_matcher.match_template(
            submission.competition_info.competition_name
        )

        if verbose:
            print(f"  匹配模板：{self.current_template.competition_name}")
            print(f"  章节数：{len(self.current_template.chapters)}章")
            print(f"  视觉风格：{self.current_template.visual_style.get('name', '默认')}")
            if self.current_template.fallback_used:
                print(f"  [WARN] 未精确匹配，使用最相似模板（置信度：{self.current_template.match_confidence:.0%}）")
            print()

        # ===== 阶段3：素材解析与建库 =====
        self._print_stage(3, "素材解析与中央数据池构建")
        customer_kb = self.input_processor.build_customer_knowledge_base()
        self.current_data_pool = self.material_parser.parse_and_build_pool(
            customer_kb=customer_kb,
            template_chapters=self.current_template.chapters,
        )

        if verbose:
            nums_count = len(self.current_data_pool.numeric_entities)
            print(f"  提取数据实体：{nums_count}组")
            print(f"  技术模块：{len(self.current_data_pool.tech_pool.get('key_modules', []))}个")
            print(f"  目标客户：{len(self.current_data_pool.market_pool.get('target_customers', []))}个")
            print()

        # ===== 阶段4：完整度检查 =====
        self._print_stage(4, "素材完整度逐章检查")
        chapter_check = self.completeness_checker.check_all_chapters(
            data_pool=self.current_data_pool,
            template_chapters=self.current_template.chapters,
        )

        if verbose:
            print(self.completeness_checker.print_report(chapter_check))
            print()

        if not chapter_check.can_proceed:
            print("[FAIL] 关键素材缺失过多，建议先补充资料。")
            return False

        # ===== 阶段5：AI内容生成 =====
        self._print_stage(5, "AI内容生成（按国奖模板逐章写作）")

        def progress_callback(current, total, chapter_name):
            bar = "█" * current + "░" * (total - current)
            print(f"\r  [{bar}] {current}/{total} 正在生成：{chapter_name}...", end="", flush=True)

        self.current_document = self.content_generator.generate_all_chapters(
            template=self.current_template,
            data_pool=self.current_data_pool,
            progress_callback=progress_callback if verbose else None,
        )
        print()
        if verbose:
            print(f"\n  [OK] 正文生成完成")
            print(f"  总字数：{self.current_document.total_word_count}字")
            print(f"  缺失标记：{len(self.current_document.missing_sections)}处")
            print()

        # ===== 阶段6：自动制图 =====
        self._print_stage(6, "自动制图（技术架构图/流程图/封面）")
        # 使用用户选择的主题配色，如未选择则使用模板默认
        user_theme = submission.doc_requirement.color_theme or "deep_blue"
        user_visual = self._load_visual_style(user_theme)
        self.diagram_generator = DiagramGenerator(visual_style=user_visual)

        tech_name = self.current_data_pool.tech_pool.get("technology_name", "核心技术")
        tech_modules = self.current_data_pool.tech_pool.get("key_modules", [])
        innovations = self.current_data_pool.tech_pool.get("innovations", [])

        diagrams = self.diagram_generator.generate_all_diagrams_for_document(
            project_name=self.current_data_pool.project_name,
            competition_name=self.current_template.competition_name,
            tech_name=tech_name,
            tech_modules=tech_modules,
            innovations=innovations,
        )

        if verbose:
            print(f"  生成图表：{len(diagrams)}张")
            for name, path in diagrams.items():
                print(f"    [Chart] {name}: {path.name}")
            print()

        # ===== 阶段7：排版美化 =====
        self._print_stage(7, "排版美化")
        color_theme = submission.doc_requirement.color_theme or "deep_blue"
        user_visual = self._load_visual_style(color_theme)
        self.layout_engine = LayoutEngine(user_visual)

        if verbose:
            print(f"  套用风格：{SUPPORTED_THEMES.get(color_theme, color_theme)}")
            print(f"  主色调：{user_visual.get('colors', {}).get('primary', '#0A2F5A')}")
            print()

        # ===== 阶段8：质量检查 =====
        self._print_stage(8, "质量检查与AI评审")
        self.quality_checker = QualityChecker(
            llm_client=self.llm_client if self.use_ai and ENABLE_AI_JUDGE else None
        )
        quality_report = self.quality_checker.run_full_check(
            document=self.current_document,
            data_pool=self.current_data_pool,
        )
        quality_text = self.quality_checker.print_report(quality_report)

        if verbose:
            print(quality_text)
            print()

        # ===== 阶段8.5：答辩预演 =====
        self._print_stage(8.5, "答辩预演（生成评委提问+电梯演讲）")
        defense_prep = DefensePrep(
            llm_client=self.llm_client if self.use_ai else None
        )
        defense_report = defense_prep.generate_defense_prep(
            full_text=self.current_document.get_full_text(),
            project_name=self.current_document.project_name,
        )
        defense_text = defense_prep.print_report(defense_report)

        if verbose:
            print(f"  生成潜在问题：{len(defense_report.questions)}个（覆盖{len(set(q.category for q in defense_report.questions))}个维度）")
            print(f"  电梯演讲脚本：已生成（约2.5-3分钟）")
            print()

        # 保存答辩报告到输出目录
        from utils.helpers import ensure_dir, write_text_file
        defense_output_dir = OUTPUT_DIR / "current"
        ensure_dir(defense_output_dir)
        write_text_file(defense_output_dir / "defense_prep_report.md", defense_text)

        # ===== 阶段9：输出导出 =====
        self._print_stage(9, "多格式输出")
        self.output_exporter = OutputExporter()

        self.current_export = self.output_exporter.export_all(
            document=self.current_document,
            layout_engine=self.layout_engine,
            quality_report_text=quality_text,
        )

        if verbose:
            print(f"  [Dir] 输出目录：{self.current_export.output_dir}")
            print(f"  [MD] Markdown: {self.current_export.markdown_path.name}")
            print(f"  [HTML] HTML:     {self.current_export.html_path.name}")
            if self.current_export.pdf_path:
                print(f"  [PDF] PDF:      {self.current_export.pdf_path.name}")
            if self.current_export.docx_path:
                print(f"  [DOCX] Word:     {self.current_export.docx_path.name}")
            print()

        # ===== 阶段10：完成 =====
        self._print_stage(10, "[OK] 完成！")
        print(f"  策划书已生成完毕，可直接提交参赛。")
        print(f"  输出位置：{self.current_export.output_dir}")
        print()
        print("=" * 70)

        return True

    def run_demo(self) -> bool:
        """运行演示案例（模拟'芯光科技'项目）"""
        demo_data = {
            "competition_info": {
                "competition_name": "互联网+高教主赛道",
                "track": "高教主赛道-本科生创意组",
                "category": "创意组",
            },
            "project_material": {
                "project_name": "芯光科技——第三代半导体GaN功率芯片国产化引领者",
                "project_brief": (
                    "芯光科技聚焦于第三代半导体GaN（氮化镓）功率芯片的研发与产业化。"
                    "团队自主研发的'三阶梯度缓冲层'外延技术，有效解决了GaN-on-Si外延片"
                    "晶体质量低的核心难题，使位错密度降低了2个数量级。基于此技术开发的"
                    "p-GaN增强型功率开关器件，在阈值电压和比导通电阻等关键指标上超越"
                    "国际竞品英飞凌CoolGaN™系列。项目已申请发明专利8项，发表SCI论文5篇，"
                    "与比亚迪、蔚来等企业达成初步合作意向。"
                ),
                "tech_principles": (
                    "本团队创新性地提出'三阶梯度缓冲层'外延结构，通过引入AlN/GaN超晶格"
                    "应力调控层，有效降低了位错密度，使GaN-on-Si外延片的晶体质量提升了2个"
                    "数量级。基于此，我们设计了p-GaN增强型功率开关器件，其阈值电压达到3.2V，"
                    "比导通电阻仅为12mΩ·cm²，相较于国际竞品（英飞凌CoolGaN™：2.8V/15mΩ·cm²），"
                    "在低功耗场景下效率提升约18%。\n\n"
                    "系统由GaN外延材料生长模块、器件设计模块、封装测试模块三大核心构成。"
                    "在工艺层面，我们优化了MOCVD生长参数，将GaN薄膜的缺陷密度从传统的"
                    "10^9/cm²降至10^7/cm²级别，为高性能器件的制备奠定了材料基础。"
                ),
                "innovations": [
                    "三阶梯度缓冲层外延结构",
                    "AlN/GaN超晶格应力调控技术",
                    "p-GaN增强型功率开关器件设计",
                    "低缺陷密度MOCVD生长工艺",
                    "芯片-模组-方案三位一体商业模式",
                ],
                "tech_params": {
                    "阈值电压": "3.2V",
                    "比导通电阻": "12mΩ·cm²",
                    "位错密度": "10^7/cm²",
                    "能效比": "较竞品提升18%",
                    "可靠性（1000h老化）": "衰减<3%",
                },
                "market_data": (
                    "据Yole数据显示，2023年全球GaN功率器件市场规模达4.2亿美元，"
                    "预计2028年将突破20亿美元，年复合增长率超过35%。当前全球GaN功率芯片"
                    "市场被英飞凌、Navitas等海外巨头垄断，国产化率不足15%。国内新能源汽车、"
                    "5G基站、快充电源等领域对高性能GaN功率芯片的需求呈井喷式增长。"
                ),
                "cooperation_info": (
                    "已与比亚迪、蔚来达成初步合作意向，产品样品正在OBC（车载充电机）"
                    "场景下进行验证测试。与中科院某研究所建立了联合实验室，共享测试平台资源。"
                ),
            },
            "team_info": {
                "project_leader": "张明远",
                "team_members": [
                    {
                        "name": "张明远",
                        "major": "微电子学与固体电子学",
                        "degree": "博士研究生",
                        "role": "项目负责人/技术总监",
                        "achievements": "发表SCI论文12篇，申请发明专利5项"
                    },
                    {
                        "name": "李思涵",
                        "major": "材料科学与工程",
                        "degree": "博士研究生",
                        "role": "外延工艺负责人",
                        "achievements": "发表SCI论文8篇，获国家奖学金"
                    },
                    {
                        "name": "王浩然",
                        "major": "电子科学与技术",
                        "degree": "硕士研究生",
                        "role": "器件设计负责人",
                        "achievements": "全国大学生电子设计竞赛一等奖"
                    },
                    {
                        "name": "陈雨桐",
                        "major": "工商管理",
                        "degree": "硕士研究生",
                        "role": "市场运营负责人",
                        "achievements": "曾任职于知名投资机构，熟悉半导体产业链"
                    },
                ],
                "advisor_name": "赵建国",
                "advisor_title": "教授、博士生导师、国家杰出青年科学基金获得者",
                "advisor_achievements": (
                    "长期从事宽禁带半导体研究，主持国家自然科学基金重点项目、"
                    "国家重点研发计划等国家级项目8项，在Nature Electronics、IEEE EDL等"
                    "顶级期刊发表论文100余篇，获国家科技进步二等奖1项。"
                    "担任中国半导体行业协会功率半导体分会常务理事。"
                ),
                "past_awards": [
                    "2025年全国大学生集成电路创新创业大赛一等奖",
                    "2024年“挑战杯”省赛金奖",
                    "2024年研究生电子设计竞赛全国二等奖",
                ],
            },
            "doc_requirement": {
                "target_pages": 80,
                "color_theme": "deep_blue",
                "specific_formats": "需包含完整的图表索引和参考文献列表",
            },
            "evidence": {
                "patent_certificates": ["发明专利8项", "实用新型3项"],
                "software_certificates": ["GaN器件仿真设计软件V1.0"],
                "product_photos": ["GaN外延片实物照片", "功率器件芯片显微照片"],
                "experiment_photos": ["电学性能测试曲线图", "可靠性老化测试装置图"],
                "cooperation_agreements": ["比亚迪OBC项目合作意向书", "蔚来技术交流备忘录"],
            },
        }

        print("=" * 70)
        print("  [DEMO] 演示案例：芯光科技 - GaN功率芯片项目")
        print("=" * 70)
        print()

        return self.run(demo_data, verbose=True, auto_confirm=True)

    def _print_stage(self, num: int, title: str) -> None:
        """打印阶段标题"""
        print(f"━━━ 阶段{num}：{title} ━━━")
        print()


# ===== CLI入口 =====

def interactive_mode(agent: CompetitionAgent) -> None:
    """交互式CLI模式：逐步引导用户输入资料"""
    print("=" * 70)
    print("  [Award] 全自动竞赛策划智能体 - 交互式向导")
    print("=" * 70)
    print()
    print("请按照提示输入您的项目信息，系统将自动生成国奖级策划书。")
    print("（输入 'q' 可随时退出）")
    print()

    data = {
        "competition_info": {},
        "project_material": {},
        "team_info": {},
        "doc_requirement": {},
        "evidence": {},
    }

    # 类别1：赛事信息
    print("── 第1/5步：赛事组别信息 ──")
    print("支持的赛事：")
    for i, comp in enumerate(SUPPORTED_COMPETITIONS, 1):
        print(f"  {i}. {comp}")
    comp_choice = input("请输入赛事名称（或序号）：").strip()
    if comp_choice.lower() == 'q':
        return
    if comp_choice.isdigit():
        idx = int(comp_choice) - 1
        if 0 <= idx < len(SUPPORTED_COMPETITIONS):
            comp_choice = SUPPORTED_COMPETITIONS[idx]
    data["competition_info"]["competition_name"] = comp_choice

    # 类别2：项目资料
    print()
    print("── 第2/5步：项目核心资料 ──")
    data["project_material"]["project_name"] = input("项目名称【必填】：").strip()
    if data["project_material"]["project_name"].lower() == 'q':
        return
    print("项目简介【必填】（输入完成后按Ctrl+D或输入'END'结束）：")
    brief_lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            brief_lines.append(line)
        except EOFError:
            break
    data["project_material"]["project_brief"] = '\n'.join(brief_lines)

    print("技术原理与核心创新（可选，输入'END'结束）：")
    tech_lines = []
    while True:
        try:
            line = input()
            if line.strip() == 'END':
                break
            tech_lines.append(line)
        except EOFError:
            break
    if tech_lines:
        data["project_material"]["tech_principles"] = '\n'.join(tech_lines)

    # 简化：其余字段快速输入
    innovations_str = input("核心创新点（用逗号分隔）：").strip()
    if innovations_str and innovations_str != 'q':
        data["project_material"]["innovations"] = [i.strip() for i in innovations_str.split(',')]

    data["project_material"]["market_data"] = input("市场调研数据（可选）：").strip()

    # 类别3：团队信息
    print()
    print("── 第3/5步：团队信息 ──")
    data["team_info"]["project_leader"] = input("项目负责人姓名：").strip()
    data["team_info"]["advisor_name"] = input("指导教师姓名：").strip()
    data["team_info"]["advisor_title"] = input("指导教师职称/资历：").strip()
    data["team_info"]["advisor_achievements"] = input("指导教师主要成就（可选）：").strip()

    # 收集团队成员
    print("团队成员信息（输入'END'结束添加）：")
    team_members = []
    while True:
        name = input("  成员姓名（或输入'END'结束）：").strip()
        if name.upper() == 'END' or not name:
            break
        member = {"name": name}
        major = input(f"    {name}的专业：").strip()
        if major: member["major"] = major
        degree = input(f"    {name}的学历：").strip()
        if degree: member["degree"] = degree
        role = input(f"    {name}的分工（如技术研发、市场运营）：").strip()
        if role: member["role"] = role
        ach = input(f"    {name}的主要成就（可选）：").strip()
        if ach: member["achievements"] = ach
        team_members.append(member)
        print(f"  [OK] {name}已添加（当前{len(team_members)}人）")
    data["team_info"]["team_members"] = team_members

    awards_str = input("团队过往获奖（用逗号分隔，可选）：").strip()
    if awards_str:
        data["team_info"]["past_awards"] = [a.strip() for a in awards_str.split(',')]

    # 类别4：文稿要求
    print()
    print("── 第4/5步：文稿定制要求 ──")
    pages = input("目标页数（默认80）：").strip()
    if pages:
        data["doc_requirement"]["target_pages"] = int(pages)

    print("可选配色方案：")
    for key, name in SUPPORTED_THEMES.items():
        print(f"  {key}: {name}")
    theme = input("选择配色方案（默认deep_blue）：").strip()
    if theme and theme in SUPPORTED_THEMES:
        data["doc_requirement"]["color_theme"] = theme

    # 类别5：佐证
    print()
    print("── 第5/5步：佐证材料（可选） ──")
    patents = input("专利数量（如有）：").strip()
    if patents:
        data["evidence"]["patent_certificates"] = [f"专利{patents}项"]

    # 确认执行
    print()
    print("=" * 70)
    print("[INFO] 资料收集完毕，准备启动智能体...")
    print("=" * 70)
    input("按Enter键开始自动生成...")

    agent.run(data, verbose=True)


def main():
    parser = argparse.ArgumentParser(
        description="全自动竞赛策划智能体 - 自动生成国奖级竞赛策划书",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python main.py                交互式CLI模式
  python main.py --demo         运行演示案例
  python main.py --config customer.json  从配置文件加载
        """
    )
    parser.add_argument("--demo", action="store_true", help="运行演示案例")
    parser.add_argument("--config", type=str, help="从JSON配置文件加载客户数据")
    parser.add_argument("--api-key", type=str, help="Anthropic API密钥")
    parser.add_argument("--model", type=str, default=ANTHROPIC_MODEL, help="模型名称")
    parser.add_argument("--output", type=str, help="输出目录路径")

    args = parser.parse_args()

    # 初始化智能体
    agent = CompetitionAgent(
        api_key=args.api_key,
        model=args.model,
    )

    if args.output:
        import config
        config.OUTPUT_DIR = Path(args.output)

    # 运行模式
    if args.demo:
        # 演示模式
        success = agent.run_demo()
        if success:
            print("\n[OK] 演示案例运行成功！")
            print(f"查看输出：{agent.current_export.output_dir}")
    elif args.config:
        # 从配置文件加载
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"[FAIL] 配置文件不存在：{config_path}")
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            customer_data = json.load(f)

        success = agent.run(customer_data, verbose=True)
        if success:
            print("\n[OK] 策划书生成成功！")
            print(f"查看输出：{agent.current_export.output_dir}")
    else:
        # 交互式模式
        try:
            interactive_mode(agent)
        except KeyboardInterrupt:
            print("\n\n[BYE] 已退出。")
            return


if __name__ == "__main__":
    main()
