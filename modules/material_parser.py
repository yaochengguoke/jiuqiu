"""
模块3：素材解析与中央数据池构建
- 解析客户提供的各类素材（文本/Word/PDF等）
- 提取结构化信息
- 构建中央数据池（确保全文数据同源）
- 建立项目知识图谱
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DATA_POOL_DIR
from utils.helpers import (
    extract_numbers, load_json, save_json, ensure_dir,
    read_text_file
)


@dataclass
class DataEntity:
    """数据实体"""
    name: str                    # 实体名称
    value: Any                   # 值
    unit: Optional[str] = None   # 单位
    source: str = ""             # 来源（从哪段素材提取）
    category: str = ""           # 分类标签
    context: str = ""            # 上下文
    confidence: float = 1.0      # 提取置信度


@dataclass
class CentralDataPool:
    """中央数据池 - 所有可量化数据实体的统一存储"""
    # 数值型实体
    numeric_entities: Dict[str, List[DataEntity]] = field(default_factory=dict)

    # 文本型池
    tech_pool: Dict[str, Any] = field(default_factory=dict)
    market_pool: Dict[str, Any] = field(default_factory=dict)
    team_pool: Dict[str, Any] = field(default_factory=dict)
    evidence_pool: Dict[str, Any] = field(default_factory=dict)

    # 关系图谱
    relations: List[Dict[str, str]] = field(default_factory=list)

    # 元数据
    project_name: str = ""
    created_at: str = ""
    version: int = 1


class MaterialParser:
    """
    素材解析模块

    职责：
    1. 从客户原始素材中提取结构化信息
    2. 构建中央数据池（CentralDataPool）
    3. 识别关键实体和关系
    4. 供所有后续模块查询使用
    """

    def __init__(self, data_pool_dir: Path = DATA_POOL_DIR):
        self.data_pool_dir = Path(data_pool_dir)
        ensure_dir(self.data_pool_dir)
        self.pool: Optional[CentralDataPool] = None

    def parse_and_build_pool(
        self,
        customer_kb: Dict[str, Any],
        template_chapters: List[Dict[str, Any]]
    ) -> CentralDataPool:
        """
        从客户知识库构建中央数据池

        Args:
            customer_kb: InputProcessor构建的客户知识库
            template_chapters: 模板的章节配置列表

        Returns:
            CentralDataPool: 构建好的中央数据池
        """
        from datetime import datetime

        self.pool = CentralDataPool(
            project_name=customer_kb.get("project_name", "未知项目"),
            created_at=datetime.now().isoformat(),
            version=1,
        )

        # Step 1: 分类存储到各池
        self.pool.tech_pool = self._extract_tech_pool(customer_kb)
        self.pool.market_pool = self._extract_market_pool(customer_kb)
        self.pool.team_pool = self._extract_team_pool(customer_kb)
        self.pool.evidence_pool = self._extract_evidence_pool(customer_kb)

        # Step 2: 提取所有可量化数据实体
        self.pool.numeric_entities = self._extract_all_numeric_entities(customer_kb)

        # Step 3: 构建实体关系
        self.pool.relations = self._build_relations(self.pool)

        # Step 4: 持久化到磁盘
        self._save_pool()

        return self.pool

    def _extract_tech_pool(self, kb: Dict[str, Any]) -> Dict[str, Any]:
        """提取技术池"""
        return {
            "project_brief": kb.get("project_brief", ""),  # 供完整度检查使用
            "tech_principles": kb.get("tech_principles", ""),
            "innovations": kb.get("innovations", []),
            "tech_params": kb.get("tech_params", {}),
            "papers": kb.get("papers", []),
            "patents": kb.get("patents", []),
            "softwares": kb.get("softwares", []),
            # 解析出的结构化数据
            "technology_name": self._extract_tech_name(kb),
            "key_modules": self._extract_key_modules(kb),
            "performance_metrics": self._extract_performance_metrics(kb),
        }

    def _extract_market_pool(self, kb: Dict[str, Any]) -> Dict[str, Any]:
        """提取市场池"""
        market_data = kb.get("market_data", "")
        industry = kb.get("industry_analysis", "")
        cooperation = kb.get("cooperation_info", "")

        return {
            "market_data_raw": market_data,
            "industry_analysis_raw": industry,
            "cooperation_info_raw": cooperation,
            "market_size": self._extract_market_size(market_data + " " + industry),
            "target_customers": self._extract_customers(market_data),
            "competitors": self._extract_competitors(market_data),
            "partners": self._extract_partners(cooperation),
        }

    def _extract_team_pool(self, kb: Dict[str, Any]) -> Dict[str, Any]:
        """提取团队池 - 交叉引用所有来源统计专利/论文"""
        # 从多个来源综合计算专利数
        patents_from_pm = len(kb.get("patents", []))
        patents_from_evidence = len(kb.get("patent_certificates", []))
        # 从 project_brief 文本中提取（如"已申请发明专利8项"）
        brief = kb.get("project_brief", "")
        patents_from_brief = 0
        patent_match = re.search(r'已?(?:申请|授权|获得).*?专利\s*(\d+)\s*项', brief)
        if patent_match:
            patents_from_brief = int(patent_match.group(1))
        total_patents = max(patents_from_pm, patents_from_evidence, patents_from_brief)

        # 从多个来源综合计算论文数
        papers_from_pm = len(kb.get("papers", []))
        papers_from_brief = 0
        paper_match = re.search(r'(?:发表|收录).*?(?:SCI|EI|核心)?.*?论文\s*(\d+)\s*[篇项]', brief)
        if paper_match:
            papers_from_brief = int(paper_match.group(1))
        total_papers = max(papers_from_pm, papers_from_brief)

        return {
            "project_leader": kb.get("project_leader", ""),
            "team_members": kb.get("team_members", []),
            "team_size": len(kb.get("team_members", [])),
            "advisor_name": kb.get("advisor_name", ""),
            "advisor_title": kb.get("advisor_title", ""),
            "advisor_achievements": kb.get("advisor_achievements", ""),
            "past_awards": kb.get("past_awards", []),
            "total_awards_count": len(kb.get("past_awards", [])),
            "total_patents": total_patents,
            "total_papers": total_papers,
        }

    def _extract_evidence_pool(self, kb: Dict[str, Any]) -> Dict[str, Any]:
        """提取佐证池"""
        return {
            "patent_certificates": kb.get("patent_certificates", []),
            "software_certificates": kb.get("software_certificates", []),
            "product_photos": kb.get("product_photos", []),
            "experiment_photos": kb.get("experiment_photos", []),
            "cooperation_agreements": kb.get("cooperation_agreements", []),
            "other_evidence": kb.get("other_evidence", []),
            # 汇总
            "total_certificates": (
                len(kb.get("patent_certificates", [])) +
                len(kb.get("software_certificates", []))
            ),
            "total_photos": (
                len(kb.get("product_photos", [])) +
                len(kb.get("experiment_photos", []))
            ),
        }

    def _extract_all_numeric_entities(self, kb: Dict[str, Any]) -> Dict[str, List[DataEntity]]:
        """从所有文本字段中提取数值实体"""
        entities = defaultdict(list)

        # 需要扫描的文本字段
        text_fields = [
            ("project_brief", kb.get("project_brief", "")),
            ("tech_principles", kb.get("tech_principles", "")),
            ("market_data", kb.get("market_data", "")),
            ("industry_analysis", kb.get("industry_analysis", "")),
            ("cooperation_info", kb.get("cooperation_info", "")),
            ("advisor_achievements", kb.get("advisor_achievements", "")),
        ]

        for field_name, text in text_fields:
            if not text:
                continue
            numbers = extract_numbers(text)
            for num in numbers:
                key = f"{num.get('value', '')}{num.get('unit', '')}"
                entity = DataEntity(
                    name=key,
                    value=num.get("value", ""),
                    unit=num.get("unit", ""),
                    source=field_name,
                    category=self._classify_number(field_name, num),
                    context=num.get("context", ""),
                )
                entities[key].append(entity)

        return dict(entities)

    def _build_relations(self, pool: CentralDataPool) -> List[Dict[str, str]]:
        """构建实体间关系"""
        relations = []

        # 技术-专利关系
        if pool.tech_pool.get("technology_name"):
            for patent in pool.tech_pool.get("patents", []):
                relations.append({
                    "source": pool.tech_pool["technology_name"],
                    "relation": "has_patent",
                    "target": str(patent),
                })

        # 团队-奖项关系
        for award in pool.team_pool.get("past_awards", []):
            relations.append({
                "source": pool.project_name,
                "relation": "won_award",
                "target": str(award),
            })

        # 产品-客户关系
        for customer in pool.market_pool.get("target_customers", []):
            relations.append({
                "source": pool.project_name,
                "relation": "targets_customer",
                "target": str(customer),
            })

        return relations

    def _extract_tech_name(self, kb: Dict[str, Any]) -> str:
        """从项目简介中提取核心技术名称（优先短小精悍的名称）"""
        brief = kb.get("project_brief", "")
        tech = kb.get("tech_principles", "")
        combined = brief + " " + tech

        # 优先匹配"XX技术"、"XX系统"等经典模式（限制在20字以内）
        classic_patterns = [
            # "AI自适应液冷"、"相变散热系统"这种2-8字+技术/系统类
            r'([一-鿿A-Za-z]{2,8}(?:技术|系统|平台|方案|方法|算法|芯片|器件|材料|散热|冷却|管理))',
            # 排除以年/月/日/获/奖/第/届开头的噪音匹配
        ]
        # 噪音前缀过滤（虚词、结构助词等无意义开头）
        noise_prefixes = set('年月日获奖第届项篇人次个的着了过被把让')
        garbage_words = {'的制备', '的材料', '了技术', '为基础'}
        for pattern in classic_patterns:
            matches = re.findall(pattern, combined)
            if matches:
                valid = [m for m in matches
                        if 3 <= len(m) <= 20
                        and m[0] not in noise_prefixes
                        and not m.startswith(('202', '201', '全国'))
                        and not any(g in m for g in garbage_words)]
                if valid:
                    valid.sort(key=len)
                    return valid[len(valid)//2]

        # 引号中的内容（限25字内）
        quoted = re.findall(r'[「『"\']([^」』"\']+)[」』"\']', combined)
        valid_quoted = [q for q in quoted if 2 <= len(q) <= 25]
        if valid_quoted:
            return min(valid_quoted, key=len)

        # 从项目名提取（取"——"后面的部分中较短的核心词）
        proj_name = kb.get("project_name", "")
        dash_parts = proj_name.split("——")
        if len(dash_parts) >= 2:
            # 尝试提取"XX芯片"、"XX系统"等经典模式
            short = re.findall(r'([一-鿿A-Za-z]{2,10}(?:芯片|系统|材料|技术|器件|电池|平台))', dash_parts[1])
            if short:
                return short[0]
            return dash_parts[1][:15]
        # 尝试从创新点列表取第一个
        innovations = kb.get("innovations", [])
        if innovations and len(innovations[0]) <= 15:
            return innovations[0]

        return "核心技术"

    def _extract_key_modules(self, kb: Dict[str, Any]) -> List[str]:
        """提取关键技术模块"""
        tech_text = kb.get("tech_principles", "")
        # 寻找模块名称模式
        modules = re.findall(r'([一-鿿\w]+模块)', tech_text)
        if not modules:
            modules = re.findall(r'([一-鿿\w]+层)', tech_text)
        return modules[:6]  # 最多6个模块

    def _extract_performance_metrics(self, kb: Dict[str, Any]) -> Dict[str, str]:
        """提取性能指标"""
        tech_params = kb.get("tech_params", {})
        if tech_params:
            return tech_params

        # 从文本中尝试提取
        tech_text = kb.get("tech_principles", "")
        metrics = {}
        patterns = [
            r'(\w+)\s*[达到为]\s*([\d.]+)\s*(\w+)',
            r'(\w+)\s*[提升了降低了减少了]\s*([\d.]+)\s*(\w*\%?)',
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, tech_text):
                key = match.group(1)
                value = match.group(2)
                unit = match.group(3) if match.lastindex >= 3 else ""
                if key not in metrics:
                    metrics[key] = f"{value}{unit}"
        return metrics

    def _extract_market_size(self, text: str) -> str:
        """提取市场规模"""
        patterns = [
            r'市场规模[约达]?\s*(\d+\.?\d*)\s*(亿|万|千)?\s*(元|美元)',
            r'(\d+\.?\d*)\s*(亿|万)?\s*(元|美元)\s*(?:的|规模)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return ""

    def _extract_customers(self, text: str) -> List[str]:
        """提取目标客户"""
        customers = []
        customer_indicators = ["客户包括", "目标客户", "面向", "服务对象", "合作伙伴包括"]

        # 新增: 从"已与XX、YY达成合作"模式提取
        coop_pattern = re.findall(r'已?与([一-鿿\w]+(?:公司|集团|科技|企业|品牌|厂商|汽车|能源|电力))', text)
        customers.extend(coop_pattern)

        # 新增: 从"等领域对...需求"模式提取应用领域作为客户类别
        domain_pattern = re.findall(r'(?:新能源汽车|5G基站|快充电源|数据中心|工业电源|物联网|智能电网|光伏储能|风电)', text)
        customers.extend(domain_pattern)

        for indicator in customer_indicators:
            if indicator in text:
                idx = text.index(indicator)
                snippet = text[idx:idx+200]
                names = re.findall(r'[一-鿿\w]+(?:公司|集团|科技|企业|品牌|厂商)', snippet)
                customers.extend(names)
        return list(set(customers))[:8]

    def _extract_competitors(self, text: str) -> List[str]:
        """提取竞品"""
        competitors = []

        # 新增: 从"被XX、YY等...垄断/主导"模式提取
        monopoly_pattern = re.findall(
            r'被\s*([一-鿿\w]+(?:公司|集团|科技|半导体|电子|光电)?)\s*[、，,]?\s*'
            r'([一-鿿\w]+(?:公司|集团|科技|半导体|电子|光电)?)\s*等[^，。]*?(?:垄断|主导|占据|控制)',
            text
        )
        for match in monopoly_pattern:
            competitors.extend([m for m in match if len(m) > 1])

        comp_indicators = ["竞品", "竞争对手", "对标", "同类产品", "友商"]
        known_competitors = [
            "英飞凌", "Navitas", "西门子", "ABB", "华为", "中兴",
            "海康", "大疆", "百度", "阿里", "腾讯", "TI", "ADI",
            "三星", "台积电", "英特尔", "高通", "博通", "美满",
            "安森美", "意法半导体", "瑞萨", "NXP", "英伟达",
        ]

        for indicator in comp_indicators:
            if indicator in text:
                idx = text.index(indicator)
                snippet = text[idx:idx+200]
                for known in known_competitors:
                    if known in snippet:
                        competitors.append(known)
                names = re.findall(
                    r'[一-鿿]+(?:科技|半导体|电子|光电|材料|新能源|芯片|能源)',
                    snippet
                )
                competitors.extend(names)

        # 新增: 全文扫描已知竞品名
        for known in known_competitors:
            if known in text and known not in competitors:
                competitors.append(known)

        return list(set(competitors))[:8]

    def _extract_partners(self, text: str) -> List[str]:
        """提取合作伙伴"""
        if not text:
            return []
        partners = re.findall(
            r'[一-鿿\w]+(?:大学|学院|研究所|研究院|公司|集团|实验室|中心)',
            text
        )
        return list(set(partners))[:5]

    def _classify_number(self, field_name: str, number: Dict[str, str]) -> str:
        """对提取的数字进行分类"""
        context = number.get("context", "").lower()

        if any(word in context for word in ["市场", "规模", "营收", "产值", "收入"]):
            return "market_size"
        elif any(word in context for word in ["效率", "功率", "性能", "参数", "指标", "精度"]):
            return "performance"
        elif any(word in context for word in ["节能", "减排", "降低", "节省", "碳"]):
            return "efficiency"
        elif any(word in context for word in ["专利", "论文", "软著", "奖项"]):
            return "achievement"
        elif any(word in context for word in ["价格", "成本", "费用"]):
            return "cost"
        elif any(word in context for word in ["人数", "团队", "成员"]):
            return "team"
        else:
            return "other"

    def query_pool(self, entity_type: str) -> List[DataEntity]:
        """查询中央数据池"""
        if self.pool is None:
            return []
        return self.pool.numeric_entities.get(entity_type, [])

    def get_all_numbers(self) -> Dict[str, str]:
        """获取所有唯一数字实体（去重取中位数）"""
        if self.pool is None:
            return {}
        result = {}
        for key, entities in self.pool.numeric_entities.items():
            if entities:
                values = [float(e.value) for e in entities if e.value.replace('.', '').isdigit()]
                if values:
                    result[key] = str(sum(values) / len(values))
        return result

    def _save_pool(self) -> None:
        """持久化数据池"""
        if self.pool is None:
            return

        # 分别保存各池
        save_json(self.data_pool_dir / "central_data.json", {
            "project_name": self.pool.project_name,
            "created_at": self.pool.created_at,
            "numeric_entities": {
                k: [{"name": e.name, "value": e.value, "unit": e.unit,
                     "category": e.category, "source": e.source}
                    for e in v]
                for k, v in self.pool.numeric_entities.items()
            },
            "relations": self.pool.relations,
        })

        save_json(self.data_pool_dir / "tech_pool.json", self.pool.tech_pool)
        save_json(self.data_pool_dir / "market_pool.json", self.pool.market_pool)
        save_json(self.data_pool_dir / "team_pool.json", self.pool.team_pool)
        save_json(self.data_pool_dir / "evidence_pool.json", self.pool.evidence_pool)

    def load_pool(self) -> Optional[CentralDataPool]:
        """从磁盘加载数据池"""
        central_path = self.data_pool_dir / "central_data.json"
        if not central_path.exists():
            return None

        central = load_json(central_path)
        self.pool = CentralDataPool(
            project_name=central.get("project_name", ""),
            created_at=central.get("created_at", ""),
        )

        # 恢复数值实体
        for key, entities in central.get("numeric_entities", {}).items():
            self.pool.numeric_entities[key] = [
                DataEntity(**e) for e in entities
            ]

        self.pool.relations = central.get("relations", [])
        self.pool.tech_pool = load_json(self.data_pool_dir / "tech_pool.json")
        self.pool.market_pool = load_json(self.data_pool_dir / "market_pool.json")
        self.pool.team_pool = load_json(self.data_pool_dir / "team_pool.json")
        self.pool.evidence_pool = load_json(self.data_pool_dir / "evidence_pool.json")

        return self.pool
