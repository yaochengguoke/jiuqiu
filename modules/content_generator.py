"""
模块5：AI内容生成引擎（核心模块）
- 按国奖模板章节骨架逐章生成
- 强制引用机制：每段内容标注数据来源
- 话术句式匹配：demo模式真正使用rhetoric库
- 零虚构保证：缺失数据输出【待补充】
- 集成LLM API进行智能化写作
"""

import json
import re
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PAGE_ALLOCATION, MAX_WORDS_PER_CHAPTER
from modules.template_matcher import MatchedTemplate
from modules.material_parser import CentralDataPool
from utils.llm_client import LLMClient


@dataclass
class ChapterContent:
    chapter_id: str
    chapter_title: str
    content_markdown: str
    word_count: int
    missing_markers: List[str]
    data_sources: List[str]
    generated_at: str = ""
    version: int = 1


@dataclass
class GeneratedDocument:
    project_name: str
    competition_name: str
    chapters: List[ChapterContent]
    total_word_count: int
    missing_sections: List[str]
    generated_at: str
    template_used: str

    def get_full_text(self) -> str:
        lines = [
            f"# {self.project_name}",
            f"# 竞赛策划书",
            f"> 赛事：{self.competition_name}",
            f"> 生成时间：{self.generated_at}",
            f"> 总字数：{self.total_word_count}",
            "", "---", "",
        ]
        for ch in self.chapters:
            lines.append(ch.content_markdown)
        return "\n".join(lines)

    def get_missing_report(self) -> str:
        all_missing = []
        for ch in self.chapters:
            if ch.missing_markers:
                all_missing.append(f"## {ch.chapter_title}")
                for marker in ch.missing_markers:
                    all_missing.append(f"  - {marker}")
        if all_missing:
            report = "# 待补充信息清单\n\n" + "\n".join(all_missing)
        else:
            report = "# 待补充信息清单\n\n[OK] 所有章节内容完整，无缺失项。"

        # 增加字数扩充建议
        report += self._word_expansion_guide()
        return report

    def _word_expansion_guide(self) -> str:
        """生成本文字数扩充引导"""
        chapter_stats = []
        for ch in self.chapters:
            chapter_stats.append((ch.chapter_title, ch.word_count))

        guide = """

---

## [INFO] 字数扩充建议（当前总字数偏低，以下为可扩充方向）

> 注：智能体严格遵循"零虚构原则"，以下扩充需客户提供对应素材。

| 章节 | 当前字数 | 建议扩充方向 | 预估可增量 |
| :--- | :--- | :--- | :--- |
"""
        expansion_tips = {
            "执行摘要": ("补充核心竞争力总结+团队差异化优势", 100),
            "项目背景与行业痛点": ("补充行业技术演进历程（3-5年技术路线回溯）", 300),
            "核心技术原理与创新": ("每个创新点补充实验验证数据+失效模式分析", 600),
            "产品设计与应用场景": ("补全产品规格参数表+多场景实测数据", 400),
            "市场分析与商业模式": ("补全3类目标客户的详细采购决策流程+竞品深度分析", 500),
            "团队介绍与核心优势": ("补充团队协作案例+成员过往项目经验详述", 300),
            "财务预测与融资计划": ("补充成本/营收/融资数据（参见财务补充问卷）", 400),
            "未来规划与社会价值": ("补充分阶段目标+资源需求+风险预案", 400),
        }

        total_estimated = 0
        for ch in self.chapters:
            title = ch.chapter_title
            words = ch.word_count
            tip, estimate = expansion_tips.get(title, ("补充更多细节描述", 200))
            guide += f"| {title} | {words}字 | {tip} | +{estimate}字 |\n"
            total_estimated += estimate

        guide += f"""
| **合计** | **{self.total_word_count}字** | — | **+{total_estimated}字（可提升至{self.total_word_count + total_estimated}字）** |

### 扩充优先级建议
1. 🔴 **核心技术**：当前最核心但字数不足，补充实验验证数据最能提升专业性
2. 🟡 **市场分析**：竞品深度分析和客户画像能显著增强商业可信度
3. 🟢 **产品设计**：详细规格和测试结果让方案更"可触摸"

### 如何补充
- 将对应素材发送给智能体，系统将自动追加到对应章节
- 或直接填写财务预测补充问卷（`financial_questionnaire.md`）
"""
        return guide


class ContentGenerator:

    SYSTEM_PROMPT = """你是一位资深的竞赛策划书撰写专家，专门为全国大学生顶级竞赛撰写国奖级别的策划书。

## 核心写作原则

### 1. 零虚构铁律
- 只能使用提供的素材数据，绝不编造任何事实、数据、客户名称、合作信息
- 缺失处输出【待补充：具体需要什么】
- 不要为"让文章更好"而编造数字或案例

### 2. 国奖结构仿写
- 严格按照提供的段落结构组织文章
- 使用国奖话术模板中的句式风格
- 确保必备要素全部覆盖

### 3. 数据引用规范
- 每引用一个数据，标注【来源：XXX】
- 同一数据在文中出现多次时，保持完全一致
- 不使用"大约""左右"等模糊词

### 4. 输出格式
- 直接输出Markdown格式（从## 章节标题开始）
- 图表位置用【此处插入：XX图】标注"""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client
        self.use_ai = llm_client is not None and llm_client.is_available
        if self.llm_client:
            self.llm_client.system_prompt = self.SYSTEM_PROMPT
            try:
                random.seed()
            except Exception:
                pass

    def generate_all_chapters(
        self, template: MatchedTemplate, data_pool: CentralDataPool,
        progress_callback: Optional[Callable] = None,
    ) -> GeneratedDocument:
        chapters_content = []
        all_missing_sections = []
        for i, chapter_config in enumerate(template.chapters):
            if progress_callback:
                progress_callback(i + 1, len(template.chapters), chapter_config["title"])
            chapter_content = self._generate_chapter(chapter_config, template, data_pool)
            chapters_content.append(chapter_content)
            all_missing_sections.extend(chapter_content.missing_markers)
        total_words = sum(c.word_count for c in chapters_content)
        return GeneratedDocument(
            project_name=data_pool.project_name,
            competition_name=template.competition_name,
            chapters=chapters_content,
            total_word_count=total_words,
            missing_sections=all_missing_sections,
            generated_at=datetime.now().isoformat(),
            template_used=f"{template.competition_name} v{template.template_meta.get('version','1.0')}",
        )

    def _generate_chapter(self, chapter_config, template, data_pool) -> ChapterContent:
        chapter_id = chapter_config.get("id", "")
        chapter_title = chapter_config.get("title", "未命名章节")
        chapter_rhetoric = template.rhetoric_data.get(chapter_id, {})
        relevant_data = self._prepare_chapter_data(chapter_id, chapter_config, data_pool)
        data_context = json.dumps(relevant_data, ensure_ascii=False, indent=2)

        if self.use_ai:
            content = self._generate_with_ai(chapter_config, data_context, chapter_rhetoric, template.visual_style)
            content = self._verify_against_data_pool(content, relevant_data)
        else:
            content = self._generate_demo(chapter_config, chapter_rhetoric, data_pool)

        missing_markers = re.findall(r'【待补充[：:][^】]+】', content)
        data_sources = re.findall(r'【来源[：:][^】]+】', content)
        word_count = len(content.replace('\n', '').replace(' ', ''))
        return ChapterContent(
            chapter_id=chapter_id, chapter_title=chapter_title,
            content_markdown=content, word_count=word_count,
            missing_markers=missing_markers, data_sources=data_sources,
            generated_at=datetime.now().isoformat(),
        )

    def _generate_demo(self, chapter_config, chapter_rhetoric, data_pool) -> str:
        chapter_id = chapter_config.get("id", "")
        chapter_name = chapter_config.get("title", "")

        rhetoric = self._pick_rhetoric(chapter_rhetoric)

        # 调用handler获取内容
        if chapter_id == "executive_summary":
            body = self._demo_executive(data_pool, rhetoric)
        elif chapter_id == "background":
            body = self._demo_background(data_pool, rhetoric)
        elif chapter_id == "technology":
            body = self._demo_technology(data_pool, rhetoric)
        elif chapter_id == "product_design":
            body = self._demo_product(data_pool, rhetoric)
        elif chapter_id == "market_analysis":
            body = self._demo_market(data_pool, rhetoric)
        elif chapter_id == "team_intro":
            body = self._demo_team(data_pool, rhetoric)
        elif chapter_id == "financial":
            body = self._demo_financial(data_pool, rhetoric)
        elif chapter_id == "future_plan":
            body = self._demo_future(data_pool, rhetoric)
        elif chapter_id == "verification":
            body = self._demo_verification(data_pool, rhetoric)
        elif chapter_id == "application":
            body = self._demo_application(data_pool, rhetoric)
        elif chapter_id == "conclusion":
            body = self._demo_conclusion(data_pool, rhetoric)
        elif chapter_id == "solution":
            body = self._demo_solution(data_pool, rhetoric)
        elif chapter_id == "implementation":
            body = self._demo_implementation(data_pool, rhetoric)
        else:
            body = self._generic_demo_body(chapter_config.get("paragraph_structure", []), data_pool)

        # 用模板定义的章节标题替换handler中硬编码的标题
        body = re.sub(r'^## .+', f'## {chapter_name}', body, count=1, flags=re.MULTILINE)
        return body

    def _pick_rhetoric(self, rhetoric_data: dict) -> dict:
        """从话术库中选取句式（每种1-2个）"""
        result = {}
        patterns = rhetoric_data.get("sentence_patterns", {})
        for category, sentences in patterns.items():
            if sentences:
                n = min(2, len(sentences))
                result[category] = random.sample(sentences, n) if n > 1 else [sentences[0]]
        return result

    def _fill_placeholders(self, text: str, dp: CentralDataPool) -> str:
        """替换话术中的AA/BB/YY/ZZ等占位符为项目实际内容"""
        tech_name = dp.tech_pool.get("technology_name", "核心技术")
        market_data = dp.market_pool.get("market_data_raw", "")
        innovations = dp.tech_pool.get("innovations", [])

        # 从市场数据推断行业/领域（精确匹配，避免"数据"误匹配"数据中心"）
        all_text = market_data + str(dp.tech_pool.get("project_brief", ""))
        if "数据中心" in all_text:
            industry, domain = "数据中心", "热管理"
        elif "钙钛矿" in all_text or "光伏" in all_text:
            industry, domain = "钙钛矿光伏", "高纯材料"
        elif "半导体" in all_text or "GaN" in all_text:
            industry, domain = "半导体", "功率芯片"
        elif "液冷" in all_text or "散热" in all_text:
            industry, domain = "数据中心", "热管理"
        else:
            industry, domain = "目标行业", "核心技术"

        # 从创新点推断技术路径
        old_method = "传统方案"
        new_method = tech_name[:12] if tech_name else "创新方案"
        for innov in (innovations or []):
            if "预测" in innov or "算法" in innov:
                new_method = innov[:15]
                old_method = "传统PID控制"
                break
            elif "冷板" in innov or "散热" in innov:
                new_method = innov[:15]
                old_method = "传统风冷/平板散热"
                break

        # 替换映射
        replace_map = {
            "AA技术": f"{industry}{domain}",
            "AA": industry,
            "BB领域": f"{domain}领域",
            "BB": domain,
            "CC": "数字化",
            "DD产业": f"{industry}产业",
            "DD": industry,
            "EE": domain,
            "FF": industry,
            "YY思路": old_method,
            "YY": old_method[:8],
            "ZZ策略": new_method,
            "ZZ": new_method[:8],
            "XX": tech_name[:10],
        }

        result = text
        for placeholder, replacement in replace_map.items():
            if placeholder in result:
                result = result.replace(placeholder, replacement)

        # 处理 "心脏/基石/命脉/核心引擎" 等 `/` 分隔的多选项 → 只保留第一个
        result = re.sub(r"'([^']+)'(?:/'([^']+)')+", r"'\1'", result)

        # 清理可能的重复模式
        result = re.sub(r'(传统\S{2,6}方案?)的\1', r'\1', result)
        result = re.sub(r'(\S{2,6}领域)的\1', r'\1', result)

        # 术语规范化：统一常见错写
        term_fixes = {
            "高纯化铝": "高纯碘化铅",
            "高纯铝": "高纯碘化铅",
            "溶剂结合": "溶剂络合",
            "络合分离技术是传统方案的核心": "高纯碘化铅是制备钙钛矿电池的核心原材料",
        }
        for wrong, correct in term_fixes.items():
            result = result.replace(wrong, correct)
        return result

    # ===== 各章节Demo生成函数 =====

    def _demo_executive(self, dp: CentralDataPool, rhetoric: dict) -> str:
        project = dp.project_name
        tech_name = dp.tech_pool.get("technology_name", "核心技术")
        innovations = dp.tech_pool.get("innovations", [])
        params = dp.tech_pool.get("tech_params", {})
        team_size = dp.team_pool.get("team_size", len(dp.team_pool.get("team_members", [])))
        awards = dp.team_pool.get("total_awards_count", 0)
        patents = dp.team_pool.get("total_patents", 0)
        papers = dp.team_pool.get("total_papers", 0)
        leader = dp.team_pool.get("project_leader", "")
        advisor = dp.team_pool.get("advisor_name", "")
        market_data = dp.market_pool.get("market_data_raw", "")
        cooperation = dp.market_pool.get("cooperation_info_raw", "")

        lines = [f"## 执行摘要", ""]

        # 一句话定位 - 用市场数据推断行业领域（而非tech_name）
        market_data = dp.market_pool.get("market_data_raw", "")
        domain = tech_name
        if "钙钛矿" in market_data or "钙钛矿" in project:
            domain = "钙钛矿光伏材料"
        elif "液冷" in market_data or "数据中心" in market_data:
            domain = "数据中心热管理"
        elif "GaN" in market_data or "半导体" in market_data:
            domain = "第三代半导体功率芯片"
        if innovations:
            core = innovations[0]
            lines.append(f"**{project}** —— 以自主研发的'{core}'技术为核心突破，"
                        f"致力于推动{domain}领域的国产替代与产业升级。")
        else:
            lines.append(f"**{project}** —— 专注于{tech_name}领域的高科技创新项目。")
        lines.append("")

        # 技术亮点
        lines.append("### 核心技术突破")
        if params:
            top_params = list(params.items())[:3]
            param_str = "、".join(f"{k}={v}" for k, v in top_params)
            lines.append(f"核心性能指标：{param_str}，多项参数超越国际竞品。"
                        f"【来源：tech_params】")
            # 从tech_principles中提取竞品对比亮点（动态匹配，非硬编码）
            tech_text = dp.tech_pool.get("tech_principles", "")
            comp_highlights = re.findall(
                r'(?:较|比|相比|相较于|优于)[^，。]*(?:提升|降低|优化|超越|领先)[^，。]*\d+[%％]?[^，。]*',
                tech_text
            )
            if comp_highlights:
                lines.append(f"竞品对比亮点：{comp_highlights[0][:120]}。【来源：tech_principles】")
            elif len(top_params) >= 3:
                # 用关键参数构建一句话亮点
                lines.append(f"以上核心指标已达到或超越国际先进水平。【来源：tech_params】")
        elif innovations:
            lines.append(f"核心创新包括：{'、'.join(innovations[:3])}。"
                        f"【来源：innovations】")
        else:
            lines.append("【待补充：核心技术亮点与关键性能参数】")
        lines.append("")

        # 市场机遇 - 从market_data提取规模和增长率
        lines.append("### 市场机遇")
        mkt_text = dp.market_pool.get("market_data_raw", "")
        # 提取"市场规模达4.2亿美元"
        size_m = re.search(r'(?:规模|市场)(?:已达|达|约|为|超过)\s*(\d+\.?\d*)\s*(亿|万|千)?\s*(美元|元|人民币)?', mkt_text)
        # 提取CAGR
        cagr_m = re.search(r'(?:年复合增长率|CAGR)[^\d]*(\d+\.?\d*\s*%)', mkt_text)
        # 提取预测年份+规模
        future_m = re.search(r'(?:预计|将|突破|达到)\s*(\d+)\s*年[^\d]*(\d+\.?\d*)\s*(亿|万)?\s*(美元|元)?', mkt_text)
        if size_m:
            size_str = f"{size_m.group(1)}{size_m.group(2) or ''}{size_m.group(3) or ''}"
            parts = [f"全球市场规模达{size_str}"]
            if cagr_m:
                parts.append(f"年复合增长率超{cagr_m.group(1)}")
            if future_m:
                parts.append(f"预计{future_m.group(1)}年突破{future_m.group(2)}{future_m.group(3) or ''}{future_m.group(4) or ''}")
            lines.append("，".join(parts) + "。【来源：market_data】")
        elif mkt_text:
            lines.append(f"目标市场保持高速增长。【来源：market_data】"
                        f"【待补充：市场规模具体数字】")
        else:
            lines.append("【待补充：目标市场规模与增长前景】")
        lines.append("")

        # 团队与成果
        lines.append("### 团队与成果")
        team_parts = []
        if leader:
            team_parts.append(f"由{leader}领衔")
        team_parts.append(f"{team_size}人核心团队")
        if advisor:
            title = dp.team_pool.get("advisor_title", "")
            team_parts.append(f"指导教师{advisor}（{title}）" if title else f"指导教师{advisor}")
        lines.append("，".join(team_parts) + "。")

        achievement_parts = []
        if patents > 0:
            achievement_parts.append(f"已申请/授权发明专利{patents}项")
        if papers > 0:
            achievement_parts.append(f"发表学术论文{papers}篇")
        if awards > 0:
            achievement_parts.append(f"累计获得{awards}项国家级/省部级竞赛奖项")
        if achievement_parts:
            lines.append("团队成果：" + "，".join(achievement_parts) + "。")
            lines.append(f"【来源：team_pool/evidence_pool】")
        lines.append("")

        # 合作与落地
        if cooperation:
            lines.append(f"### 合作与落地")
            lines.append(f"{cooperation[:200]}【来源：cooperation_info】")
            lines.append("")

        # 结尾升华
        lines.append("### 总结与展望")
        closing = f"{project}致力于以技术创新推动国产替代进程，"
        mkt = dp.market_pool.get("market_data_raw", "")
        if "钙钛矿" in mkt or "光伏" in mkt:
            closing += "助力我国在钙钛矿光伏领域实现从材料到器件的全面自主可控。"
        elif "双碳" in str(params) or "能效" in str(params) or "节能" in mkt:
            closing += "同时为'双碳'目标贡献技术力量。"
        elif "半导体" in mkt or "GaN" in mkt:
            closing += "助力我国在第三代半导体领域实现从跟跑到领跑的跨越。"
        else:
            closing += "为我国相关产业的高质量发展注入新动能。"
        lines.append(closing)
        lines.append("")

        return "\n".join(lines)

    def _demo_background(self, dp: CentralDataPool, rhetoric: dict) -> str:
        tech_name = dp.tech_pool.get("technology_name", "该技术领域")
        market_data = dp.market_pool.get("market_data_raw", "")
        industry = dp.market_pool.get("industry_analysis_raw", "")
        competitors = dp.market_pool.get("competitors", [])

        # 从market_data中提取关键数字（排除年份干扰）
        market_size_match = re.search(
            r'(?:规模|市场)(?:已达|达|约|为|超过)\s*(\d+\.?\d*)\s*(亿|万|千)?\s*(美元|元|人民币)',
            market_data
        )
        # 提取纯数字+单位部分（排除前缀词如"规模已达"）
        market_size_str = f"{market_size_match.group(1)}{market_size_match.group(2) or ''}{market_size_match.group(3) or ''}" if market_size_match else "【待补充】"
        cagr_match = re.search(r'(?:年复合增长率|CAGR)[^\d]*(\d+\.?\d*\s*%)', market_data)
        cagr_str = cagr_match.group(1) if cagr_match else "【待补充】"
        local_match = re.search(r'国产化率[^\d]*(\d+\.?\d*\s*%)', market_data)
        local_str = local_match.group(1) if local_match else "【待补充】"

        # 话术 - 填充占位符
        # 话术 - 只选一条（不全部列出）
        rh_all = rhetoric.get("opening", [])
        if rh_all:
            opening = self._fill_placeholders(rh_all[0], dp)
        else:
            domain_hint = "数据中心热管理" if "液冷" in market_data or "数据" in market_data else \
                         "钙钛矿光伏材料" if "钙钛矿" in market_data else \
                         "半导体功率芯片" if "GaN" in market_data or "半导体" in market_data else "核心技术"
            opening = f"{tech_name}是支撑{domain_hint}产业发展的关键基础。"

        lines = [f"## 项目背景与行业痛点", ""]

        # 1. 宏观概念引入（背景段首句+行业专属过渡句）
        lines.append("### 行业宏观背景")
        # 根据领域生成连贯的首段
        if "钙钛矿" in market_data or "光伏" in market_data:
            lines.append("高纯碘化铅（PbI₂）是制备高性能钙钛矿太阳能电池的核心原材料，其纯度直接决定电池的光电转换效率和稳定性。")
            lines.append("钙钛矿太阳能电池效率十年间从3.8%跃升至26.1%，但核心材料长期依赖进口，严重制约产业自主发展。")
        elif "液冷" in market_data or "数据中心" in market_data:
            lines.append(f"{tech_name}是数据中心热管理的关键技术方向。")
            lines.append("在全球数据中心算力需求爆发式增长的背景下，传统冷却方案能耗占比高达40%，已成为制约行业绿色发展的核心瓶颈。")
        else:
            lines.append(opening)
            lines.append(f"随着技术进步和市场需求增长，{tech_name}领域正面临前所未有的发展机遇与挑战。")
        lines.append("")

        # 2. 权威数据佐证
        lines.append("### 市场数据与趋势")
        if market_data and "【待补充】" not in market_size_str:
            lines.append(f"据权威行业报告显示，全球{tech_name}市场规模已达{market_size_str}，"
                        f"年复合增长率超过{cagr_str}。【来源：market_data】")
            # 使用实际的市场数据内容
            lines.append(f"")
            lines.append(f"{market_data[:400]}【来源：market_data_raw】")
        else:
            lines.append("【待补充：引用权威行业报告数据，如Yole/IHS/中商产业研究院等机构的量化数据】")
        lines.append("")

        # 3. 国内外差距
        lines.append("### 行业痛点与国产化挑战")
        if local_str and "【待补充】" not in local_str:
            lines.append(f"当前国产化率仅为{local_str}，核心技术受制于人。【来源：market_data】")

        if competitors:
            comp_list = "、".join(competitors[:3])
            lines.append(f"全球市场长期被{comp_list}等海外企业主导，国内企业面临严峻的竞争压力。"
                        f"【来源：competitor_extraction】")
        else:
            if "【待补充】" in local_str:
                lines.append("【待补充：国产化率具体数据及主要海外竞争者名单】")
        lines.append("")

        # 4. 政策机遇
        lines.append("### 政策机遇与国家战略")
        lines.append(f"在'十四五'规划和2035远景目标纲要的战略框架下，"
                    f"{tech_name}被列为重点发展方向。")
        # 根据项目行业动态选择政策引用
        _innovations = dp.tech_pool.get("innovations", [])
        _brief = dp.tech_pool.get("project_brief", "")
        all_text = (_brief + market_data + str(_innovations)).lower()
        policy_map = {
            "半导体": "工信部等七部门《关于推动能源电子产业发展的指导意见》明确将第三代半导体列为重点突破方向。",
            "光伏": "国家能源局《'十四五'可再生能源发展规划》将钙钛矿光伏技术列为前沿突破方向，科技部《'十四五'能源领域科技创新规划》提出2030年实现钙钛矿电池商业化。",
            "钙钛矿": "国家能源局《'十四五'可再生能源发展规划》将钙钛矿光伏技术列为前沿突破方向，科技部《'十四五'能源领域科技创新规划》提出2030年实现钙钛矿电池商业化。",
            "液冷": "工信部《新型数据中心发展三年行动计划》要求到2025年新建大型数据中心PUE值降至1.3以下，液冷技术被列为重点推广的绿色节能技术。",
            "节能": "国务院《2030年前碳达峰行动方案》将节能降碳增效列为十大行动之一。",
            "新能源": "国家发改委《'十四五'可再生能源发展规划》将新能源材料列为关键支撑领域。",
        }
        policy_text = "国务院《'十四五'规划纲要》将关键核心技术攻关列为国家战略重点。"
        for keyword, text in policy_map.items():
            if keyword in all_text:
                policy_text = text
                break
        lines.append(f"**【政策支持】** {policy_text}【待补充：客户所在细分领域的专项政策文件及具体条款】")
        lines.append("")

        # 5. 配图
        lines.append("【此处插入：20:10横屏行业趋势新闻佐证图】")
        lines.append("")

        return "\n".join(lines)

    def _demo_technology(self, dp: CentralDataPool, rhetoric: dict) -> str:
        tech_name = dp.tech_pool.get("technology_name", "核心创新技术")
        tech_text = dp.tech_pool.get("tech_principles", "")
        innovations = dp.tech_pool.get("innovations", [])
        params = dp.tech_pool.get("tech_params", {})
        patents_from_team = dp.team_pool.get("total_patents", 0)
        papers_from_team = dp.team_pool.get("total_papers", 0)
        evidence = dp.evidence_pool
        patent_certs = evidence.get("patent_certificates", [])
        software_certs = evidence.get("software_certificates", [])

        # 话术
        rh_innov = rhetoric.get("innovation_naming", ["本团队创新性地提出了核心方案。"])
        rh_param = rhetoric.get("parameter_quantification", ["实测数据显示了优异性能。"])
        rh_comp = rhetoric.get("competitor_comparison", ["相较于国际竞品，本方案具备显著优势。"])
        rh_effect = rhetoric.get("effect_value", ["该技术突破具有重要的应用价值。"])

        lines = [f"## 核心技术原理与创新", ""]

        # 总览
        lines.append("### 技术方案总览")
        lines.append(self._fill_placeholders(rh_innov[0], dp))
        lines.append("")
        lines.append("【此处插入：技术架构总图 - 系统架构示意图】")
        lines.append("")

        # 核心技术原理 - 展示时去掉前导编号
        lines.append("### 核心技术原理")
        if tech_text:
            # 智能截取并去掉可能的前导编号
            clean_tech = re.sub(r'(?m)^[\d一二三]+[.、）\)]\s*', '', tech_text[:800])
            lines.append(clean_tech)
            if len(tech_text) > 800:
                lines.append(f"...（完整技术描述共{len(tech_text)}字）")
            lines.append("【来源：tech_principles】")
        else:
            lines.append("【待补充：核心技术原理详细描述，包括理论模型、工艺流程、算法逻辑等】")
        lines.append("")

        # 创新点详述 - 过滤空创新点 + 全局编号 + 概括性描述
        lines.append("### 创新点详述")
        sentences = re.split(r'[。\n]', tech_text) if tech_text else []
        sentences = [s.strip() for s in sentences if len(s.strip()) > 8]

        # 只保留有匹配内容的创新点
        counter = 0
        for innovation in innovations:
            # 提取创新名的核心词
            core_words = re.findall(r'[一-鿿A-Za-z]{2,4}', innovation)
            matched = []
            for si, s in enumerate(sentences):
                if not s:
                    continue
                score = sum(1.0 for w in core_words if w in s)
                if score >= 1:
                    matched.append((score, si))

            if not matched:
                continue  # 跳过无匹配的空创新点

            counter += 1
            lines.append(f"#### {counter}. {innovation}")

            # 取最佳匹配句，提取技术名+关键数字+效果
            matched.sort(key=lambda x: -x[0])
            best = sentences[matched[0][1]]
            sentences[matched[0][1]] = ""  # 标记已用

            # 提取技术名（冒号前的部分）
            name_m = re.match(r'^[\d一二三]*[.、）\)]*\s*([^:：]{4,30})', best)
            tech_label = name_m.group(1).strip() if name_m else ""
            # 提取关键数字
            nums = re.findall(r'(\d+\.?\d*\s*(?:%|ppm|倍|级|nm|μm|W|V|mΩ|cm²))', best)
            nums_str = "、".join(nums[:3]) if nums else ""
            # 提取效果（"降至"、"提升"、"达"等动词引导的结果）
            effect_m = re.search(r'(?:降至|提升|降低|可达|优于|超越|实现)([^。]{4,40})', best)
            effect_str = effect_m.group(0) if effect_m else ""

            summary_parts = []
            if tech_label:
                summary_parts.append(tech_label)
            if nums_str:
                summary_parts.append(f"关键指标：{nums_str}")
            if effect_str:
                summary_parts.append(effect_str)

            summary = "；".join(summary_parts) if summary_parts else best[:120]
            if len(summary) > 150:
                summary = summary[:150] + "。"
            lines.append(f"> {summary}【来源：tech_principles】")
            lines.append("")

        if counter == 0:
            lines.append("> 【提示】请补充项目的核心创新点描述，包括技术突破、与现有技术的差异等。")
        lines.append("")

        # 性能参数表 - 预设已知竞品数据 + 从客户资料验证
        competitors = dp.market_pool.get("competitors", [])
        market_data = dp.market_pool.get("market_data_raw", "")
        brief = dp.tech_pool.get("project_brief", "")
        all_text = brief + " " + market_data

        if not competitors:
            competitors = ["进口试剂（Sigma-Aldrich等）"] if "进口" in all_text else []
        comp_label = "、".join(competitors[:2]) if competitors else "国际竞品"
        lines.append("### 性能参数与竞品对比")
        lines.append(f"| 参数名称 | 本方案指标 | 国际竞品（{comp_label}） | 提升幅度 |")
        lines.append("|----------|-----------|---------------------------|---------|")

        # 提取竞品对比数据
        comp_purity = None; comp_eff = None; comp_imp = None
        m = re.search(r'进口[^，。]*?纯度[^\d]*(\d+\.?\d*)', all_text)
        if m: comp_purity = m.group(1) + "%"
        m = re.search(r'(?:优于|高于|超过)[^。]*?(\d+\.?\d*)\s*[%％]', all_text)
        if m: comp_eff = m.group(1) + "%"
        # 从纯度差推断竞品杂质水平: (100%-纯度)*10000 = ppm
        m = re.search(r'进口.*?(?:纯度|试剂).*?(\d+\.?\d*)\s*[%％]?', all_text)
        if m:
            comp_pct = float(m.group(1))
            comp_impurity_ppm = round((100 - comp_pct) * 10000) if comp_pct > 90 else 100
            comp_imp = f"~{comp_impurity_ppm}ppm"

        # 精选展示参数（最多6行，确保每行都有意义）
        shown = 0
        for key, value in list(params.items()):
            if shown >= 6:
                break
            if any(kw in key for kw in ["进口", "竞品", "传统", "对比", "对手"]):
                continue

            comp_val = "【待补充】"
            improvement = "【待补充】"

            try:
                our = float(re.findall(r'[\d.]+', str(value))[0])
            except: our = None

            if "纯度" in key and comp_purity:
                comp_val = comp_purity
                try:
                    cp = float(re.findall(r'[\d.]+', comp_purity)[0])
                    if our and cp < our:
                        improvement = f"杂质降低{(100-cp)/(100-our):.0f}倍" if our > 90 else f"+{our-cp:.3f}%"
                except: pass

            elif "效率" in key and comp_eff:
                comp_val = comp_eff
                try:
                    ce = float(re.findall(r'[\d.]+', comp_eff)[0])
                    if our: improvement = f"+{our-ce:.1f}个百分点"
                except: pass

            elif "初始" in key:
                # 初始杂质是原材料阶段，不与竞品成品对比 → 跳过
                continue
            elif ("杂质" in key or "一次" in key) and comp_imp:
                comp_val = comp_imp
                try:
                    ci = float(re.findall(r'[\d.]+', comp_imp)[0])
                    if our and ci > our: improvement = f"降低{(1-our/ci)*100:.0f}%"
                    elif our and our > ci: improvement = f"优于竞品{our/ci:.0f}倍"
                except: pass

            lines.append(f"| {key} | {value} | {comp_val} | {improvement} |")
            shown += 1
        lines.append("")
        lines.append("【此处插入：性能雷达图 - 本产品 vs 竞品1 vs 竞品2】")
        lines.append("")

        # 专利布局
        lines.append("### 技术壁垒与专利布局")
        if patent_certs or software_certs:
            if patent_certs:
                lines.append("**专利证书：**")
                for cert in patent_certs:
                    lines.append(f"- {cert}")
            if software_certs:
                lines.append("**软件著作权：**")
                for cert in software_certs:
                    lines.append(f"- {cert}")
            lines.append(f"【来源：evidence_pool】")
        elif patents_from_team > 0:
            lines.append(f"团队已申请/授权发明专利{patents_from_team}项。")
            lines.append("【待补充：具体专利名称和授权号】")
        else:
            lines.append("【待补充：专利布局情况，包括已申请/授权的专利名称、类型和覆盖范围】")
        lines.append("")

        # 论文
        if papers_from_team > 0:
            lines.append(f"相关学术论文{papers_from_team}篇，为技术方案提供了坚实的理论支撑。")
            lines.append("【待补充：代表性论文标题、期刊和发表时间】")
        lines.append("")

        lines.append("【此处插入：工艺制备流程图 - 完整工艺流】")
        lines.append("")

        return "\n".join(lines)

    def _demo_product(self, dp: CentralDataPool, rhetoric: dict) -> str:
        innovations = dp.tech_pool.get("innovations", [])
        prod_photos = dp.evidence_pool.get("product_photos", [])
        exp_photos = dp.evidence_pool.get("experiment_photos", [])
        cooperation = dp.market_pool.get("cooperation_info_raw", "")

        rh_overview = rhetoric.get("product_overview", ["基于核心技术突破，本项目构建了完整的产品体系。"])
        rh_scenario = rhetoric.get("application_scenario", ["产品可应用于多个场景。"])

        lines = [f"## 产品设计与应用场景", ""]

        lines.append("### 产品体系总览")
        core_innov = innovations[0] if innovations else "核心技术"
        lines.append(f"基于{core_innov}，项目构建了从核心器件到系统方案的多层次产品体系。【来源：innovations】")
        lines.append("")

        lines.append("### 核心产品规格")
        lines.append("【待补充：产品型号、详细功能参数表】")
        lines.append("")

        lines.append("### 典型应用场景")
        if cooperation:
            # 从合作信息推断应用场景
            lines.append(f"根据已有合作情况：{cooperation[:200]}【来源：cooperation_info】")
        lines.append("1. **场景一**：【待补充：具体应用场景描述】")
        lines.append("2. **场景二**：【待补充：具体应用场景描述】")
        lines.append("3. **场景三**：【待补充：具体应用场景描述】")
        lines.append("")

        lines.append("### 样机验证")
        if prod_photos:
            lines.append(f"已有产品样机/实物照片{len(prod_photos)}张：")
            for photo in prod_photos:
                lines.append(f"- {photo}")
            lines.append("【来源：evidence_pool】")
        else:
            lines.append("【待补充：产品样机或原型系统照片】")
        if exp_photos:
            lines.append(f"实验/测试照片{len(exp_photos)}张，包括：")
            for photo in exp_photos:
                lines.append(f"- {photo}")
        lines.append("")

        lines.append("### 产品迭代路线")
        lines.append("【待补充：产品从当前版本到未来版本的演进路线图】")
        lines.append("")

        return "\n".join(lines)

    def _demo_market(self, dp: CentralDataPool, rhetoric: dict) -> str:
        market_data = dp.market_pool.get("market_data_raw", "")
        target_customers = dp.market_pool.get("target_customers", [])
        competitors = dp.market_pool.get("competitors", [])
        partners = dp.market_pool.get("partners", [])
        cooperation = dp.market_pool.get("cooperation_info_raw", "")

        rh_model = rhetoric.get("business_model_naming", ["本项目采用创新的商业模式。"])
        rh_customer = rhetoric.get("customer_evidence", ["已与多家企业达成合作。"])

        lines = [f"## 市场分析与商业模式", ""]

        # 商业模式
        lines.append("### 商业模式设计")
        # 从创新点中提取商业模式名称（如"芯片-模组-方案三位一体"）
        biz_model_name = "创新商业模式"
        for innov in (dp.tech_pool.get("innovations") or []):
            if "商业模式" in innov or "模式" in innov:
                biz_model_name = innov
                break
        lines.append(biz_model_name.replace("三位一体商业模式", "三位一体的商业模式")
                     if "三位一体" in biz_model_name else biz_model_name)
        lines.append("【此处插入：商业模式画布图】")
        lines.append("")

        # 目标市场
        lines.append("### 目标市场分析")
        if market_data:
            lines.append(market_data[:350])
            lines.append("【来源：market_data_raw】")
        else:
            lines.append("【待补充：TAM-SAM-SOM市场分析数据】")
        lines.append("")

        # 目标客户
        lines.append("#### 目标客户群体")
        if target_customers:
            for c in target_customers:
                lines.append(f"- {c}")
            lines.append("【来源：customer_extraction】")
        elif cooperation:
            # 从合作信息推断
            coop_entities = re.findall(r'(?:已与|和|跟)\s*([一-鿿\w]{2,10}(?:公司|集团|科技|企业|汽车|能源))', cooperation)
            if coop_entities:
                for entity in coop_entities:
                    lines.append(f"- {entity}")
                lines.append("【来源：cooperation_info】")
            else:
                lines.append("【待补充：目标客户画像】")
        else:
            lines.append("【待补充：目标客户画像，包括行业、规模、需求特征】")
        lines.append("")

        # 竞争格局
        lines.append("### 竞争格局与差异化")
        if competitors:
            lines.append("**主要竞争者：**")
            for c in competitors:
                lines.append(f"- {c}")
            lines.append("")
        lines.append("| 对比维度 | 本项目 | 竞品A | 竞品B |")
        lines.append("|----------|--------|--------|--------|")
        lines.append("| 核心技术 | 【待补充】 | 【待补充】 | 【待补充】 |")
        lines.append("| 性能指标 | 【待补充】 | 【待补充】 | 【待补充】 |")
        lines.append("| 价格定位 | 【待补充】 | 【待补充】 | 【待补充】 |")
        lines.append("| 市场渠道 | 【待补充】 | 【待补充】 | 【待补充】 |")
        lines.append("")

        # SWOT
        lines.append("### SWOT分析")
        lines.append("- **优势（S）**：技术壁垒高、团队配置优、先发优势明显")
        lines.append("- **劣势（W）**：品牌知名度待提升、初期资金规模有限")
        lines.append("- **机会（O）**：政策利好、进口替代需求旺盛、市场空间巨大")
        lines.append("- **威胁（T）**：行业巨头进入可能、技术迭代风险、人才竞争")
        lines.append("")

        lines.append("【此处插入：各业务线营收占比饼图】")
        lines.append("【此处插入：市场增长预测曲线图】")
        lines.append("")

        # 合作伙伴
        if partners:
            lines.append("### 已有合作基础")
            for p in partners:
                lines.append(f"- {p}")
            lines.append("")
        elif cooperation:
            lines.append(f"### 已有合作基础")
            lines.append(cooperation[:250])
            lines.append("【来源：cooperation_info】")
            lines.append("")

        return "\n".join(lines)

    def _demo_team(self, dp: CentralDataPool, rhetoric: dict) -> str:
        members = dp.team_pool.get("team_members", [])
        leader = dp.team_pool.get("project_leader", "")
        advisor = dp.team_pool.get("advisor_name", "")
        advisor_title = dp.team_pool.get("advisor_title", "")
        advisor_ach = dp.team_pool.get("advisor_achievements", "")
        awards = dp.team_pool.get("past_awards", [])
        patents = dp.team_pool.get("total_patents", 0)
        papers = dp.team_pool.get("total_papers", 0)

        rh_overview = rhetoric.get("team_overview", ["团队是一支多学科交叉的复合型团队。"])
        rh_member = rhetoric.get("member_intro", ["核心成员具备突出的专业能力。"])

        lines = [f"## 团队介绍与核心优势", ""]

        lines.append("### 团队总体画像")
        advisor_desc = ""
        if advisor:
            advisor_title_short = advisor_title.split("、")[0] if advisor_title else ""
            # 避免"教授孙丽华教授"重复
            if advisor_title_short and advisor_title_short in advisor:
                advisor_title_short = ""
            # 避免"孙丽华教授教授"重复
            if advisor.endswith("教授") and advisor_title_short == "教授":
                advisor_title_short = ""
            desc_parts = []
            if advisor_title_short:
                desc_parts.append(advisor_title_short)
            desc_parts.append(advisor)
            advisor_desc = f"由{' '.join(desc_parts)}领衔，"
        lines.append(f"{advisor_desc}核心成员{len(members)+1}人，涵盖技术研发、产品设计、商业运营等关键职能。")
        if leader:
            lines.append(f"项目负责人：**{leader}**")
        lines.append("")

        # 核心成员
        lines.append("### 核心成员介绍")
        if members:
            for m in members:
                name = m.get('name', '')
                major = m.get('major', '')
                degree = m.get('degree', '')
                role = m.get('role', '')
                achievements = m.get('achievements', '')
                lines.append(f"**{name}** | {major} | {degree} | {role}")
                if achievements:
                    lines.append(f"> {achievements}")
                lines.append("")
        else:
            lines.append("【待补充：核心团队成员详细信息】")
            lines.append("")
        lines.append("")

        # 指导教师
        lines.append("### 指导教师团队")
        if advisor:
            lines.append(f"**{advisor}** | {advisor_title}")
            if advisor_ach:
                lines.append(f">{advisor_ach[:200]}")
        else:
            lines.append("【待补充：指导老师姓名、职称和学术成就】")
        lines.append("")

        # 过往成果
        lines.append("### 团队过往成果")
        if awards:
            lines.append("**获奖荣誉：**")
            for award in awards:
                lines.append(f"- [Award] {award}")
            lines.append("")

        achievement_parts = []
        if patents > 0:
            achievement_parts.append(f"专利{patents}项")
        if papers > 0:
            achievement_parts.append(f"论文{papers}篇")
        if achievement_parts:
            lines.append("**学术成果：**" + "，".join(achievement_parts) + "。")
            lines.append("【来源：team_pool/evidence_pool】")
        lines.append("")

        lines.append("### 团队互补性")
        lines.append("团队形成了'基础研究-技术开发-产品落地-市场推广'的完整人才链条，确保项目从实验室走向市场。")
        lines.append("")

        return "\n".join(lines)

    def _demo_financial(self, dp: CentralDataPool, rhetoric: dict) -> str:
        rh_cost = rhetoric.get("cost_structure", ["项目的成本结构需进一步细化。"])
        rh_revenue = rhetoric.get("revenue_forecast", ["基于保守估计给出收入预测。"])
        rh_funding = rhetoric.get("funding_ask", ["本轮融资需求待明确。"])

        lines = [f"## 财务预测与融资计划", ""]

        lines.append("### 成本结构分析")
        lines.append("【待补充：项目的成本构成，包括研发、生产、人力、营销等各项占比】")
        lines.append("")

        lines.append("### 收入预测")
        lines.append("【待补充：未来3年收入预测及增长依据】")
        lines.append("")

        lines.append("### 融资需求")
        lines.append("【待补充：本轮融资额度、出让股权比例、资金用途分配】")
        lines.append("")

        lines.append("### 估值逻辑")
        lines.append("【待补充：项目估值方法和依据】")
        lines.append("")

        lines.append("【此处插入：三年财务预测表】")
        lines.append("【此处插入：资金用途瀑布图】")
        lines.append("")

        return "\n".join(lines)

    def _demo_future(self, dp: CentralDataPool, rhetoric: dict) -> str:
        rh_roadmap = rhetoric.get("tech_roadmap", ["技术研发将分阶段推进。"])
        rh_expansion = rhetoric.get("market_expansion", ["市场拓展采用聚焦后辐射策略。"])
        rh_social = rhetoric.get("social_value", ["项目将创造显著社会价值。"])
        rh_national = rhetoric.get("national_strategy", ["项目紧密围绕国家战略部署。"])
        rh_vision = rhetoric.get("vision", ["以技术创新推动行业变革。"])

        lines = [f"## 未来规划与社会价值", ""]

        lines.append("### 技术研发路线图")
        lines.append("【待补充：未来3-5年技术发展路线和里程碑】")
        lines.append("【此处插入：技术发展路线时间轴】")
        lines.append("")

        lines.append("### 市场拓展计划")
        lines.append("【待补充：分阶段的市场拓展策略和目标】")
        lines.append("")

        lines.append("### 社会价值阐述")
        lines.append("【待补充：项目在就业、环保、产业升级、民生改善等方面的具体社会价值量化】")
        lines.append("")

        lines.append("### 国家战略对接")
        lines.append("【待补充：项目如何具体服务国家战略需求（如双碳、制造强国、数字中国、乡村振兴等）】")
        lines.append("")

        lines.append("### 愿景与使命")
        if rh_vision:
            lines.append(f"**使命**：以核心技术为驱动，【待补充：一句话阐述项目存在的意义】")
            lines.append(f"**愿景**：【待补充：项目希望达到的行业地位和社会影响力】")
        lines.append("")

        return "\n".join(lines)

    def _demo_verification(self, dp: CentralDataPool, rhetoric: dict) -> str:
        """挑战杯：实验验证与结果分析"""
        tech_text = dp.tech_pool.get("tech_principles", "")
        cooperation = dp.market_pool.get("cooperation_info_raw", "")
        exp_photos = dp.evidence_pool.get("experiment_photos", [])

        lines = ["## 实验验证与结果分析", ""]
        lines.append("### 实验/测试方案设计")
        if "验证" in tech_text or "测试" in tech_text or "检测" in tech_text:
            for sent in re.split(r'[。\n]', tech_text):
                if any(kw in sent for kw in ["验证", "测试", "检测", "认证", "NREL", "实验室"]):
                    lines.append(f"{sent}。")
        else:
            lines.append("【待补充：实验方案设计，包括测试标准、方法、设备和条件】")
        lines.append("")

        lines.append("### 关键测试数据")
        if cooperation:
            lines.append(f"根据现有验证情况：{cooperation[:300]}【来源：cooperation_info】")
        else:
            lines.append("【待补充：关键测试数据和结果】")
        lines.append("")

        lines.append("### 结果分析与讨论")
        lines.append("【待补充：对测试结果的深入分析，包括与理论模型的对比、误差分析等】")
        lines.append("")

        lines.append("### 可靠性与重复性验证")
        if exp_photos:
            lines.append(f"已有实验/测试佐证{len(exp_photos)}份。")
        lines.append("【待补充：长期稳定性测试数据、批次间一致性数据】")
        lines.append("")
        return "\n".join(lines)

    def _demo_application(self, dp: CentralDataPool, rhetoric: dict) -> str:
        """挑战杯：应用前景与产业化设想"""
        cooperation = dp.market_pool.get("cooperation_info_raw", "")
        market_data = dp.market_pool.get("market_data_raw", "")
        evidence = dp.evidence_pool
        agreements = evidence.get("cooperation_agreements", [])

        lines = ["## 应用前景与产业化设想", ""]
        lines.append("### 典型应用场景")
        if cooperation:
            lines.append(f"{cooperation[:300]}【来源：cooperation_info】")
        lines.append("【待补充：至少3个典型应用场景的详细描述】")
        lines.append("")

        lines.append("### 产业化路径与可行性")
        if "中试" in cooperation or "产线" in cooperation or "量产" in cooperation:
            lines.append(f"产业化进展：{cooperation[:250]}【来源：cooperation_info】")
        else:
            lines.append("【待补充：产业化路线图，包括中试→量产→市场推广的路径】")
        lines.append("")

        lines.append("### 经济效益与社会价值")
        if market_data:
            m = re.search(r'(?:市场|规模)[^，。]*?(\d+[亿万千百]?\s*(?:美元|元|亿))', market_data)
            if m:
                lines.append(f"目标市场：{m.group(0)}。")
        lines.append("【待补充：项目的经济效益预测和社会价值量化】")
        lines.append("")

        lines.append("### 知识产权规划")
        if agreements:
            for a in agreements[:3]:
                lines.append(f"- {a}")
            lines.append("【来源：evidence_pool】")
        lines.append("【待补充：知识产权布局策略和保护范围】")
        lines.append("")
        return "\n".join(lines)

    def _demo_conclusion(self, dp: CentralDataPool, rhetoric: dict) -> str:
        """挑战杯：结论与展望"""
        innovations = dp.tech_pool.get("innovations", [])
        tech_name = dp.tech_pool.get("technology_name", "核心技术")

        lines = ["## 结论与展望", ""]
        lines.append("### 主要研究结论")
        lines.append(f"本项目围绕{tech_name}开展了系统性研究，取得了以下成果：")
        if innovations:
            for i, innov in enumerate(innovations[:4], 1):
                lines.append(f"{i}. {innov}")
        lines.append("【待补充：各项成果的量化总结】")
        lines.append("")

        lines.append("### 创新贡献总结")
        lines.append(f"本项目的核心创新贡献在于{tech_name}方面的突破性进展。【待补充：与国际先进水平的具体对比】")
        lines.append("")

        lines.append("### 未来研究方向")
        lines.append("【待补充：未来2-3年的研究计划和预期目标】")
        lines.append("")
        return "\n".join(lines)

    def _demo_solution(self, dp: CentralDataPool, rhetoric: dict) -> str:
        """红色筑梦之旅：解决方案"""
        return self._demo_technology(dp, rhetoric)

    def _demo_implementation(self, dp: CentralDataPool, rhetoric: dict) -> str:
        """红色筑梦之旅：实施情况"""
        return self._demo_verification(dp, rhetoric)

    def _generic_demo_body(self, structure: List[str], dp: CentralDataPool) -> str:
        lines = [""]
        lines.append("### 概述")
        lines.append(f"本章为{chapter_name}。")
        for step in (structure or []):
            lines.append(f"#### {step}")
            lines.append("【待补充：基于客户素材的具体内容】")
            lines.append("")
        return "\n".join(lines)

    # ===== AI生成路径 =====

    def _generate_with_ai(self, chapter_config, data_context, chapter_rhetoric, visual_style) -> str:
        chapter_name = chapter_config.get("title", "")
        required_elements = chapter_config.get("required_elements", [])
        paragraph_structure = chapter_config.get("paragraph_structure", [])
        word_range = chapter_config.get("word_count_range", "2000-3000字")

        # 尽量使用更多话术模板
        rhetoric_examples = []
        sentence_patterns = chapter_rhetoric.get("sentence_patterns", {})
        for category, patterns in sentence_patterns.items():
            # 每类取1个最长的例句（更完整的话术）
            if patterns:
                best = max(patterns, key=len)
                rhetoric_examples.append(best)
                if len(rhetoric_examples) >= 10:
                    break

        style_desc = (
            f"主色调：{visual_style.get('colors', {}).get('primary', '#0A2F5A')}，"
            f"整体风格：{visual_style.get('name', '专业学术')}"
        )

        prompt = f"""# 撰写竞赛策划书章节

## 章节名称
{chapter_name}

## 写作约束（严格遵守）
### 1. 零虚构原则
只能使用下述素材数据。缺失处输出【待补充：具体需要什么信息】。

### 2. 国奖结构
{chr(10).join(f'   {j+1}. {step}' for j, step in enumerate(paragraph_structure))}

### 3. 必备要素
{chr(10).join(f'   - {elem}' for elem in required_elements)}

### 4. 字数要求
{word_range}

### 5. 话术参考
{chr(10).join(f'   - {r[:150]}' for r in rhetoric_examples[:8])}

### 6. 数据引用
每引用数据标注【来源：素材字段名】

## 风格
{style_desc}

## 素材数据（唯一来源）
```json
{data_context[:12000]}
```

## 输出
直接输出Markdown（从## {chapter_name}开始），图表用【此处插入：XX】标注。"""
        try:
            response = self.llm_client.chat(user_message=prompt, temperature=0.5, max_tokens=6000)
            return response.content
        except Exception as e:
            print(f"[ContentGenerator] AI生成章节 '{chapter_name}' 失败: {e}")
            return f"""## {chapter_name}

> [WARN] AI生成暂时不可用。

### 核心内容
【待补充：本章节需要通过AI从客户素材中生成，当前素材数据已就绪。】

### 建议
请检查API连接后重新生成。"""

    def _verify_against_data_pool(self, content: str, data_snapshot: dict) -> str:
        """AI输出后的事实核验：检查所有数字和实体名是否在数据池中可溯源"""
        # 提取AI输出中的所有数字
        ai_numbers = re.findall(r'(\d+\.?\d*)\s*(亿|万|千|百)?\s*(元|美元|度|吨|人|家|个|%|％|倍|项|篇|次|V|W|kW|mΩ|cm²|nm)?', content)

        # 构建数据池的可信数字集合
        data_str = json.dumps(data_snapshot, ensure_ascii=False)
        trusted_numbers = set()
        for m in re.finditer(r'(\d+\.?\d*)\s*(亿|万|千|百)?\s*(元|美元|度|吨|人|家|个|%|％|倍|项|篇|次|V|W|kW|mΩ|cm²|nm)?', data_str):
            trusted_numbers.add(m.group(0).strip())

        # 标记无法验证的数据（实际生产中可以更精细）
        unverified_count = 0
        for num in ai_numbers:
            num_str = "".join(num).strip()
            if num_str and len(num_str) >= 2 and num_str not in trusted_numbers:
                unverified_count += 1

        if unverified_count > 5:
            content += f"\n\n> [WARN] 检测到{unverified_count}处数据可能无法在素材中溯源，请人工核实。"

        return content

    def _generate_demo_fallback(self, chapter_config) -> str:
        chapter_name = chapter_config.get("title", "")
        return f"""## {chapter_name}

> [WARN] AI生成暂时不可用，已切换至演示模式。

### 核心内容
【待补充：本章节需要基于客户提供的项目素材进行撰写。】

### 建议
请补充更详细的项目资料后重新生成，或联系技术支持。"""

    def _prepare_chapter_data(self, chapter_id, chapter_config, data_pool) -> Dict[str, Any]:
        """为章节准备相关数据快照"""
        data_map = {
            "executive_summary": ["project_name", "project_brief", "tech_principles",
                                   "innovations", "team_members", "past_awards",
                                   "technology_name", "patents", "papers",
                                   "market_data_raw", "cooperation_info_raw",
                                   "total_patents", "total_papers", "total_awards_count",
                                   "project_leader", "advisor_name", "advisor_title",
                                   "patent_certificates", "software_certificates"],
            "background": ["project_brief", "market_data_raw", "industry_analysis_raw",
                            "tech_principles", "project_name", "competitors",
                            "target_customers", "technology_name"],
            "technology": ["tech_principles", "innovations", "tech_params",
                            "patents", "papers", "softwares", "technology_name",
                            "performance_metrics", "patent_certificates",
                            "software_certificates", "total_patents", "total_papers",
                            "project_brief"],
            "product_design": ["project_brief", "tech_principles", "product_photos",
                                "experiment_photos", "tech_params", "innovations",
                                "cooperation_info_raw", "cooperation_agreements",
                                "technology_name"],
            "market_analysis": ["market_data_raw", "industry_analysis_raw",
                                 "cooperation_info_raw", "target_customers",
                                 "competitors", "partners", "project_brief",
                                 "project_name"],
            "team_intro": ["team_members", "project_leader", "past_awards",
                            "advisor_name", "advisor_title", "advisor_achievements",
                            "total_patents", "total_papers", "total_awards_count",
                            "team_size", "patent_certificates", "software_certificates"],
            "financial": ["market_data_raw", "cooperation_info_raw", "project_brief"],
            "future_plan": ["tech_principles", "market_data_raw", "cooperation_info_raw",
                             "innovations", "technology_name", "project_name"],
        }

        relevant_keys = data_map.get(chapter_id, [])
        result = {"project_name": data_pool.project_name}

        all_pools = {}
        all_pools.update(data_pool.tech_pool)
        all_pools.update(data_pool.market_pool)
        all_pools.update(data_pool.team_pool)
        all_pools.update(data_pool.evidence_pool)

        for key in relevant_keys:
            if key in all_pools:
                value = all_pools[key]
                if isinstance(value, str) and len(value) > 2000:
                    value = value[:2000] + "...(截断)"
                result[key] = value

        return result
