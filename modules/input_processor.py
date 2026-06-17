"""
模块1：输入处理与校验
- 定义5类必填资料的数据结构（pydantic Schema）
- 实现输入完整性校验
- 实现资料完整度评分与分级响应
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


# ===== 五类必填资料的Schema定义 =====

class CompetitionInfo(BaseModel):
    """类别1：赛事组别信息"""
    competition_name: str = Field(..., description="赛事名称，如'互联网+高教主赛道'")
    track: Optional[str] = Field(None, description="具体赛道/组别")
    category: Optional[str] = Field(None, description="参赛类别（创意组/初创组/成长组等）")

    @validator("competition_name")
    def validate_competition(cls, v):
        supported = [
            "互联网+高教主赛道", "互联网+青年红色筑梦之旅",
            "挑战杯科技发明A类", "挑战杯科技发明B类",
            "节能减排本科组", "节能减排研究生组",
            "创青春创业计划赛", "三创赛"
        ]
        if v not in supported:
            # 不直接拒绝，但提示可能没有精确匹配的模板
            pass
        return v


class ProjectCoreMaterial(BaseModel):
    """类别2：项目核心资料（写作主体素材）"""
    project_name: str = Field(..., description="项目名称【必填】")
    project_brief: str = Field(..., description="项目简介（200-500字）【必填】")
    project_draft: Optional[str] = Field(None, description="项目初稿（如有）")
    tech_principles: Optional[str] = Field(None, description="技术原理与核心创新描述")
    innovations: Optional[List[str]] = Field(default_factory=list, description="核心创新点列表")
    tech_params: Optional[Dict[str, str]] = Field(default_factory=dict, description="关键技术参数")
    papers: Optional[List[str]] = Field(default_factory=list, description="相关论文列表")
    patents: Optional[List[str]] = Field(default_factory=list, description="相关专利列表")
    softwares: Optional[List[str]] = Field(default_factory=list, description="软著列表")
    market_data: Optional[str] = Field(None, description="市场调研数据描述")
    industry_analysis: Optional[str] = Field(None, description="行业分析资料")
    cooperation_info: Optional[str] = Field(None, description="项目合作、落地应用情况")


class TeamInfo(BaseModel):
    """类别3：团队信息"""
    project_leader: str = Field(..., description="项目负责人姓名")
    team_members: List[Dict[str, str]] = Field(
        default_factory=list,
        description="队员信息：[{name, major, degree, role, achievements}, ...]"
    )
    advisor_name: Optional[str] = Field(None, description="指导老师姓名")
    advisor_title: Optional[str] = Field(None, description="指导老师职称/资历")
    advisor_achievements: Optional[str] = Field(None, description="指导老师学术成就")
    past_awards: Optional[List[str]] = Field(default_factory=list, description="团队过往竞赛获奖")


class DocumentRequirement(BaseModel):
    """类别4：文稿定制要求"""
    target_pages: Optional[int] = Field(80, description="目标策划书页数")
    specific_formats: Optional[str] = Field(None, description="特殊排版要求")
    color_theme: Optional[str] = Field("deep_blue", description="配色方案偏好")
    extra_requirements: Optional[str] = Field(None, description="其他定制要求")


class EvidenceMaterial(BaseModel):
    """类别5：项目佐证素材"""
    patent_certificates: Optional[List[str]] = Field(default_factory=list, description="专利证书路径/描述")
    software_certificates: Optional[List[str]] = Field(default_factory=list, description="软著证书路径/描述")
    product_photos: Optional[List[str]] = Field(default_factory=list, description="产品样机实拍图路径/描述")
    experiment_photos: Optional[List[str]] = Field(default_factory=list, description="实验图路径/描述")
    cooperation_agreements: Optional[List[str]] = Field(default_factory=list, description="校企合作协议路径/描述")
    other_evidence: Optional[List[str]] = Field(default_factory=list, description="其他佐证材料")


# ===== 客户完整提交包 =====

class CustomerSubmission(BaseModel):
    """客户完整提交数据包"""
    competition_info: CompetitionInfo
    project_material: ProjectCoreMaterial
    team_info: TeamInfo
    doc_requirement: DocumentRequirement = Field(default_factory=DocumentRequirement)
    evidence: EvidenceMaterial = Field(default_factory=EvidenceMaterial)


# ===== 完整度评估 =====

class CompletenessLevel(str, Enum):
    FULL = "full"           # ≥80% 直接执行
    PARTIAL = "partial"     # 50-80% 引导补全
    INSUFFICIENT = "insufficient"  # <50% 暂缓执行


@dataclass
class CompletenessReport:
    """资料完整度评估报告"""
    level: CompletenessLevel
    score: float  # 0.0 - 1.0
    category_scores: Dict[str, float]  # 每个类别的分数
    filled_items: List[str]
    missing_items: List[str]
    recommendation: str


class InputProcessor:
    """
    输入处理与校验模块

    职责：
    1. 接收客户提交的原始数据
    2. 验证数据完整性和格式
    3. 给出完整度评分和分级响应建议
    4. 生成结构化的客户专属知识库原始数据
    """

    # 五类资料的权重分配（用于计算完整度）
    CATEGORY_WEIGHTS = {
        "competition_info": 0.10,   # 赛事信息
        "project_material": 0.40,    # 项目资料（最重要）
        "team_info": 0.20,           # 团队信息
        "doc_requirement": 0.10,     # 文稿要求
        "evidence": 0.20,            # 佐证素材
    }

    # 每类资料中的必填字段
    REQUIRED_FIELDS = {
        "competition_info": ["competition_name"],
        "project_material": ["project_name", "project_brief"],
        "team_info": ["project_leader", "team_members"],
        "doc_requirement": [],  # 全部可选
        "evidence": [],         # 全部可选
    }

    def __init__(self):
        self.submission: Optional[CustomerSubmission] = None
        self.completeness_report: Optional[CompletenessReport] = None

    def process_submission(self, raw_data: Dict[str, Any]) -> Tuple[CustomerSubmission, CompletenessReport]:
        """
        处理客户提交的原始数据

        Args:
            raw_data: 客户提交的原始JSON数据

        Returns:
            (CustomerSubmission, CompletenessReport): 结构化提交数据 + 完整度报告
        """
        # Step 1: 数据清洗与标准化
        cleaned_data = self._clean_and_normalize(raw_data)

        # Step 2: Schema校验
        self.submission = CustomerSubmission(**cleaned_data)

        # Step 3: 完整度评估
        self.completeness_report = self._evaluate_completeness(self.submission)

        return self.submission, self.completeness_report

    def process_simple(
        self,
        competition_name: str,
        project_name: str,
        project_brief: str,
        team_leader: str = "",
        team_members: List[Dict] = None,
        tech_principles: str = "",
        innovations: List[str] = None,
        market_data: str = "",
        target_pages: int = 80,
        color_theme: str = "deep_blue",
        **extra_fields
    ) -> Tuple[CustomerSubmission, CompletenessReport]:
        """
        简化接口：通过关键字参数快速提交

        适合快速启动，只需提供最核心的信息
        """
        raw_data = {
            "competition_info": {
                "competition_name": competition_name,
                **{k: v for k, v in extra_fields.items() if k in ["track", "category"]}
            },
            "project_material": {
                "project_name": project_name,
                "project_brief": project_brief,
                "tech_principles": tech_principles,
                "innovations": innovations or [],
                "market_data": market_data,
                **{k: v for k, v in extra_fields.items()
                   if k in ["project_draft", "tech_params", "papers", "patents",
                            "softwares", "industry_analysis", "cooperation_info"]}
            },
            "team_info": {
                "project_leader": team_leader,
                "team_members": team_members or [],
                **{k: v for k, v in extra_fields.items()
                   if k in ["advisor_name", "advisor_title", "advisor_achievements", "past_awards"]}
            },
            "doc_requirement": {
                "target_pages": target_pages,
                "color_theme": color_theme,
                **{k: v for k, v in extra_fields.items()
                   if k in ["specific_formats", "extra_requirements"]}
            },
            "evidence": {
                **{k: v for k, v in extra_fields.items()
                   if k in ["patent_certificates", "software_certificates", "product_photos",
                           "experiment_photos", "cooperation_agreements", "other_evidence"]}
            }
        }
        return self.process_submission(raw_data)

    def _clean_and_normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """数据清洗与标准化"""
        cleaned = {}

        # 确保五类资料的key存在
        for category in ["competition_info", "project_material", "team_info",
                          "doc_requirement", "evidence"]:
            cleaned[category] = raw_data.get(category, {})

        # 标准化项目材料
        if "project_material" in cleaned:
            pm = cleaned["project_material"]
            # 确保列表类型字段
            for list_field in ["innovations", "papers", "patents", "softwares"]:
                if list_field in pm and not isinstance(pm[list_field], list):
                    pm[list_field] = [pm[list_field]] if pm[list_field] else []

        # 标准化团队信息
        if "team_info" in cleaned:
            ti = cleaned["team_info"]
            if "past_awards" in ti and not isinstance(ti["past_awards"], list):
                ti["past_awards"] = [ti["past_awards"]] if ti["past_awards"] else []

        return cleaned

    def _evaluate_completeness(self, submission: CustomerSubmission) -> CompletenessReport:
        """
        评估资料的完整度

        评分规则：
        - 每类资料按必填字段填充率计分
        - 加权汇总得出总分
        """
        category_scores = {}
        filled_items = []
        missing_items = []

        # 逐类评估
        for category, required_fields in self.REQUIRED_FIELDS.items():
            category_data = getattr(submission, category, None)
            if category_data is None:
                category_scores[category] = 0.0
                missing_items.append(f"{category}: 整个类别缺失")
                continue

            category_dict = category_data.dict() if hasattr(category_data, 'dict') else category_data

            # 必填字段
            if required_fields:
                filled = 0
                for field in required_fields:
                    value = category_dict.get(field)
                    if self._is_field_filled(value):
                        filled += 1
                        filled_items.append(f"{category}.{field}")
                    else:
                        missing_items.append(f"{category}.{field}（必填）")
                category_scores[category] = filled / len(required_fields)
            else:
                category_scores[category] = 1.0  # 无必填字段视为满分

            # 额外加分：非必填但有内容的字段
            extra_fields = [k for k in category_dict.keys() if k not in required_fields]
            if extra_fields:
                filled_extra = sum(
                    1 for f in extra_fields if self._is_field_filled(category_dict.get(f))
                )
                if filled_extra > 0:
                    # 每个额外字段可小幅加分，最多不超过该类别满分
                    bonus = min(0.2, filled_extra * 0.05)
                    category_scores[category] = min(1.0, category_scores[category] + bonus)

        # 加权总分
        total_score = sum(
            category_scores.get(cat, 0) * self.CATEGORY_WEIGHTS.get(cat, 0)
            for cat in self.CATEGORY_WEIGHTS
        )

        # 分级判定
        if total_score >= 0.80:
            level = CompletenessLevel.FULL
            recommendation = self._build_recommendation_full(filled_items, missing_items)
        elif total_score >= 0.50:
            level = CompletenessLevel.PARTIAL
            recommendation = self._build_recommendation_partial(filled_items, missing_items)
        else:
            level = CompletenessLevel.INSUFFICIENT
            recommendation = self._build_recommendation_insufficient(missing_items)

        return CompletenessReport(
            level=level,
            score=round(total_score, 2),
            category_scores=category_scores,
            filled_items=filled_items,
            missing_items=missing_items,
            recommendation=recommendation,
        )

    def _is_field_filled(self, value: Any) -> bool:
        """检查字段是否有效填充"""
        if value is None:
            return False
        if isinstance(value, str) and not value.strip():
            return False
        if isinstance(value, (list, dict)) and len(value) == 0:
            return False
        return True

    def _build_recommendation_full(self, filled: List[str], missing: List[str]) -> str:
        lines = ["✅ 资料完整度良好（≥80%），可直接启动生成流程。"]
        if missing:
            lines.append(f"\n⚠️ 以下项目建议补充以提升质量（非必填）：")
            for m in missing:
                lines.append(f"  - {m}")
        return "\n".join(lines)

    def _build_recommendation_partial(self, filled: List[str], missing: List[str]) -> str:
        lines = [
            "⚠️ 资料完整度一般（50%-80%）。",
            "系统将先基于已有信息生成初稿，缺失部分标记为【待补充】。",
            f"\n📋 请尽快补充以下关键信息："
        ]
        for m in missing:
            lines.append(f"  - {m}")
        lines.append("\n💡 补充后可重新生成以获得完整的国奖级策划书。")
        return "\n".join(lines)

    def _build_recommendation_insufficient(self, missing: List[str]) -> str:
        lines = [
            "❌ 资料严重不足（<50%），暂不启动生成流程。",
            f"\n📋 必须补充以下信息后才能启动："
        ]
        for m in missing:
            lines.append(f"  - {m}")
        lines.append("\n请补充后重新提交。")
        return "\n".join(lines)

    def build_customer_knowledge_base(self) -> Dict[str, Any]:
        """
        将客户提交的资料构建为结构化知识库（客户专属库的初始数据）
        """
        if self.submission is None:
            return {}

        sub = self.submission
        pm = sub.project_material
        ti = sub.team_info

        return {
            "project_name": pm.project_name,
            "project_brief": pm.project_brief,
            "project_draft": pm.project_draft or "",
            "competition": sub.competition_info.competition_name,
            "track": sub.competition_info.track or "",

            # 技术池
            "tech_principles": pm.tech_principles or "",
            "innovations": pm.innovations or [],
            "tech_params": pm.tech_params or {},
            "papers": pm.papers or [],
            "patents": pm.patents or [],
            "softwares": pm.softwares or [],

            # 市场池
            "market_data": pm.market_data or "",
            "industry_analysis": pm.industry_analysis or "",
            "cooperation_info": pm.cooperation_info or "",

            # 团队池
            "project_leader": ti.project_leader,
            "team_members": ti.team_members or [],
            "advisor_name": ti.advisor_name or "",
            "advisor_title": ti.advisor_title or "",
            "advisor_achievements": ti.advisor_achievements or "",
            "past_awards": ti.past_awards or [],

            # 佐证池
            "patent_certificates": sub.evidence.patent_certificates or [],
            "software_certificates": sub.evidence.software_certificates or [],
            "product_photos": sub.evidence.product_photos or [],
            "experiment_photos": sub.evidence.experiment_photos or [],
            "cooperation_agreements": sub.evidence.cooperation_agreements or [],
            "other_evidence": sub.evidence.other_evidence or [],

            # 文稿要求
            "target_pages": sub.doc_requirement.target_pages or 80,
            "color_theme": sub.doc_requirement.color_theme or "deep_blue",
            "specific_formats": sub.doc_requirement.specific_formats or "",
            "extra_requirements": sub.doc_requirement.extra_requirements or "",
        }
