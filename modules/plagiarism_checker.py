"""
查重预检模块
- 模板句检测：识别国奖常用套话
- n-gram 重复检测：发现跨章节长句重复
- 综合风险评分 + 改写建议
"""

import re
from typing import List
from dataclasses import dataclass, field


@dataclass
class PlagiarismFinding:
    section: str        # 所在章节
    text_snippet: str   # 匹配的文本片段
    risk: str           # low / medium / high / critical
    suggestion: str     # 改写建议


@dataclass
class PlagiarismReport:
    findings: List[PlagiarismFinding] = field(default_factory=list)
    overall_risk: str = "low"           # low / medium / high
    risk_score: int = 0                  # 0-100, 越高越危险
    checked_chars: int = 0

    def summary(self) -> str:
        return (
            f"查重预检：{len(self.findings)}个风险点 / "
            f"整体风险={self.overall_risk}({self.risk_score}分) / "
            f"检查{self.checked_chars}字"
        )


class PlagiarismChecker:
    """查重预检器"""

    # 国奖模板高频句库：(短语, 风险分1-5, 改写建议)
    TEMPLATE_PHRASES = [
        ("被列入国家战略性新兴产业", 4, "替换为具体政策名称和条款号"),
        ("不仅是一项商业机遇，更是国家战略需求", 4, "缩为一句，或引用具体政策原文"),
        ("实现了从0到1的突破", 4, "改为具体的性能提升数值"),
        ("填补了国内空白", 3, "确认有第三方查新报告/鉴定证书支撑"),
        ("成为行业的领军者", 4, "删除或改为具体市场份额目标"),
        ("具有广阔的市场前景", 1, "替换为具体市场规模数据"),
        ("年复合增长率超过", 1, "标注数据来源报告名称和年份"),
        ("被XX、XX等海外巨头垄断", 2, "列出竞品具体市场份额百分比"),
        ("三位一体的商业模式", 2, "用项目特色命名替代通用说法"),
        ("构建了完整的技术壁垒", 2, "细化为具体专利数量和覆盖范围"),
        ("卡脖子", 2, "全文控制在3处以内"),
        ("国产化率不足", 1, "每次出现标注具体数据来源"),
        ("核心技术受制于人", 3, "替换为具体的技术差距量化对比"),
        ("实现了弯道超车", 4, "改为性能参数对比表"),
        ("自主可控", 2, "控制使用频率，避免空泛"),
        ("致力于打造", 3, "改为具体的里程碑目标"),
        ("一站式解决方案", 2, "列出方案包含的具体模块"),
        ("助力产业升级", 1, "说明具体升级的维度和效果"),
        ("为国家战略贡献力量", 3, "指明具体是哪项国家战略、如何贡献"),
    ]

    def check(self, full_text: str) -> PlagiarismReport:
        """执行查重预检"""
        report = PlagiarismReport()
        report.checked_chars = len(full_text)

        # 1. 模板句检测
        for phrase, score, suggestion in self.TEMPLATE_PHRASES:
            count = full_text.count(phrase)
            if count >= 2 or (count >= 1 and score >= 4):
                for m in re.finditer(re.escape(phrase), full_text):
                    ctx = full_text[max(0,m.start()-20):min(len(full_text),m.end()+20)]
                    report.findings.append(PlagiarismFinding(
                        section=self._which_section(full_text, m.start()),
                        text_snippet=ctx.replace('\n',' ').strip(),
                        risk="high" if score>=4 else ("medium" if score>=2 else "low"),
                        suggestion=suggestion,
                    ))

        # 2. n-gram 长句重复（≥18字跨章节重复）
        sentences = re.split(r'[。！？\n]', full_text)
        sentences = [s.strip() for s in sentences if len(s.strip()) >= 18]
        fingerprints = {}
        for s in sentences:
            for i in range(len(s)-14):
                fg = s[i:i+15]
                if fg in fingerprints and fingerprints[fg] != s:
                    report.findings.append(PlagiarismFinding(
                        section="全文",
                        text_snippet=f"重复句段: {fg}...",
                        risk="medium",
                        suggestion="跨章节存在高度相似内容，建议改写其中一处",
                    ))
                    break
                fingerprints[fg] = s

        # 3. 风险评分（上限80，留20分给未知风险）
        hi = sum(1 for f in report.findings if f.risk == "high")
        md = sum(1 for f in report.findings if f.risk == "medium")
        report.risk_score = min(80, hi * 12 + md * 4 + len(report.findings))
        if report.risk_score >= 50:
            report.overall_risk = "high"
        elif report.risk_score >= 20:
            report.overall_risk = "medium"

        return report

    def _which_section(self, text: str, pos: int) -> str:
        before = text[:pos]
        secs = re.findall(r'^## (.+)$', before, re.MULTILINE)
        return secs[-1] if secs else "未知章节"

    def format_markdown(self, report: PlagiarismReport) -> str:
        """生成 Markdown 查重报告"""
        lines = [
            "# 查重预检报告",
            f"整体风险：**{report.overall_risk}**（{report.risk_score}分）",
            f"检查字数：{report.checked_chars}字",
            f"风险点：{len(report.findings)}处",
            "",
            "| 风险 | 章节 | 文本片段 | 建议 |",
            "|------|------|----------|------|",
        ]
        for f in report.findings[:15]:
            icon = {"critical":"🔴","high":"🟠","medium":"🟡","low":"⚪"}.get(f.risk,"")
            lines.append(f"| {icon} {f.risk} | {f.section} | {f.text_snippet[:40]}... | {f.suggestion} |")
        lines.append("")
        if report.overall_risk == "high":
            lines.append("> ⚠️ 查重风险较高，建议在提交前进行个性化改写。重点修改标红段落。")
        return "\n".join(lines)
