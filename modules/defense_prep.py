"""
答辩预演模块
- 基于策划书内容自动生成评委可能提问的问题清单
- 提供每个问题的建议回答思路
- 生成300字执行摘要 + 1分钟路演稿
- 生成3分钟电梯演讲脚本
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DefenseQuestion:
    category: str
    question: str
    difficulty: str
    suggested_answer: str
    related_chapter: str


@dataclass
class DefensePrepReport:
    project_name: str
    questions: List[DefenseQuestion]
    elevator_pitch: str
    defense_tips: List[str]
    generated_at: str


class DefensePrep:
    """
    答辩预演模块

    基于国奖评审经验，生成多维度的评委提问清单和答辩指导。
    面向竞赛答辩场景，覆盖：
    - 技术创新类问题
    - 商业模式类问题
    - 团队与执行类问题
    - 社会价值类问题
    - 数据真实性类问题
    """

    # 各维度的典型评委提问模板
    QUESTION_TEMPLATES = {
        "技术创新": [
            {
                "question": "请用通俗的语言解释你们的核心技术原理，让非专业人士也能理解。",
                "difficulty": "基础",
                "template": "建议用打比方的方式解释，例如'如果传统方案是XX，我们就像YY一样...'，重点说清楚'做了什么'和'为什么更好'。"
            },
            {
                "question": "你们的技术壁垒在哪里？如何防止被模仿或超越？",
                "difficulty": "中等",
                "template": "从三个层面回答：1) 技术复杂度（工艺/算法门槛）2) 专利保护（已布局XX项）3) 先发优势和持续迭代能力。"
            },
            {
                "question": "你们的技术与现有方案相比，具体在哪些指标上有优势？优势有多大？",
                "difficulty": "中等",
                "template": "用具体数据对比，至少列出3个关键指标的本方案vs竞品的数值对比表，并说明数据来源。"
            },
            {
                "question": "你们的技术目前处于什么阶段（TRL几级）？距离实际应用还有多远？",
                "difficulty": "关键",
                "template": "诚实说明技术成熟度（实验室验证/小试/中试/小批量），给出明确的时间节点和里程碑。"
            },
            {
                "question": "技术方案中最大的不确定性是什么？如果关键技术路线走不通，有备选方案吗？",
                "difficulty": "困难",
                "template": "展示对技术风险的认识和Plan B，体现科学严谨性。可以说'我们在XX方面有YY作为备选...'"
            },
        ],
        "商业模式": [
            {
                "question": "你们的盈利模式是什么？什么时候可以实现盈亏平衡？",
                "difficulty": "关键",
                "template": "清晰说明收入来源（产品/服务/授权等），给出盈亏平衡的时间预估和计算依据。"
            },
            {
                "question": "目标市场的规模是多少？你们的市场占有率目标？",
                "difficulty": "基础",
                "template": "引用权威第三方数据，用TAM-SAM-SOM模型分析，占有率目标要合理。"
            },
            {
                "question": "你们的定价策略是什么？凭什么比竞品贵/便宜？",
                "difficulty": "中等",
                "template": "如果定价高：强调性能和品牌溢价；如果定价低：强调成本优势和技术降本。"
            },
            {
                "question": "如果有巨头进入这个市场，你们如何应对？",
                "difficulty": "困难",
                "template": "展示差异化优势（技术深度/客户关系/敏捷性），不要回避竞争。"
            },
        ],
        "团队与执行": [
            {
                "question": "为什么是你们这个团队来做这件事？你们的独特优势是什么？",
                "difficulty": "基础",
                "template": "强调团队成员的互补性、技术积累、行业经验和过往成果。"
            },
            {
                "question": "团队成员之间如何分工？谁负责技术，谁负责市场？",
                "difficulty": "基础",
                "template": "清晰说明分工逻辑，体现'专业的人做专业的事'。"
            },
            {
                "question": "如果核心成员离开，项目还能继续吗？",
                "difficulty": "困难",
                "template": "说明知识沉淀机制（文档/专利/流程）、人才梯队建设和激励方案。"
            },
        ],
        "社会价值": [
            {
                "question": "你们的项目对社会有什么价值？",
                "difficulty": "基础",
                "template": "从经济效益（就业/税收）、环境效益（减排/节能）、产业升级（国产替代/技术引领）等方面阐述。"
            },
            {
                "question": "项目如何响应国家战略？与哪些政策方向契合？",
                "difficulty": "中等",
                "template": "对应具体政策文件（如十四五规划/双碳目标/制造强国等），说明项目的战略意义。"
            },
        ],
        "数据验证": [
            {
                "question": "你们的数据是如何获得的？是否经过第三方验证？",
                "difficulty": "关键",
                "template": "说明数据来源（自测/第三方检测/用户反馈），如有权威机构的检测报告请展示。"
            },
            {
                "question": "市场规模数据的来源是什么？",
                "difficulty": "中等",
                "template": "引用具体机构名称和报告年份，展示对行业的深入理解。"
            },
        ],
    }

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate_defense_prep(self, full_text: str, project_name: str) -> DefensePrepReport:
        """
        生成答辩准备报告

        Args:
            full_text: 完整策划书文本
            project_name: 项目名称

        Returns:
            DefensePrepReport: 答辩准备报告
        """
        questions = self._generate_all_questions(full_text)
        elevator_pitch = self._generate_elevator_pitch(full_text, project_name)
        defense_tips = self._generate_defense_tips(len(questions))

        return DefensePrepReport(
            project_name=project_name,
            questions=questions,
            elevator_pitch=elevator_pitch,
            defense_tips=defense_tips,
            generated_at=datetime.now().isoformat(),
        )

    def _generate_all_questions(self, full_text: str) -> List[DefenseQuestion]:
        """生成所有维度的评委提问"""
        all_questions = []

        for category, templates in self.QUESTION_TEMPLATES.items():
            for tmpl in templates:
                # 根据策划书内容判断该问题是否相关
                if self._is_question_relevant(tmpl["question"], full_text, category):
                    suggested = self._personalize_answer(tmpl["template"], full_text, category)
                    all_questions.append(DefenseQuestion(
                        category=category,
                        question=tmpl["question"],
                        difficulty=tmpl["difficulty"],
                        suggested_answer=suggested,
                        related_chapter=self._find_related_chapter(category),
                    ))

        # 基于策划书内容动态生成额外问题
        dynamic_questions = self._generate_dynamic_questions(full_text)
        all_questions.extend(dynamic_questions)

        return all_questions

    def _is_question_relevant(self, question: str, full_text: str, category: str) -> bool:
        """判断问题是否与策划书相关"""
        # 技术类问题：检查是否有技术描述
        if category == "技术创新":
            return "技术" in full_text or "创新" in full_text
        # 商业类：检查是否有市场数据
        if category == "商业模式":
            return "市场" in full_text or "营收" in full_text or "商业模式" in full_text
        # 团队类：总是相关
        if category == "团队与执行":
            return "团队" in full_text or "成员" in full_text
        return True

    def _personalize_answer(self, template: str, full_text: str, category: str) -> str:
        """基于策划书内容个性化回答模板"""
        # 尝试提取关键词填入模板
        project_name_match = re.search(r'# (.+)', full_text)
        project_name = project_name_match.group(1) if project_name_match else "本项目"

        personalized = template.replace("XX", project_name[:10])

        # 提取技术名
        tech_matches = re.findall(r'(?:创新|提出|研发)了[「"]([^」"]+)[」"]', full_text)
        if tech_matches and "XX" in personalized:
            personalized = personalized.replace("XX", tech_matches[0][:10], 1)

        return personalized

    def _find_related_chapter(self, category: str) -> str:
        mapping = {
            "技术创新": "核心技术原理与创新",
            "商业模式": "市场分析与商业模式",
            "团队与执行": "团队介绍与核心优势",
            "社会价值": "未来规划与社会价值",
            "数据验证": "全文（跨章节数据一致性）",
        }
        return mapping.get(category, "全文")

    def _generate_dynamic_questions(self, full_text: str) -> List[DefenseQuestion]:
        """基于策划书内容动态生成针对性问题"""
        dynamic = []

        # 检测缺失标记
        missing_count = full_text.count("【待补充")
        if missing_count > 3:
            dynamic.append(DefenseQuestion(
                category="数据验证",
                question=f"策划书中有{missing_count}处信息待补充，这些缺失是否影响对项目完整性的判断？",
                difficulty="关键",
                suggested_answer="坦诚说明这些数据的状态，并承诺在答辩前补充完整。可以口头补充关键数据来弥补。",
                related_chapter="全文",
            ))

        # 检测是否有竞品对比
        if "竞品" in full_text and "【待补充】" in full_text[full_text.index("竞品"):full_text.index("竞品")+200] if "竞品" in full_text else False:
            pass  # 竞品数据不完整的情况已在上面覆盖

        # 检查融资计划
        if "融资" not in full_text or "【待补充】" in full_text[full_text.index("融资"):full_text.index("融资")+100] if "融资" in full_text else True:
            dynamic.append(DefenseQuestion(
                category="商业模式",
                question="你们的融资需求和资金用途是什么？",
                difficulty="关键",
                suggested_answer="即使策划书中未详细列出，也请在口头回答时准备：融资金额、出让比例、资金用途分配（研发/市场/团队）、预期里程碑。",
                related_chapter="财务预测与融资计划",
            ))

        return dynamic

    def _generate_elevator_pitch(self, full_text: str, project_name: str) -> str:
        """生成3分钟电梯演讲脚本"""
        # 提取关键信息
        lines = full_text.split('\n')
        first_tech = ""
        first_innovation = ""

        for line in lines:
            if "创新" in line and "：" in line and not first_innovation:
                first_innovation = line.strip().lstrip("- ")[:60]
                break

        pitch = f"""# 3分钟电梯演讲脚本

## 开场（30秒）—— 抓住注意力
各位评委老师好！我是{project_name}的负责人。
我今天带来的项目是【用一句话描述你们做什么】。

## 痛点（30秒）—— 为什么值得做
当前，【描述行业痛点】，这个问题严重影响了【受影响的对象】。
现有的解决方案【有什么不足】。

## 方案（60秒）—— 你们怎么做
我们提出的解决方案是【核心技术/产品名称】。
与现有方案相比，我们的核心优势是：【列出2-3个最有说服力的差异化优势，用数据说话】。
{first_innovation if first_innovation else "【请根据策划书填入核心创新点】"}

## 成果（30秒）—— 证明你们行
目前我们已取得【已申请X项专利/X篇论文/获得X项奖项】，
【已有X家企业合作/意向订单/用户验证】。

## 愿景（30秒）—— 未来要做什么
我们的目标是【3年内的目标】，本轮计划融资【X万元】，
用于【资金主要用途】。

## 结束语
这就是我们的项目，感谢各位评委老师！请多提宝贵意见。

---
*注：方括号【】中的内容请根据策划书实际数据填入。练习时请计时，控制在2.5-3分钟内。*
"""
        return pitch

    def _generate_defense_tips(self, question_count: int) -> List[str]:
        return [
            "**黄金法则**：先结论后解释。每个回答先给出一句话结论，再展开论证。",
            "**数据为王**：能用数据回答的绝不用形容词。随身携带关键数据小卡片。",
            "**诚实为本**：不知道就说不知道，但接着说'我们正在研究/测试'，展示进取心。",
            "**眼神交流**：回答时与提问评委保持眼神接触，展现自信。",
            "**时间控制**：每个回答控制在1-2分钟，不要超时。",
            "**团队配合**：让每个成员都有发言机会，展现团队实力。",
            f"**充分准备**：本次共生成{question_count}个潜在问题，建议团队逐一模拟练习。",
            "**录音复盘**：模拟答辩时录音，事后复盘改进。",
        ]

    def print_report(self, report: DefensePrepReport) -> str:
        """格式化输出答辩准备报告"""
        lines = [
            "=" * 60,
            "  [Award] 答辩预演报告",
            "=" * 60,
            f"项目：{report.project_name}",
            f"生成时间：{report.generated_at}",
            f"潜在问题数：{len(report.questions)}个",
            "",
            "━" * 40,
            "  评委可能提问（按类别整理）",
            "━" * 40,
        ]

        categories = {}
        for q in report.questions:
            if q.category not in categories:
                categories[q.category] = []
            categories[q.category].append(q)

        for cat, qs in categories.items():
            lines.append(f"\n### {cat} ({len(qs)}题)")
            for i, q in enumerate(qs, 1):
                diff_icon = {"基础": "[i]", "中等": "[WARN]", "关键": "[ALERT]", "困难": "[ALERT]"}.get(q.difficulty, "")
                lines.append(f"\n**Q{i}** [{q.difficulty}] {q.question}")
                lines.append(f"> 建议回答思路：{q.suggested_answer[:200]}")

        lines.append(f"\n{'━' * 40}")
        lines.append("  3分钟电梯演讲")
        lines.append(f"{'━' * 40}")
        lines.append(report.elevator_pitch)

        lines.append(f"\n{'━' * 40}")
        lines.append("  答辩技巧提醒")
        lines.append(f"{'━' * 40}")
        for tip in report.defense_tips:
            lines.append(f"- {tip}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def generate_summary(self, full_text: str, project_name: str) -> str:
        """生成300字执行摘要 + 1分钟路演稿"""
        # 提取关键数据
        tech_match = re.findall(r'(?:创新|核心技术|自主研发)[：:]*([^。\n]{10,80})', full_text)
        param_match = re.findall(r'(\w+(?:效率|纯度|精度|速度|能耗|成本|指标)[^\n]{5,60})', full_text)
        market_match = re.search(r'(?:市场|规模)[^。]*?(\d+\.?\d*\s*[亿万]?\s*(?:美元|元|亿).*?)(?:[。；]|$)', full_text)
        award_match = re.findall(r'(?:获奖|一等奖|二等奖|特等奖|金奖|银奖)[^\n]{5,40}', full_text)
        patent_match = re.search(r'(\d+\s*项\s*(?:发明)?专利)', full_text)

        tech = tech_match[0][:60] if tech_match else "核心技术突破"
        params = "、".join(param_match[:3]) if param_match else "关键性能指标"
        market = market_match.group(0)[:50] if market_match else "目标市场"
        awards = award_match[0][:30] if award_match else "多项竞赛奖项"
        patents = patent_match.group(0) if patent_match else "多项专利"

        summary = f"""# 执行摘要（300字）

{project_name}，聚焦于{tech}。项目{params}，在核心指标上达到国际先进水平。

市场方面，{market}，增长潜力巨大。团队已{awards}，拥有{patents}，具备扎实的技术积累和产业化基础。

项目采用自主创新的技术路线，通过产学研协同，已与多家行业头部企业达成合作意向，为后续规模化推广奠定基础。未来三年，项目计划完成产品迭代和产能扩建，力争成为细分领域的国内领军者。

---

# 1分钟路演稿

各位评委老师好！我是{project_name}的负责人。

【30秒 - 痛点】{tech}是行业核心瓶颈，现有方案存在成本高、效率低的问题。

【30秒 - 方案】我们自主研发了{tech}，核心指标{params}，已获{patents}。

【30秒 - 成果】项目已{awards}，市场{market}。本轮融资用于产品迭代和市场拓展。

谢谢！
"""
        return summary
