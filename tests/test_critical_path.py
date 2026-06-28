# -*- coding: utf-8 -*-
"""
关键路径单元测试: 输入处理 → 模板匹配 → 完整度检查
不需要 API 密钥，纯离线测试
"""
import sys, json, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SUPPORTED_COMPETITIONS, get_competition_metadata
from modules.input_processor import InputProcessor, CompletenessLevel
from modules.template_matcher import TemplateMatcher
from modules.completeness_checker import CompletenessChecker


class TestConfigDynamicLoad(unittest.TestCase):
    """#4: 赛事信息从 index.json 动态加载"""

    def test_competitions_loaded_from_index(self):
        self.assertGreaterEqual(len(SUPPORTED_COMPETITIONS), 8)
        self.assertIn("互联网+高教主赛道", SUPPORTED_COMPETITIONS)
        self.assertIn("挑战杯科技发明A类", SUPPORTED_COMPETITIONS)

    def test_metadata_returns_full_info(self):
        meta = get_competition_metadata()
        self.assertIn("互联网+高教主赛道", meta)
        self.assertEqual(meta["互联网+高教主赛道"]["template_file"], "internet_plus_main.json")
        self.assertEqual(meta["互联网+高教主赛道"]["typical_pages"], 80)
        self.assertEqual(meta["互联网+高教主赛道"]["visual_style"], "deep_blue")

    def test_all_competitions_have_template_files(self):
        meta = get_competition_metadata()
        templates_dir = Path(__file__).parent.parent / "knowledge_base" / "templates"
        for name, info in meta.items():
            tpl_path = templates_dir / info["template_file"]
            self.assertTrue(tpl_path.exists(),
                            f"{name}: template file {info['template_file']} not found")


class TestInputProcessor(unittest.TestCase):
    """输入处理: 完整度评估 + 分级响应"""

    def setUp(self):
        self.processor = InputProcessor()

    def test_full_submission_passes(self):
        data = {
            "competition_info": {"competition_name": "互联网+高教主赛道"},
            "project_material": {
                "project_name": "测试项目",
                "project_brief": "这是一个测试项目的简介，内容足够长以满足最低要求。",
                "tech_principles": "核心技术原理描述",
                "market_data": "市场规模数据",
            },
            "team_info": {
                "project_leader": "张三",
                "team_members": [{"name": "张三"}, {"name": "李四"}],
            },
            "doc_requirement": {},
            "evidence": {},
        }
        submission, report = self.processor.process_submission(data)
        self.assertIsNotNone(submission)
        self.assertIsNotNone(report)
        self.assertIn(report.level, [CompletenessLevel.FULL, CompletenessLevel.PARTIAL])

    def test_missing_project_brief_generates_warning(self):
        data = {
            "competition_info": {"competition_name": "互联网+高教主赛道"},
            "project_material": {"project_name": "测试项目", "project_brief": ""},
            "team_info": {"project_leader": "", "team_members": []},
            "doc_requirement": {},
            "evidence": {},
        }
        submission, report = self.processor.process_submission(data)
        self.assertLess(report.score, 0.7)  # 有project_name+team结构就有基础分

    def test_competition_info_defaults_to_empty(self):
        data = {
            "competition_info": {"competition_name": "互联网+高教主赛道"},
            "project_material": {"project_name": "测试", "project_brief": "简介内容"},
            "team_info": {"project_leader": "张三", "team_members": [{"name": "张三"}]},
            "doc_requirement": {},
            "evidence": {},
        }
        submission, report = self.processor.process_submission(data)
        self.assertIsNotNone(submission)
        self.assertEqual(submission.competition_info.competition_name, "互联网+高教主赛道")

    def test_empty_doc_and_evidence_handled(self):
        data = {
            "competition_info": {"competition_name": "挑战杯科技发明A类"},
            "project_material": {
                "project_name": "项目名",
                "project_brief": "这是一个有足够内容的项目简介用于测试。",
            },
            "team_info": {
                "project_leader": "负责人",
                "team_members": [{"name": "成员一"}],
            },
            "doc_requirement": {},
            "evidence": {},
        }
        submission, report = self.processor.process_submission(data)
        self.assertIsNotNone(submission)
        # doc_requirement and evidence are optional — score should still be decent
        self.assertGreater(report.score, 0.3)


class TestTemplateMatcher(unittest.TestCase):
    """模板匹配: 精确匹配 + 模糊匹配 + fallback"""

    def setUp(self):
        self.matcher = TemplateMatcher()

    def test_exact_match_returns_correct_template(self):
        template = self.matcher.match_template("互联网+高教主赛道")
        self.assertEqual(template.competition_name, "互联网+高教主赛道")
        self.assertFalse(template.fallback_used)
        self.assertGreater(len(template.chapters), 0)

    def test_all_supported_competitions_match(self):
        for name in SUPPORTED_COMPETITIONS:
            template = self.matcher.match_template(name)
            self.assertIsNotNone(template)
            self.assertGreater(len(template.chapters), 0,
                               f"{name}: template has no chapters")

    def test_unknown_competition_falls_back(self):
        template = self.matcher.match_template("不存在的赛事名称XYZ")
        self.assertIsNotNone(template)
        self.assertTrue(template.fallback_used)
        self.assertGreater(len(template.chapters), 0)

    def test_template_has_required_sections(self):
        template = self.matcher.match_template("互联网+高教主赛道")
        chapter_titles = [ch.get("title", "") for ch in template.chapters]
        self.assertGreater(len(chapter_titles), 5)  # 至少5章
        self.assertTrue(all(t for t in chapter_titles), "All chapters should have titles")

    def test_template_visual_style_exists(self):
        template = self.matcher.match_template("节能减排本科组")
        self.assertIsNotNone(template.visual_style)
        self.assertIn("colors", template.visual_style or {})
        self.assertIn("primary", template.visual_style.get("colors", {}))


class TestCompletenessChecker(unittest.TestCase):
    """完整度检查: 逐章扫描缺失"""

    def setUp(self):
        self.matcher = TemplateMatcher()
        self.checker = CompletenessChecker(llm_client=None)

    def _make_data_pool(self, project_name="测试项目", tech_principles="技术原理描述",
                        market_data="市场规模100亿", team_members=None):
        from modules.material_parser import CentralDataPool
        pool = CentralDataPool()
        pool.project_name = project_name
        pool.tech_pool = {
            "technology_name": "测试技术",
            "key_modules": ["模块A", "模块B"],
            "innovations": ["创新1", "创新2"],
            "tech_principles": tech_principles,
            "tech_params": {"参数1": "值1"},
            "papers": ["论文1"],
            "patents": ["专利1"],
            "softwares": ["软著1"],
        }
        pool.market_pool = {
            "target_customers": ["客户A"],
            "market_size": "100亿",
            "market_data": market_data,
            "industry_analysis": "行业分析",
            "cooperation_info": "合作信息",
            "market_data_raw": market_data,
            "cooperation_info_raw": "合作原始数据",
        }
        pool.evidence_pool = {
            "patents": ["发明专利5项"],
            "papers": ["SCI论文3篇"],
            "product_photos": ["实物照片"],
            "experiment_photos": ["测试装置图"],
            "cooperation_agreements": ["合作意向书"],
        }
        pool.team_pool = {
            "project_leader": "张三",
            "team_members": team_members or [
                {"name": "张三", "major": "微电子", "degree": "博士", "role": "负责人"},
                {"name": "李四", "major": "材料", "degree": "硕士", "role": "研发"},
            ],
            "advisor_name": "王教授",
            "advisor_title": "博士生导师",
            "advisor_achievements": "国家杰青",
            "past_awards": ["一等奖"],
        }
        pool.numeric_entities = []
        return pool

    def test_full_data_passes_all_chapters(self):
        template = self.matcher.match_template("互联网+高教主赛道")
        pool = self._make_data_pool()
        report = self.checker.check_all_chapters(
            data_pool=pool, template_chapters=template.chapters)
        self.assertTrue(report.can_proceed)

    def test_minimal_data_still_checks(self):
        template = self.matcher.match_template("互联网+高教主赛道")
        pool = self._make_data_pool(tech_principles="", market_data="")
        report = self.checker.check_all_chapters(
            data_pool=pool, template_chapters=template.chapters)
        self.assertIsNotNone(report)

    def test_different_competitions_all_checkable(self):
        for name in SUPPORTED_COMPETITIONS[:3]:
            template = self.matcher.match_template(name)
            pool = self._make_data_pool()
            report = self.checker.check_all_chapters(
                data_pool=pool, template_chapters=template.chapters)
            self.assertIsNotNone(report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
