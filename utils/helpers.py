"""
全自动竞赛策划智能体 - 工具函数
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


def ensure_dir(dir_path: Path) -> Path:
    """确保目录存在，不存在则创建"""
    dir_path = Path(dir_path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def read_text_file(file_path: Path) -> str:
    """读取文本文件，自动处理编码"""
    encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"无法解码文件: {file_path}")


def write_text_file(file_path: Path, content: str, encoding: str = "utf-8") -> None:
    """写入文本文件"""
    ensure_dir(file_path.parent)
    with open(file_path, "w", encoding=encoding) as f:
        f.write(content)


def extract_numbers(text: str) -> List[Dict[str, str]]:
    """
    从文本中提取所有可量化数据实体
    返回格式: [{"value": "100亿", "unit": "元", "context": "市场规模"}, ...]
    """
    patterns = [
        # 带单位的数字: "100亿元", "320万度", "48%"
        r'(\d+\.?\d*)\s*(亿|万|千|百)?\s*(元|美元|度|吨|人|家|个|%|％|倍|项|篇|次)',
        # 纯数字关键指标
        r'(\d+\.?\d*)\s*(GB|TB|Mbps|nm|μm|cm|mm|V|W|kW|MHz|GHz)',
    ]

    results = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            # 获取上下文（前后20字）
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end].replace('\n', ' ').strip()

            # 构建完整单位：合并magnitude(group2)和unit(group3) for pattern 1
            if match.lastindex >= 3:
                unit = (match.group(2) or "") + (match.group(3) or "")
            elif match.lastindex >= 2:
                unit = match.group(2) or ""
            else:
                unit = ""
            results.append({
                "full_match": match.group(0),
                "value": match.group(1),
                "unit": unit,
                "context": context,
                "position": match.start(),
            })

    return results


def sanitize_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    illegal_chars = r'[<>:"/\\|?*\n\r\t]'
    name = re.sub(illegal_chars, '_', name)
    name = name.strip().strip('.')
    if len(name) > 200:
        name = name[:200]
    return name or "untitled"


def format_change_log(changes: List[Dict[str, str]]) -> str:
    """
    格式化变更日志
    changes: [{"section": "第三章", "before": "...", "after": "...", "reason": "..."}, ...]
    """
    log_lines = [
        f"# 修改日志",
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"共 {len(changes)} 处修改\n",
    ]

    for i, change in enumerate(changes, 1):
        log_lines.append(f"## 修改 {i}：{change.get('section', '未指定章节')}")
        log_lines.append(f"- **修改前**：{change.get('before', 'N/A')}")
        log_lines.append(f"- **修改后**：{change.get('after', 'N/A')}")
        log_lines.append(f"- **原因**：{change.get('reason', '客户要求')}")
        log_lines.append("")

    return "\n".join(log_lines)


def load_json(file_path: Path) -> dict:
    """加载JSON文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: dict) -> None:
    """保存JSON文件"""
    ensure_dir(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_sections_from_markdown(md_text: str) -> Dict[str, str]:
    """从Markdown文本中按##标题拆分为章节"""
    sections = {}
    current_section = "前言"
    current_content = []

    for line in md_text.split('\n'):
        if line.startswith('## '):
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[3:].strip()
            current_content = []
        elif line.startswith('# '):
            if current_content:
                sections[current_section] = '\n'.join(current_content).strip()
            current_section = line[2:].strip()
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = '\n'.join(current_content).strip()

    return sections


def compare_numbers_across_chapters(chapters: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    跨章节数据一致性检查（去重+容忍度）
    只标记真实矛盾：同一指标在不同章节中出现不同数值
    不标记合理复用：同一数值在不同章节自然出现（如3.2V、15%等）
    """
    # 按"指标名+数值"分组，检测真正的矛盾
    metric_values = {}  # {metric_key: {value: [chapters]}}

    for chapter_name, content in chapters.items():
        numbers = extract_numbers(content)
        for num in numbers:
            context = num.get("context", "")
            value = num.get("value", "")
            unit = num.get("unit", "")

            # 提取上下文中的关键词作为"指标名"
            metric = _extract_metric_name(context)
            key = f"{metric}|{unit}" if metric else f"{value}{unit}"

            if key not in metric_values:
                metric_values[key] = {}
            val_key = f"{value}{unit}"
            if val_key not in metric_values[key]:
                metric_values[key][val_key] = []
            metric_values[key][val_key].append(chapter_name)

    conflicts = []
    for metric_key, value_map in metric_values.items():
        # 如果同一个指标在不同章节有不同数值 → 真正的矛盾
        if len(value_map) > 1:
            values_list = list(value_map.items())
            for i in range(len(values_list)):
                for j in range(i + 1, len(values_list)):
                    val_a, chapters_a = values_list[i]
                    val_b, chapters_b = values_list[j]
                    # 排除明显是不同指标的情况（key太短可能是噪声）
                    metric_name = metric_key.split("|")[0]
                    if len(metric_name) >= 2 and len(val_a) >= 2 and len(val_b) >= 2:
                        conflicts.append({
                            "value": f"{val_a} vs {val_b}",
                            "metric": metric_name,
                            "occurrences": [
                                {"chapter": chapters_a[0], "context": f"指标={metric_name}, 值={val_a}"},
                                {"chapter": chapters_b[0], "context": f"指标={metric_name}, 值={val_b}"},
                            ],
                        })

    return conflicts


def _extract_metric_name(context: str) -> str:
    """从数字上下文提取指标名称"""
    # 排除竞品对比场景（"vs"、"竞品"、"相较于"等）
    if re.search(r'(?:竞品|相较于|对比|vs\.?|VS\.?)', context):
        return f"_comparison_{hash(context) % 10000}"  # 每个对比场景唯一标记，不参与跨章节比较

    # 常见指标模式
    patterns = [
        r'(阈值电压|比导通电阻|位错密度|能效比|可靠性|效率)',
        r'(国产化率|市场规模|年复合增长率|CAGR)',
        r'(专利|论文|获奖|团队成员|导师)',
        r'(节能|减排|降碳|能耗|PUE)',
        r'(衰减|提升|降低|优化)',
    ]
    for pattern in patterns:
        match = re.search(pattern, context)
        if match:
            return match.group(1)

    # 提取上下文中的中文关键词（最近的名词）
    words = re.findall(r'[一-鿿]{2,6}', context)
    if words:
        return words[-1]

    return ""
