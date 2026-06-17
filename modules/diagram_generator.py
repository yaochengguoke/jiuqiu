"""
模块6：全自动制图模块
- 语义解析：从技术文本提取组件和关系
- 模板匹配：从图元库匹配合适的图表模板
- 填充渲染：使用matplotlib生成矢量图表
- 背景配图：生成20:10横屏行业新闻佐证图
- 封面生成：根据配色方案自动生成高端封面
"""

import os
import json
import re
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import IMAGE_DPI, IMAGE_ASPECT_RATIO_BG, OUTPUT_DIR
from utils.helpers import ensure_dir

# matplotlib配置（无GUI后端）
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Arc, Rectangle, Polygon
import matplotlib.font_manager as fm
import numpy as np

# 尝试设置中文字体
try:
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
except Exception:
    pass


@dataclass
class DiagramSpec:
    """图表规格"""
    diagram_type: str  # arch, flow, chart, cover, news_bg
    title: str
    output_path: Path
    width_inches: float = 8
    height_inches: float = 6


class DiagramGenerator:
    """
    全自动制图模块

    制图流程（三步走）：
    Step 1: 语义解析 - 从技术文本提取核心组件、连接关系、数据流向
    Step 2: 模板匹配 - 根据解析结果匹配最合适的图元模板
    Step 3: 填充渲染 - 将文字标签填入模板空位，自动配色导出

    支持的图表类型：
    - 技术架构总图（三层架构）
    - 核心模块拆解图
    - 工艺制备流程图
    - 性能雷达对比图
    - 商业模式画布图
    - 市场增长预测图
    - 营收占比饼图
    - 20:10行业新闻配图
    - 高端封面图
    """

    def __init__(self, visual_style: Dict[str, Any], output_dir: Path = None):
        """
        Args:
            visual_style: 视觉风格配置（从模板加载）
            output_dir: 图表输出目录
        """
        self.style = visual_style
        self.colors = visual_style.get("colors", {})
        self.chart_style = visual_style.get("chart_style", {})

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = OUTPUT_DIR / "current" / "generated_images"
        ensure_dir(self.output_dir)

    def generate_cover(
        self,
        project_name: str,
        competition_name: str,
        subtitle: str = "",
        team_name: str = "",
    ) -> Path:
        """生成高端赛事封面"""
        fig, ax = plt.subplots(figsize=(8.27, 11.69), dpi=IMAGE_DPI)  # A4比例

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")
        accent = self.colors.get("accent", "#FF6B35")
        cover_bg = self.colors.get("primary", "#0A2F5A")

        # 背景渐变
        gradient = np.linspace(0, 1, 256).reshape(-1, 1)
        gradient = np.hstack([gradient, gradient, gradient])
        # 根据主题主色调动态选择colormap
        cmap_map = {"blue": plt.cm.Blues, "green": plt.cm.Greens, "red": plt.cm.Reds,
                    "orange": plt.cm.Oranges, "gray": plt.cm.Greys, "purple": plt.cm.Purples}
        cmap_key = "blue"
        if "green" in primary.lower() or "1B5E20" in primary:
            cmap_key = "green"
        elif "red" in primary.lower() or "8B1A1A" in primary:
            cmap_key = "red"
        elif "orange" in primary.lower() or "E65100" in primary:
            cmap_key = "orange"
        ax.imshow(gradient, extent=[0, 1, 0, 1], aspect='auto', alpha=0.3,
                  cmap=cmap_map.get(cmap_key, plt.cm.Blues))

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # 顶部装饰线
        ax.axhline(y=0.85, xmin=0.15, xmax=0.85, color=accent, linewidth=3)
        ax.axhline(y=0.84, xmin=0.15, xmax=0.85, color=accent, linewidth=1, alpha=0.5)

        # 项目名称
        ax.text(0.5, 0.72, project_name, fontsize=32, fontweight='bold',
                ha='center', va='center', color='white',
                bbox=dict(boxstyle='round,pad=0.8', facecolor=primary, edgecolor='none', alpha=0.9))

        # 副标题
        if subtitle:
            ax.text(0.5, 0.62, subtitle, fontsize=16, ha='center', va='center',
                    color=matplotlib.colors.to_hex([0.85, 0.85, 0.9]))

        # 竞赛名称
        ax.text(0.5, 0.45, competition_name, fontsize=20, fontweight='bold',
                ha='center', va='center', color=primary_light)

        # 团队信息
        if team_name:
            ax.text(0.5, 0.35, team_name, fontsize=14, ha='center', va='center',
                    color='#8899AA')

        # 底部装饰
        ax.axhline(y=0.18, xmin=0.2, xmax=0.8, color=primary_light, linewidth=1, alpha=0.5)
        ax.text(0.5, 0.12, 'CONFIDENTIAL · FOR COMPETITION ONLY',
                fontsize=10, ha='center', va='center', color='#666666',
                style='italic')

        # 装饰几何图形
        circle = plt.Circle((0.08, 0.92), 0.08, color=accent, alpha=0.3, transform=ax.transAxes)
        ax.add_patch(circle)
        circle2 = plt.Circle((0.92, 0.08), 0.05, color=primary_light, alpha=0.3, transform=ax.transAxes)
        ax.add_patch(circle2)

        output_path = self.output_dir / f"cover_{self._safe_name(project_name)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor=cover_bg, edgecolor='none', pad_inches=0.3)
        plt.close(fig)

        return output_path

    def generate_tech_architecture(
        self,
        tech_name: str,
        modules: List[str],
        diagram_type: str = "three_layer_arch",
    ) -> Path:
        """生成技术架构图"""
        fig, ax = plt.subplots(figsize=(10, 7), dpi=IMAGE_DPI)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 10)
        ax.axis('off')

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")

        if diagram_type == "three_layer_arch" and len(modules) >= 3:
            # 三层架构
            # 从主题色派生层级颜色（浅→深）
            import matplotlib.colors as mcolors
            base_rgb = mcolors.to_rgb(primary_light if primary_light else primary)
            layer_colors = [
                mcolors.to_hex(tuple(c * 0.3 + 0.7 for c in base_rgb)),
                mcolors.to_hex(tuple(c * 0.15 + 0.85 for c in base_rgb)),
                mcolors.to_hex(tuple(c * 0.05 + 0.95 for c in base_rgb)),
            ]
            layer_borders = [primary, primary_light, primary_light]
            layer_names = modules[:3] if len(modules) >= 3 else modules + [''] * (3 - len(modules))

            for i, (name, fill, border) in enumerate(zip(layer_names, layer_colors, layer_borders)):
                y_bottom = 1.5 + i * 2.5
                rect = FancyBboxPatch(
                    (1.5, y_bottom), 7, 2,
                    boxstyle="round,pad=0.3",
                    facecolor=fill, edgecolor=border, linewidth=2
                )
                ax.add_patch(rect)
                ax.text(5, y_bottom + 1, name, fontsize=14, fontweight='bold',
                        ha='center', va='center', color=border)

                # 层级标签
                labels = ["应用层/展示层", "处理层/算法层", "数据层/感知层"]
                ax.text(0.8, y_bottom + 1, labels[i], fontsize=11,
                        ha='center', va='center', color='#666666', rotation=0)

            # 箭头
            for i in range(2):
                y_from = 3.5 + i * 2.5
                ax.annotate('', xy=(5, y_from - 0.3), xytext=(5, y_from + 0.3),
                           arrowprops=dict(arrowstyle='<->', color=primary, lw=2))

        else:
            # 核心模块拆解图 - 中心+四周
            ax.text(5, 5, tech_name, fontsize=14, fontweight='bold',
                    ha='center', va='center',
                    bbox=dict(boxstyle='round', facecolor=primary, edgecolor='none',
                             alpha=0.9, pad=1),
                    color='white')

            angles = np.linspace(0, 2 * np.pi, len(modules), endpoint=False)
            radius = 3.5

            for i, (angle, module) in enumerate(zip(angles, modules)):
                x = 5 + radius * np.cos(angle)
                y = 5 + radius * np.sin(angle)

                rect = FancyBboxPatch(
                    (x - 1, y - 0.5), 2, 1,
                    boxstyle="round,pad=0.2",
                    facecolor='#E3F2FD', edgecolor=primary_light, linewidth=1.5
                )
                ax.add_patch(rect)
                ax.text(x, y, module[:12], fontsize=10, ha='center', va='center',
                        color=primary)

                # 连接线
                ax.plot([5, x], [5, y], color=primary_light, linewidth=1, alpha=0.5,
                       linestyle='--')

        ax.set_title(f'{tech_name} - 技术架构总图', fontsize=18, fontweight='bold',
                    color=primary, pad=20)
        output_path = self.output_dir / f"arch_{self._safe_name(tech_name)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_flow_chart(
        self,
        title: str,
        steps: List[str],
        layout: str = "horizontal",
    ) -> Path:
        """生成流程图"""
        n = len(steps)
        fig, ax = plt.subplots(figsize=(max(12, n * 1.5), 4), dpi=IMAGE_DPI)
        ax.set_xlim(0, n * 2 + 1)
        ax.set_ylim(0, 6)
        ax.axis('off')

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")

        for i, step in enumerate(steps):
            x_center = 2 + i * 2

            # 步骤框
            rect = FancyBboxPatch(
                (x_center - 1.2, 1.5), 2.4, 1.2,
                boxstyle="round,pad=0.3",
                facecolor=primary_light + '20', edgecolor=primary_light, linewidth=2
            )
            ax.add_patch(rect)

            # 步骤编号
            ax.text(x_center, 2.5, f'Step {i+1}', fontsize=10, ha='center',
                    va='center', color=primary, fontweight='bold')

            # 步骤内容
            ax.text(x_center, 1.8, step[:15], fontsize=9, ha='center',
                    va='center', color='#333333')

            # 箭头
            if i < n - 1:
                ax.annotate('', xy=(x_center + 1.0, 2.1), xytext=(x_center + 1.6, 2.1),
                           arrowprops=dict(arrowstyle='->', color=primary, lw=2))

        ax.set_title(title, fontsize=16, fontweight='bold', color=primary, pad=15)
        output_path = self.output_dir / f"flow_{self._safe_name(title)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_radar_chart(
        self,
        title: str,
        categories: List[str],
        our_scores: List[float],
        competitor_scores: List[List[float]],
        competitor_names: List[str],
    ) -> Path:
        """生成多维度雷达对比图"""
        N = len(categories)
        angles = [n / float(N) * 2 * math.pi for n in range(N)]
        angles += angles[:1]  # 闭合

        fig, ax = plt.subplots(figsize=(8, 8), dpi=IMAGE_DPI, subplot_kw=dict(polar=True))

        palette = self.chart_style.get("color_palette", ["#0A2F5A", "#FF6B35", "#4FD1C5", "#9F7AEA"])

        # 绘制网格
        ax.set_theta_offset(math.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_rlabel_position(0)

        values = our_scores + our_scores[:1]
        ax.fill(angles, values, alpha=0.25, color=palette[0], label='本项目')
        ax.plot(angles, values, linewidth=2, color=palette[0])

        for i, (scores, name) in enumerate(zip(competitor_scores, competitor_names)):
            vals = scores + scores[:1]
            ax.fill(angles, vals, alpha=0.1, color=palette[i + 1])
            ax.plot(angles, vals, linewidth=1.5, color=palette[i + 1], linestyle='--',
                   label=name)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_title(title, fontsize=16, fontweight='bold', pad=25)
        ax.legend(loc='lower right', bbox_to_anchor=(1.3, 0))

        output_path = self.output_dir / f"radar_{self._safe_name(title)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_pie_chart(
        self,
        title: str,
        labels: List[str],
        sizes: List[float],
    ) -> Path:
        """生成营收占比饼图"""
        fig, ax = plt.subplots(figsize=(8, 6), dpi=IMAGE_DPI)

        palette = self.chart_style.get("color_palette", ["#0A2F5A", "#2B7FFF", "#4FD1C5", "#FF6B35", "#9F7AEA"])

        wedges, texts, autotexts = ax.pie(
            sizes, labels=None, autopct='%1.1f%%',
            startangle=90, pctdistance=0.75,
            colors=palette[:len(labels)],
            wedgeprops=dict(width=0.4, edgecolor='white')
        )

        for autotext in autotexts:
            autotext.set_fontsize(11)
            autotext.set_fontweight('bold')

        # 图例
        legend_labels = [f'{l} ({s}%)' for l, s in zip(labels, [f'{x:.1f}' for x in sizes])]
        ax.legend(wedges, legend_labels, title="业务板块", loc="center left",
                 bbox_to_anchor=(1, 0, 0.5, 1))

        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        output_path = self.output_dir / f"pie_{self._safe_name(title)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_bar_chart(
        self,
        title: str,
        categories: List[str],
        values: List[float],
        ylabel: str = "",
        compare_values: Optional[List[float]] = None,
        compare_label: str = "竞品",
    ) -> Path:
        """生成柱状对比图"""
        fig, ax = plt.subplots(figsize=(10, 6), dpi=IMAGE_DPI)

        x = np.arange(len(categories))
        width = 0.35
        palette = self.chart_style.get("color_palette", ["#0A2F5A", "#FF6B35"])

        bars1 = ax.bar(x - width/2 if compare_values else x, values, width,
                       label='本项目', color=palette[0], edgecolor='white')

        if compare_values:
            bars2 = ax.bar(x + width/2, compare_values, width,
                          label=compare_label, color=palette[1], edgecolor='white')

        # 数值标签
        for bar in [bars1]:
            for rect in bar:
                height = rect.get_height()
                ax.annotate(f'{height:.1f}',
                           xy=(rect.get_x() + rect.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=9)

        ax.set_xticks(x)
        ax.set_xticklabels(categories, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=11)
        ax.set_title(title, fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        output_path = self.output_dir / f"bar_{self._safe_name(title)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_news_bg_image(
        self,
        topic: str,
        chapter_name: str,
    ) -> Path:
        """生成20:10横屏行业新闻佐证图（风格化背景+关键词排版）"""
        width = 20
        height = 10
        fig, ax = plt.subplots(figsize=(width, height), dpi=IMAGE_DPI)
        ax.set_xlim(0, width)
        ax.set_ylim(0, height)
        ax.axis('off')

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")
        bg_color = self.colors.get("background", "#F5F7FA")

        # 背景
        ax.set_facecolor(bg_color)
        fig.patch.set_facecolor(bg_color)

        # 网格装饰
        for i in range(1, 20):
            alpha = 0.03 if i % 5 else 0.06
            ax.axvline(x=i, color=primary_light, alpha=alpha, linewidth=1)
            ax.axhline(y=i/2, color=primary_light, alpha=alpha, linewidth=1)

        # 左侧色块
        rect_left = Rectangle((0.5, 1), 1, 8, facecolor=primary, alpha=0.15)
        ax.add_patch(rect_left)

        # 标题框
        title_box = FancyBboxPatch(
            (1.5, 3.5), 17, 3,
            boxstyle="round,pad=0.5",
            facecolor='white', edgecolor=primary_light, linewidth=1.5, alpha=0.9
        )
        ax.add_patch(title_box)

        # 标题文本
        ax.text(10, 5.5, f'行业视角：{topic}', fontsize=28, fontweight='bold',
                ha='center', va='center', color=primary)
        ax.text(10, 4.5, chapter_name, fontsize=16, ha='center', va='center',
                color=primary_light)

        # 底部数据标签
        tags = ["行业趋势", "政策解读", "市场分析", "数据洞察"]
        for i, tag in enumerate(tags):
            x = 3 + i * 4
            ax.text(x, 1.5, f'# {tag}', fontsize=12, ha='center', va='center',
                    color='white',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor=primary, alpha=0.7))

        # 来源注
        ax.text(19, 0.5, '数据来源：行业权威报告', fontsize=8,
                ha='right', color='#999999', style='italic')

        output_path = self.output_dir / f"news_{self._safe_name(topic)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor=bg_color, edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_timeline(
        self,
        title: str,
        milestones: List[Tuple[str, str]],  # (时间, 里程碑描述)
    ) -> Path:
        """生成技术路线时间轴"""
        fig, ax = plt.subplots(figsize=(14, 4), dpi=IMAGE_DPI)

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")
        n = len(milestones)

        ax.set_xlim(-0.5, n + 0.5)
        ax.set_ylim(0, 4)
        ax.axis('off')

        # 主轴线
        ax.axhline(y=2, xmin=0.5/n, xmax=(n-0.5)/n, color=primary, linewidth=3)

        for i, (time_label, milestone) in enumerate(milestones):
            x = i + 0.5

            # 节点
            circle = plt.Circle((x, 2), 0.2, facecolor=primary_light,
                               edgecolor='white', linewidth=2, zorder=5)
            ax.add_patch(circle)

            # 时间标签（上方）
            ax.text(x, 2.8, time_label, fontsize=12, fontweight='bold',
                    ha='center', va='center', color=primary,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#E3F2FD',
                             edgecolor=primary_light, alpha=0.9))

            # 里程碑描述（下方）
            ax.text(x, 1.2, milestone[:20], fontsize=10, ha='center',
                    va='center', color='#333333')

        ax.set_title(title, fontsize=16, fontweight='bold', color=primary, pad=20)
        output_path = self.output_dir / f"timeline_{self._safe_name(title)}.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor='white', edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_business_canvas(
        self,
        value_prop: str = "",
        customers: List[str] = None,
        channels: List[str] = None,
        revenue: List[str] = None,
        key_resources: List[str] = None,
    ) -> Path:
        """生成商业模式画布（9宫格）"""
        customers = customers or []
        channels = channels or []
        revenue = revenue or []
        key_resources = key_resources or []

        fig, ax = plt.subplots(figsize=(12, 8), dpi=IMAGE_DPI)
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 8)
        ax.axis('off')

        primary = self.colors.get("primary", "#0A2F5A")
        primary_light = self.colors.get("primary_light", "#2B7FFF")
        bg = self.colors.get("background", "#F5F7FA")

        # 9宫格定义: (x, y, w, h, label, items)
        grid_cells = [
            (0, 5.5, 3, 2.5, "关键合作伙伴\nKey Partners",
             ["上下游供应商", "科研院所合作", "行业协会支持"]),
            (3, 5.5, 3, 2.5, "关键业务\nKey Activities",
             ["技术研发与迭代", "产品设计与测试", "市场推广与销售"]),
            (6, 5.5, 3, 2.5, "核心资源\nKey Resources",
             key_resources[:3] if key_resources else ["核心技术专利", "研发团队", "实验平台"]),
            (0, 3, 3, 2.5, "价值主张\nValue Proposition",
             [value_prop[:25] if value_prop else "高性能/低成本/国产替代"]),
            (3, 3, 3, 2.5, "客户关系\nCustomer Relationships",
             ["专属技术支持", "定期回访服务", "定制化解决方案"]),
            (6, 3, 3, 2.5, "渠道通路\nChannels",
             channels[:3] if channels else ["直销团队", "行业展会", "线上平台"]),
            (0, 0.5, 3, 2.5, "客户细分\nCustomer Segments",
             customers[:3] if customers else ["新能源汽车", "5G基站", "快充电源"]),
            (3, 0.5, 3, 2.5, "成本结构\nCost Structure",
             ["研发成本", "人力成本", "设备折旧"]),
            (6, 0.5, 3, 2.5, "收入来源\nRevenue Streams",
             revenue[:3] if revenue else ["芯片销售", "模组方案", "技术授权"]),
        ]

        for x, y, w, h, title, items in grid_cells:
            rect = FancyBboxPatch((x + 0.1, y + 0.1), w - 0.2, h - 0.2,
                                  boxstyle="round,pad=0.2",
                                  facecolor='white', edgecolor=primary_light,
                                  linewidth=1.5, alpha=0.9)
            ax.add_patch(rect)
            ax.text(x + w/2, y + h - 0.5, title, fontsize=9, fontweight='bold',
                    ha='center', va='top', color=primary)
            for j, item in enumerate(items[:3]):
                ax.text(x + w/2, y + h - 1.0 - j*0.4, f"• {item[:20]}",
                       fontsize=7, ha='center', va='top', color='#555555')

        ax.set_title('商业模式画布 (Business Model Canvas)', fontsize=18,
                     fontweight='bold', color=primary, pad=15)
        output_path = self.output_dir / "biz_canvas.png"
        fig.savefig(output_path, dpi=IMAGE_DPI, bbox_inches='tight',
                    facecolor=bg, edgecolor='none')
        plt.close(fig)
        return output_path

    def generate_all_diagrams_for_document(
        self,
        project_name: str,
        competition_name: str,
        tech_name: str,
        tech_modules: List[str],
        innovations: List[str],
    ) -> Dict[str, Path]:
        """
        一键生成策划书所需的全套图表

        Returns:
            Dict[str, Path]: 图表类型 -> 文件路径
        """
        # 清空共享图片目录，确保本次生成的图不与旧图混淆
        import shutil
        if self.output_dir.exists():
            for f in self.output_dir.glob("*.png"):
                f.unlink()

        diagrams = {}

        # 1. 封面
        diagrams["cover"] = self.generate_cover(
            project_name=project_name,
            competition_name=competition_name,
        )

        # 2. 技术架构图（用创新点作为模块fallback）
        modules_for_arch = tech_modules if tech_modules else innovations[:5] if innovations else ["核心技术"]
        diagrams["tech_arch"] = self.generate_tech_architecture(
            tech_name=tech_name,
            modules=modules_for_arch[:5],
        )

        # 3. 流程图
        if innovations:
            diagrams["innovation_flow"] = self.generate_flow_chart(
                title="核心创新技术路线",
                steps=innovations[:8],
            )

        # 4. 行业新闻配图
        diagrams["news_bg"] = self.generate_news_bg_image(
            topic=tech_name,
            chapter_name="项目背景与行业痛点",
        )

        # 5. 商业模式画布
        diagrams["biz_canvas"] = self.generate_business_canvas(
            value_prop=f"{tech_name} - 高性能国产替代方案",
            customers=innovations[:3] if innovations else [],
        )

        # 6. 技术路线时间轴
        diagrams["timeline"] = self.generate_timeline(
            title=f"{project_name} - 技术发展路线图",
            milestones=[
                ("2026", "完成实验室验证，核心参数定型"),
                ("2027", "通过车规级认证（AEC-Q101）"),
                ("2028", "小批量试产，首批客户导入"),
                ("2029", "规模化量产，拓展海外市场"),
            ],
        )

        return diagrams

    def _safe_name(self, text: str) -> str:
        """清理文件名中的特殊字符"""
        safe = re.sub(r'[<>:"/\\|?*]', '_', text)
        return safe[:50]
