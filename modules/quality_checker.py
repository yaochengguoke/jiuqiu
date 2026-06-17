"""
模块8：质量检查与AI评审
- 全文数据一致性校验（与中央数据池比对）
- AI模拟评审官：从多维度打分
- 查重预检：标记高风险同质化段落
- 自动问题清单生成
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PLAGIARISM_THRESHOLD
from modules.material_parser import CentralDataPool
from modules.content_generator import GeneratedDocument
from utils.helpers import extract_numbers, compare_numbers_across_chapters


@dataclass
class ConsistencyIssue:
    """数据一致性问题"""
    chapter: str
    field: str
    expected_value: str
    found_value: str
    severity: str  # "critical", "warning", "info"


@dataclass
class PlagiarismWarning:
    """查重警告"""
    section: str
    text_snippet: str
    risk_level: str
    suggestion: str


@dataclass
class QualityReport:
    """质量检查综合报告"""
    # 数据一致性
    consistency_issues: List[ConsistencyIssue]
    consistency_score: float  # 0-100

    # AI评审
    ai_judge_result: Optional[Dict[str, Any]] = None
    overall_score: Optional[float] = None
    is_award_level: bool = False

    # 查重
    plagiarism_warnings: List[PlagiarismWarning] = field(default_factory=list)
    plagiarism_risk: str = "low"  # "low", "medium", "high"

    # 文档完整性
    missing_count: int = 0
    total_chapters: int = 0

    # 建议
    critical_issues: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)

    checked_at: str = ""


class QualityChecker:
    """
    质量检查与AI评审模块

    职责：
    1. 数据一致性校验：检查全文数字与中央数据池是否一致
    2. AI模拟评审：多维度打分预估竞赛成绩
    3. 查重预检：识别模板化过重的段落
    4. 生成改进建议清单
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def run_full_check(
        self,
        document: GeneratedDocument,
        data_pool: CentralDataPool,
    ) -> QualityReport:
        """
        运行完整质量检查流程

        Args:
            document: 生成的策划书文档
            data_pool: 中央数据池

        Returns:
            QualityReport: 完整的质量检查报告
        """
        report = QualityReport(
            consistency_issues=[],
            consistency_score=100.0,
            total_chapters=len(document.chapters),
            missing_count=len(document.missing_sections),
            checked_at=datetime.now().isoformat(),
        )

        # 1. 数据一致性检查
        report.consistency_issues = self._check_consistency(document, data_pool)
        if report.consistency_issues:
            critical_count = sum(1 for i in report.consistency_issues if i.severity == "critical")
            report.consistency_score = max(0, 100 - critical_count * 15 - len(report.consistency_issues) * 3)

        # 2. 查重预检
        report.plagiarism_warnings = self._check_plagiarism(document)
        high_risk = sum(1 for w in report.plagiarism_warnings if w.risk_level == "high")
        if high_risk > 3:
            report.plagiarism_risk = "high"
        elif high_risk > 0:
            report.plagiarism_risk = "medium"

        # 3. AI模拟评审（如果LLM可用）
        if self.llm_client:
            try:
                full_text = document.get_full_text()
                judge_result = self.llm_client.judge_content(full_text, {})
                report.ai_judge_result = judge_result
                report.overall_score = judge_result.get("总分", 0)
                report.is_award_level = judge_result.get("是否达到国奖水准", False)

                if not report.is_award_level:
                    report.improvement_suggestions = judge_result.get("关键改进建议", [])
            except Exception as e:
                print(f"[QualityChecker] AI评审失败: {e}")
        else:
            # 演示模式下的简单评分
            report.overall_score = self._demo_scoring(document)
            report.ai_judge_result = {
                "创新性": {"score": 22, "comment": "基于已有创新点评估"},
                "商业价值": {"score": 17, "comment": "商业模式清晰"},
                "社会价值": {"score": 14, "comment": "需加强国家战略呼应"},
                "团队实力": {"score": 13, "comment": "团队结构合理"},
                "文档规范": {"score": 14, "comment": "结构完整"},
                "逻辑一致性": {"score": report.consistency_score / 10, "comment": ""},
                "总分": report.overall_score,
                "关键改进建议": report.improvement_suggestions,
                "是否达到国奖水准": report.overall_score >= 90,
            }

        # 4. 汇总关键问题
        report.critical_issues = self._summarize_critical(report)

        return report

    def _check_consistency(
        self,
        document: GeneratedDocument,
        data_pool: CentralDataPool,
    ) -> List[ConsistencyIssue]:
        """全文数据一致性校验"""
        issues = []

        # 提取文档中所有数字
        chapters_dict = {ch.chapter_title: ch.content_markdown for ch in document.chapters}

        # 跨章节一致性对比
        conflicts = compare_numbers_across_chapters(chapters_dict)
        for conflict in conflicts:
            for occ in conflict["occurrences"]:
                issues.append(ConsistencyIssue(
                    chapter=occ["chapter"],
                    field=f"数值: {conflict['value']}",
                    expected_value=conflict["value"],
                    found_value=f"在{occ['chapter']}中上下文中检测到不一致",
                    severity="critical",
                ))

        # 与中央数据池对比关键数据
        full_text = document.get_full_text()
        # 从data_pool直接提取数值实体（而非调用MaterialParser的方法）
        central_numbers = {}
        for key, entities in data_pool.numeric_entities.items():
            if entities:
                values = [float(e.value) for e in entities if e.value.replace('.', '').isdigit()]
                if values:
                    central_numbers[key] = str(sum(values) / len(values))

        for key, expected_val in central_numbers.items():
            if key.replace('.', '').isdigit():
                # 在正文中搜索该数字
                pattern = re.escape(key)
                if not re.search(pattern, full_text):
                    issues.append(ConsistencyIssue(
                        chapter="全文",
                        field=f"中央数据池数值: {key}",
                        expected_value=expected_val,
                        found_value="未在正文中找到",
                        severity="warning",
                    ))

        return issues

    def _check_plagiarism(self, document: GeneratedDocument) -> List[PlagiarismWarning]:
        """简单查重预检：检测模板痕迹过重的段落"""
        warnings = []

        # 高频模板短语（过度使用国奖模板的标记）
        template_phrases = [
            ("被列入国家战略性新兴产业", "high", "建议替换为更具体的政策表述"),
            ("年复合增长率超过", "medium", "确保此增长率数据在素材中有据可查"),
            ("被XX、XX等海外巨头垄断", "medium", "确认竞品名称与客户素材一致"),
            ("不仅是一项商业机遇，更是国家战略需求", "high", "这是高频模板句，建议个性化改写"),
            ("三位一体的商业模式", "medium", "考虑使用客户项目特色的商业模式命名"),
            ("填补了国内空白", "medium", "需有确实证据支撑，勿滥用此表述"),
            ("实现了从0到1的突破", "high", "过度使用的宣传语，建议量化具体成果"),
            ("卡脖子", "medium", "合理使用但不要堆砌政策热词"),
            ("国产化率不足", "medium", "确认具体数据来源"),
        ]

        full_text = document.get_full_text()

        for phrase, risk, suggestion in template_phrases:
            count = full_text.count(phrase)
            if count >= 2:
                # 查找短语上下文
                for match in re.finditer(re.escape(phrase), full_text):
                    start = max(0, match.start() - 30)
                    end = min(len(full_text), match.end() + 30)
                    snippet = full_text[start:end].replace('\n', ' ')

                    warnings.append(PlagiarismWarning(
                        section=self._find_section(full_text, match.start()),
                        text_snippet=snippet,
                        risk_level=risk,
                        suggestion=suggestion,
                    ))

        # 计算整体风险
        high_count = sum(1 for w in warnings if w.risk_level == "high")
        if high_count > 3:
            for w in warnings:
                if w.risk_level == "high":
                    w.risk_level = "critical"

        return warnings[:10]  # 最多显示10条

    def _find_section(self, full_text: str, position: int) -> str:
        """根据文本位置确定所属章节"""
        text_before = full_text[:position]
        sections = list(re.finditer(r'^## (.+)$', text_before, re.MULTILINE))
        if sections:
            return sections[-1].group(1)
        return "未知章节"

    def _demo_scoring(self, document: GeneratedDocument) -> float:
        """演示模式下的评分（更合理的校准）"""
        # 基础分：章节完整
        score = 70.0 if len(document.chapters) >= 8 else 60.0

        # 字数贡献（满分+20）
        words = document.total_word_count
        if words >= 15000:
            score += 20
        elif words >= 8000:
            score += 15
        elif words >= 5000:
            score += 10
        elif words >= 3000:
            score += 5

        # 缺失项惩罚（区分关键/非关键缺失）
        missing = len(document.missing_sections)
        if missing <= 3:
            score += 5  # 几乎完整
        elif missing <= 10:
            score += 0  # 正常范围
        elif missing <= 20:
            score -= 2  # 轻微扣分
        else:
            score -= 5  # 较多缺失

        return max(0, min(100, score))

    def _summarize_critical(self, report: QualityReport) -> List[str]:
        """汇总最严重的问题"""
        critical = []

        # 数据一致性的关键问题
        for issue in report.consistency_issues:
            if issue.severity == "critical":
                critical.append(
                    f"[数据矛盾] {issue.chapter}中的{issue.field}："
                    f"期望={issue.expected_value}，实际={issue.found_value}"
                )

        # 查重高风险
        if report.plagiarism_risk == "high":
            critical.append(
                "[查重风险] 检测到多处高频模板句式，建议进行个性化改写以降低查重率"
            )

        # 缺失项过多
        if report.missing_count > 5:
            critical.append(
                f"[内容不完整] 全文有{report.missing_count}处信息缺失，"
                "建议客户补充关键资料后重新生成"
            )

        # AI评审不达标
        if report.ai_judge_result and not report.is_award_level and report.overall_score:
            shortfall = 90 - report.overall_score
            critical.append(
                f"[未达国奖水准] AI评审得分{report.overall_score}，距国奖线差{shortfall}分"
            )

        return critical

    def print_report(self, report: QualityReport) -> str:
        """格式化输出质量报告"""
        lines = [
            "=" * 60,
            "[Chart] 质量检查与AI评审报告",
            "=" * 60,
            f"检查时间：{report.checked_at}",
            f"检查章节：{report.total_chapters}章",
            f"缺失标记：{report.missing_count}处",
            "",
        ]

        # 总体评分
        if report.overall_score:
            score_bar = "█" * int(report.overall_score / 5) + "░" * (20 - int(report.overall_score / 5))
            level = "[Award] 国奖水准" if report.is_award_level else "[WARN] 未达国奖线"
            lines.append(f"AI评审总分：{report.overall_score:.1f}/100 {level}")
            lines.append(f"[{score_bar}]")
            lines.append("")

        # 各维度评分
        if report.ai_judge_result:
            lines.append("维度评分：")
            for dim, result in report.ai_judge_result.items():
                if isinstance(result, dict) and "score" in result:
                    lines.append(f"  {dim}: {result['score']}分 - {result.get('comment', '')}")
            lines.append("")

        # 数据一致性
        lines.append(f"数据一致性：{report.consistency_score:.0f}/100")
        if report.consistency_issues:
            lines.append(f"  发现{len(report.consistency_issues)}处问题：")
            for issue in report.consistency_issues[:5]:
                icon = {"critical": "[FAIL]", "warning": "[WARN]", "info": "[i]"}.get(issue.severity, "•")
                lines.append(f"  {icon} [{issue.chapter}] {issue.field}")
        else:
            lines.append("  [OK] 全文数据一致，未发现矛盾")
        lines.append("")

        # 查重
        lines.append(f"查重风险等级：{report.plagiarism_risk}")
        if report.plagiarism_warnings:
            for w in report.plagiarism_warnings[:5]:
                lines.append(f"  [{w.risk_level}] {w.suggestion}")
                lines.append(f"       原文：「{w.text_snippet[:60]}...」")
        lines.append("")

        # 关键问题
        if report.critical_issues:
            lines.append("[ALERT] 需要关注的关键问题：")
            for issue in report.critical_issues:
                lines.append(f"  • {issue}")
        else:
            lines.append("[OK] 未发现关键问题，质量达标")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)
