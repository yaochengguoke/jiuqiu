"""基础单元测试"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_input_processor():
    from modules.input_processor import InputProcessor
    ip = InputProcessor()
    raw = {"competition_info":{"competition_name":"互联网+高教主赛道"},"project_material":{"project_name":"测试","project_brief":"测试简介"},"team_info":{"project_leader":"张三","team_members":[]},"doc_requirement":{},"evidence":{}}
    sub, comp = ip.process_submission(raw)
    assert comp.score >= 0.5, f"完整度偏低: {comp.score}"

def test_template_matcher():
    from modules.template_matcher import TemplateMatcher
    tm = TemplateMatcher()
    t = tm.match_template("互联网+高教主赛道")
    assert len(t.chapters) >= 7, f"章节数异常: {len(t.chapters)}"

def test_material_parser():
    from modules.material_parser import MaterialParser
    mp = MaterialParser()
    kb = {"project_brief":"测试项目简介，技术指标达到99.9%，市场规模100亿元","tech_principles":"核心技术描述","project_name":"测试"}
    pool = mp.parse_and_build_pool(kb, [{"id":"test","title":"测试"}])
    assert pool.project_name == "测试"

def test_completeness_checker():
    from modules.completeness_checker import CompletenessChecker
    from modules.material_parser import CentralDataPool
    cc = CompletenessChecker()
    dp = CentralDataPool(project_name="测试")
    dp.tech_pool = {"tech_principles":"测试技术原理"}
    dp.market_pool = {"market_data_raw":"测试市场数据"}
    dp.team_pool = {"team_members":[{"name":"张三"}],"project_leader":"张三"}
    r = cc.check_all_chapters(dp, [{"id":"technology","title":"核心技术"},{"id":"team_intro","title":"团队"}])
    assert r.overall_status in ("ready","partial"), r.overall_status

def test_content_generator():
    from modules.content_generator import ContentGenerator
    from modules.material_parser import CentralDataPool
    cg = ContentGenerator()
    dp = CentralDataPool(project_name="测试项目")
    dp.tech_pool = {"innovations":["创新点1"],"tech_principles":"测试原理","technology_name":"测试技术"}
    dp.market_pool = {"market_data_raw":"市场规模100亿"}
    dp.team_pool = {"team_members":[{"name":"张三"}],"project_leader":"张三","total_patents":5,"total_papers":3,"past_awards":["奖项1"],"advisor_name":"李四","advisor_title":"教授"}
    dp.evidence_pool = {}
    from modules.template_matcher import TemplateMatcher
    tm = TemplateMatcher()
    t = tm.match_template("互联网+高教主赛道")
    doc = cg.generate_all_chapters(t, dp)
    assert doc.total_word_count > 100, f"字数异常: {doc.total_word_count}"
    assert len(doc.chapters) >= 7

def test_plagiarism_checker():
    from modules.plagiarism_checker import PlagiarismChecker
    pc = PlagiarismChecker()
    r = pc.check("这是一个测试文本，包含核心技术突破和年复合增长率超过预期。")
    assert r.checked_chars > 0

def test_ppt_generator():
    from modules.ppt_generator import PPTGenerator
    from pathlib import Path
    ppg = PPTGenerator()
    text = "## 项目背景\n测试内容。\n## 核心技术\n创新点描述。\n## 团队\n团队成员信息。"
    out = ppg.generate_ppt(text, "测试", Path("test_out.pptx"))
    assert out and out.exists(), "PPT未生成"
    out.unlink()

def test_defense_prep():
    from modules.defense_prep import DefensePrep
    dp = DefensePrep()
    text = "## 项目背景\n测试市场数据。\n## 核心技术\n自主研发AI算法，效率提升30%。"
    r = dp.generate_defense_prep(text, "测试")
    assert len(r.questions) > 0
    s = dp.generate_summary(text, "测试")
    assert len(s) > 50

def test_llm_client():
    from utils.llm_client import LLMClient
    c = LLMClient(api_key="sk-test")
    # 无真实key时is_available检查
    assert isinstance(c.is_available, bool)

if __name__ == "__main__":
    tests = [f for f in dir() if f.startswith("test_")]
    passed = 0
    for t in tests:
        try:
            globals()[t]()
            print(f"  PASS {t}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {t}: {e}")
    print(f"\n{passed}/{len(tests)} passed")
