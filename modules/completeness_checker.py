"""
模块4：资料完整度分级响应检查器
- 对照模板大纲检查各章节所需素材是否齐全
- 分级响应：完整→直接写、部分→引导补全、严重→暂缓
- 生成结构化问题清单引导客户补充
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .material_parser import CentralDataPool


class ChapterStatus(str, Enum):
    READY = "ready"           # 素材齐全，可直接写作
    PARTIAL = "partial"       # 部分缺失，可写作但需标记【待补充】
    BLOCKED = "blocked"       # 关键素材缺失，暂不写作


@dataclass
class ChapterCheckResult:
    """单个章节的素材检查结果"""
    chapter_id: str
    chapter_title: str
    status: ChapterStatus
    required_elements: List[str]
    available_elements: List[str]
    missing_elements: List[str]
    suggested_questions: List[str]  # 引导客户补充的问题


@dataclass
class CompletenessCheckReport:
    """完整度检查总报告"""
    overall_status: str  # "ready", "partial", "insufficient"
    chapters_check: List[ChapterCheckResult]
    missing_critical_data: List[str]
    question_list: List[str]  # 统一的客户问题清单
    can_proceed: bool
    recommendation: str


class CompletenessChecker:
    """
    资料完整度分级响应检查器

    职责：
    1. 对照模板大纲逐章检查素材覆盖度
    2. 识别关键数据缺口
    3. 生成引导式问题清单
    4. 决定是否启动写作流程
    """

    # 各章节对应的数据池关键字段映射
    CHAPTER_DATA_REQUIREMENTS = {
        "executive_summary": {
            "critical": ["project_name", "project_brief"],
            "expected": ["innovations", "tech_params", "past_awards"],
            "nice_to_have": ["market_size", "patents"],
        },
        "background": {
            "critical": ["project_brief"],
            "expected": ["market_data", "industry_analysis", "tech_principles"],
            "nice_to_have": ["papers", "patents"],
        },
        "technology": {
            "critical": ["tech_principles"],
            "expected": ["innovations", "tech_params", "patents", "papers"],
            "nice_to_have": ["tech_principles", "softwares"],
        },
        "product_design": {
            "critical": ["project_brief", "tech_principles"],
            "expected": ["product_photos", "tech_params"],
            "nice_to_have": ["experiment_photos", "cooperation_info"],
        },
        "market_analysis": {
            "critical": ["market_data"],
            "expected": ["industry_analysis", "cooperation_info", "project_brief"],
            "nice_to_have": ["cooperation_agreements"],
        },
        "team_intro": {
            "critical": ["team_members", "project_leader"],
            "expected": ["past_awards", "advisor_name", "advisor_title"],
            "nice_to_have": ["advisor_achievements"],
        },
        "financial": {
            "critical": ["market_data_raw"],
            "expected": ["cooperation_info_raw", "project_name"],
            "nice_to_have": ["cooperation_agreements"],
        },
        "future_plan": {
            "critical": ["project_name"],
            "expected": ["tech_principles", "market_data_raw"],
            "nice_to_have": ["cooperation_info_raw", "innovations"],
        },
    }

    def __init__(self, llm_client=None):
        """
        Args:
            llm_client: LLM客户端，用于生成引导式问题。None则使用简单模板。
        """
        self.llm_client = llm_client

    def check_all_chapters(
        self,
        data_pool: CentralDataPool,
        template_chapters: List[Dict[str, Any]],
    ) -> CompletenessCheckReport:
        """
        检查所有章节的素材完整度

        Args:
            data_pool: 中央数据池
            template_chapters: 模板章节配置

        Returns:
            CompletenessCheckReport: 完整度检查报告
        """
        chapters_check = []
        all_missing = []
        all_questions = []
        blocked_count = 0

        for chapter in template_chapters:
            chapter_id = chapter.get("id", "")
            chapter_title = chapter.get("title", "")

            result = self._check_chapter(chapter_id, chapter_title, data_pool)
            chapters_check.append(result)

            if result.status == ChapterStatus.BLOCKED:
                blocked_count += 1

            all_missing.extend(result.missing_elements)
            all_questions.extend(result.suggested_questions)

        # 总体判定
        total_chapters = len(template_chapters) or 1
        if blocked_count == 0:
            overall_status = "ready"
            can_proceed = True
            recommendation = "所有章节素材齐全或仅有轻微缺失，可以启动完整写作流程。"
        elif blocked_count <= total_chapters * 0.3:
            overall_status = "partial"
            can_proceed = True
            recommendation = (
                f"有{blocked_count}个章节存在关键素材缺失，"
                "将先基于已有信息写作，缺失部分标记为【待补充】。\n"
                "建议客户根据问题清单补充后重新生成对应章节。"
            )
        else:
            overall_status = "insufficient"
            can_proceed = False
            recommendation = (
                f"有{blocked_count}个章节存在严重素材缺失（>30%），"
                "建议客户先补充关键资料后再启动生成。\n"
                "系统将生成详细的问题清单。"
            )

        # 去重缺失项
        unique_missing = list(dict.fromkeys(all_missing))
        unique_questions = list(dict.fromkeys(all_questions))

        return CompletenessCheckReport(
            overall_status=overall_status,
            chapters_check=chapters_check,
            missing_critical_data=unique_missing,
            question_list=unique_questions,
            can_proceed=can_proceed,
            recommendation=recommendation,
        )

    def _check_chapter(
        self,
        chapter_id: str,
        chapter_title: str,
        data_pool: CentralDataPool,
    ) -> ChapterCheckResult:
        """
        检查单个章节的素材覆盖度

        判定规则：
        - 关键字段全部缺失 → BLOCKED
        - 关键字段齐全，部分期望字段缺失 → PARTIAL
        - 关键+期望字段基本齐全 → READY
        """
        requirements = self.CHAPTER_DATA_REQUIREMENTS.get(
            chapter_id,
            {"critical": [], "expected": [], "nice_to_have": []}
        )

        # 合并所有池为一个扁平字典以便查询
        all_data = {
            # 项目级基础字段
            "project_name": data_pool.project_name,
            "project_brief": data_pool.tech_pool.get("tech_principles", ""),
        }
        all_data.update(data_pool.tech_pool)
        all_data.update(data_pool.market_pool)
        all_data.update(data_pool.team_pool)
        all_data.update(data_pool.evidence_pool)

        # 字段名映射（兼容不同的命名方式）
        field_aliases = {
            "market_data": ["market_data", "market_data_raw", "market_size"],
            "industry_analysis": ["industry_analysis", "industry_analysis_raw"],
            "cooperation_info": ["cooperation_info", "cooperation_info_raw"],
            "cooperation_agreements": ["cooperation_agreements"],
            "tech_principles": ["tech_principles"],
            "innovations": ["innovations"],
            "tech_params": ["tech_params"],
            "patents": ["patents"],
            "papers": ["papers"],
            "softwares": ["softwares"],
            "team_members": ["team_members"],
            "project_leader": ["project_leader"],
            "past_awards": ["past_awards"],
            "advisor_name": ["advisor_name"],
            "advisor_title": ["advisor_title"],
            "advisor_achievements": ["advisor_achievements"],
            "product_photos": ["product_photos"],
            "experiment_photos": ["experiment_photos"],
            "market_size": ["market_size", "market_data_raw"],
        }

        # 将别名字段的值补充到all_data中
        for canonical_name, aliases in field_aliases.items():
            if not self._has_data(all_data, canonical_name):
                for alias in aliases:
                    if self._has_data(all_data, alias):
                        all_data[canonical_name] = all_data[alias]
                        break

        # 检查关键字段
        critical_missing = []
        for field in requirements.get("critical", []):
            if not self._has_data(all_data, field):
                critical_missing.append(f"[关键] {field}")

        # 检查期望字段
        expected_missing = []
        expected_available = []
        for field in requirements.get("expected", []):
            if self._has_data(all_data, field):
                expected_available.append(field)
            else:
                expected_missing.append(f"[期望] {field}")

        # 检查锦上添花字段
        nice_available = []
        for field in requirements.get("nice_to_have", []):
            if self._has_data(all_data, field):
                nice_available.append(field)

        # 判定状态
        if len(critical_missing) >= len(requirements.get("critical", [])) * 0.5:
            if len(requirements.get("critical", [])) > 0:
                status = ChapterStatus.BLOCKED
            else:
                status = ChapterStatus.PARTIAL
        elif expected_missing:
            status = ChapterStatus.PARTIAL
        else:
            status = ChapterStatus.READY

        # 生成引导式问题
        all_missing = critical_missing + expected_missing
        questions = self._generate_questions(chapter_title, all_missing)

        return ChapterCheckResult(
            chapter_id=chapter_id,
            chapter_title=chapter_title,
            status=status,
            required_elements=requirements.get("critical", []) + requirements.get("expected", []),
            available_elements=expected_available + nice_available,
            missing_elements=all_missing,
            suggested_questions=questions,
        )

    def _has_data(self, data_dict: Dict[str, Any], field: str) -> bool:
        """检查数据池中是否有某个字段的有效数据"""
        value = data_dict.get(field)
        if value is None:
            return False
        if isinstance(value, str) and len(value.strip()) == 0:
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True

    def _generate_questions(self, chapter_title: str, missing: List[str]) -> List[str]:
        """为缺失项生成引导式问题"""
        if not missing:
            return []

        if self.llm_client:
            try:
                return self.llm_client.generate_questions_for_missing(missing)
            except Exception:
                pass

        # 模板化问题生成
        questions = []
        question_templates = {
            "tech_principles": f"请问您在{chapter_title}中涉及的核心技术原理是什么？请详细描述技术路线和关键工艺。",
            "market_data": f"关于{chapter_title}，您是否已有市场调研数据？如目标市场规模、增长率、竞争格局等。",
            "innovations": "您的项目有哪些核心创新点？请列出3-5个最重要的技术创新。",
            "tech_params": "请提供关键的技术性能参数，如效率、精度、速度等具体数值指标。",
            "patents": "项目是否已申请专利？请提供专利名称、类型和申请/授权情况。",
            "papers": "团队是否发表了相关学术论文？请提供论文标题、期刊和发表时间。",
            "past_awards": "团队过往获得过哪些竞赛奖项或荣誉？请列出最重要的3-5项。",
            "team_members": "请补充团队成员的详细信息（姓名、专业、学历、分工、成就）。",
            "project_leader": "请提供项目负责人的详细信息。",
            "advisor_name": "请补充指导老师的姓名和基本信息。",
            "advisor_achievements": "请介绍指导老师的主要学术成就和行业影响力。",
            "product_photos": "是否有产品样机或原型系统的照片？请提供以便在策划书中展示。",
            "cooperation_info": "项目是否已有合作企业或落地应用？请提供合作详情。",
            "cooperation_agreements": "是否有校企合作协议或落地证明文件？",
            "industry_analysis": "请提供您对所属行业的分析，包括产业链位置和发展趋势。",
            "market_size": "请补充目标市场的规模数据，最好引用权威第三方报告。",
        }

        for item in missing:
            # 提取字段名（去掉前缀标记）
            field_name = item.replace("[关键] ", "").replace("[期望] ", "").strip()
            if field_name in question_templates:
                questions.append(question_templates[field_name])
            else:
                questions.append(f"请补充 {chapter_title} 相关的 {field_name} 信息。")

        return questions

    def print_report(self, report: CompletenessCheckReport) -> str:
        """格式化打印完整度报告"""
        lines = [
            "=" * 60,
            "[Chart] 素材完整度检查报告",
            "=" * 60,
            f"总体状态：{report.overall_status}",
            f"是否可继续：{'[OK] 是' if report.can_proceed else '[FAIL] 否'}",
            f"\n{report.recommendation}\n",
        ]

        for ch in report.chapters_check:
            icon = {"ready": "[OK]", "partial": "[WARN]", "blocked": "[FAIL]"}.get(ch.status, "[?]")
            lines.append(f"{icon} {ch.chapter_title} ({ch.status})")
            if ch.missing_elements:
                for m in ch.missing_elements:
                    lines.append(f"   ↳ 缺失: {m}")

        if report.question_list:
            lines.append("\n" + "-" * 40)
            lines.append("[INFO] 请客户补充以下信息：")
            for i, q in enumerate(report.question_list, 1):
                lines.append(f"  {i}. {q}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
