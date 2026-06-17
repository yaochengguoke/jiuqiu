"""
全自动竞赛策划智能体 - Streamlit Web 应用
"""

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from main import CompetitionAgent
from config import SUPPORTED_COMPETITIONS, SUPPORTED_THEMES

st.set_page_config(
    page_title="全自动竞赛策划智能体",
    page_icon="[Award]",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 主页标题 ──
st.title("[Award] 全自动竞赛策划智能体")
st.caption("双库驱动 · 国奖模板仿写 · 零虚构 · 全自动制图排版 · 一键输出成品策划书")

# ── 侧边栏：项目资料输入 ──
with st.sidebar:
    st.header("[INFO] 第一步：填写项目资料")

    competition = st.selectbox(
        "赛事组别",
        SUPPORTED_COMPETITIONS,
        help="选择您要参加的比赛，系统将自动匹配对应的国奖模板"
    )

    project_name = st.text_input(
        "项目名称 【必填】",
        placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化",
    )

    with st.expander("[Pin] 项目核心资料", expanded=True):
        project_brief = st.text_area(
            "项目简介 【必填】",
            height=130,
            placeholder="请描述：\n1. 项目是做什么的\n2. 核心技术是什么\n3. 取得了哪些成果\n4. 市场前景如何",
        )
        tech_principles = st.text_area(
            "技术原理与核心创新",
            height=100,
            placeholder="请详细描述技术原理，越详细生成质量越高（可选）",
        )
        innovations_str = st.text_input(
            "核心创新点",
            placeholder="用逗号分隔，例：AI预测调度,仿生微通道冷板,变频泵阀联动",
        )
        market_data = st.text_area(
            "市场调研数据",
            height=80,
            placeholder="市场规模、增长率、竞争格局、政策环境等（可选）",
        )
        cooperation = st.text_input(
            "项目合作 / 落地应用情况",
            placeholder="例：已与XX公司达成合作，产品在XX场景完成验证（可选）",
        )

    with st.expander("[Pin] 团队信息"):
        leader = st.text_input("项目负责人姓名")
        team_text = st.text_area(
            "团队成员",
            height=100,
            placeholder="每行一人，格式：姓名,专业,学历,分工,成就\n例：\n张三,计算机科学,博士研究生,技术负责人,发表SCI论文5篇\n李四,工商管理,硕士研究生,市场运营,获国家奖学金",
            help="每行写一个成员，用逗号分隔各项信息",
        )
        advisor = st.text_input("指导教师姓名")
        advisor_title = st.text_input("指导教师职称 / 学术资历")
        past_awards_str = st.text_area(
            "团队过往获奖",
            height=60,
            placeholder="每行一项，例：\n2025年全国大学生节能减排大赛一等奖\n2024年挑战杯省赛金奖",
        )

    with st.expander("[Pin] 文稿定制"):
        col1, col2 = st.columns(2)
        with col1:
            pages = st.number_input("目标页数", 30, 150, 80)
        with col2:
            color_theme = st.selectbox(
                "配色方案",
                list(SUPPORTED_THEMES.keys()),
                format_func=lambda x: SUPPORTED_THEMES[x],
            )

    with st.expander("[Pin] 佐证材料"):
        patents = st.text_area(
            "专利 / 软著",
            height=50,
            placeholder="例：发明专利5项（2项已授权），软著1项",
        )
        evidence_text = st.text_area(
            "其他佐证",
            height=60,
            placeholder="产品照片描述、检测报告、合作协议等（可选）",
        )

    st.markdown("---")
    generate = st.button(
        "[ROCKET] 开始生成策划书",
        type="primary",
        use_container_width=True,
    )

# ── 空状态提示 ──
if "generated" not in st.session_state:
    st.session_state.generated = False

if not st.session_state.generated:
    st.info(
        "[INFO] 请在左侧填写项目资料，然后点击「开始生成策划书」按钮。\n\n"
        "系统将自动完成：模板匹配 → 素材解析 → 国奖框架重写 → 自动制图 → 排版美化 → 成品输出",
    )

    with st.expander("这是什么？"):
        st.markdown("""
        ### 全自动竞赛策划智能体

        一个 AI 驱动的竞赛策划书自动生成系统，专为大学生顶级竞赛设计。

        **核心能力：**
        - [Pin] **双库驱动**：国奖模板库 + 客户专属知识库
        - [Pin] **1:1 仿写国奖结构**：章节、字数、话术完全对标
        - [Pin] **零虚构**：所有内容来自客户资料，绝不编造
        - [Pin] **全自动制图**：封面、架构图、流程图、配图一键生成
        - [Pin] **多格式输出**：Markdown + HTML + Word 三种格式

        **适用赛事：** 互联网+、挑战杯、节能减排、创青春、三创赛 等 8 个主流赛事
        """)

# ── 生成逻辑 ──
if generate:
    if not project_name or not project_brief:
        st.error("项目名称和项目简介为必填项，请填写后重试！")
    else:
        st.session_state.generated = True

        # 解析输入
        team_members = []
        if team_text:
            for line in team_text.strip().split('\n'):
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 2:
                    m = {"name": parts[0]}
                    if len(parts) > 1: m["major"] = parts[1]
                    if len(parts) > 2: m["degree"] = parts[2]
                    if len(parts) > 3: m["role"] = parts[3]
                    if len(parts) > 4: m["achievements"] = parts[4]
                    team_members.append(m)

        innovations = [i.strip() for i in innovations_str.split(',')] if innovations_str else []
        past_awards = [a.strip() for a in past_awards_str.split('\n') if a.strip()] if past_awards_str else []
        evidence_list = [e.strip() for e in evidence_text.split('\n') if e.strip()] if evidence_text else []

        raw_data = {
            "competition_info": {"competition_name": competition},
            "project_material": {
                "project_name": project_name, "project_brief": project_brief,
                "tech_principles": tech_principles, "innovations": innovations,
                "market_data": market_data, "cooperation_info": cooperation,
            },
            "team_info": {
                "project_leader": leader, "team_members": team_members,
                "advisor_name": advisor, "advisor_title": advisor_title,
                "past_awards": past_awards,
            },
            "doc_requirement": {"target_pages": pages, "color_theme": color_theme},
            "evidence": {
                "patent_certificates": [patents] if patents.strip() else [],
                "product_photos": evidence_list,
            },
        }

        with st.spinner("智能体运行中，正在为您生成国奖级策划书..."):
            progress = st.progress(0, text="正在初始化...")
            status = st.empty()

            agent = CompetitionAgent()

            # 阶段1
            progress.progress(10, text="[1/7] 校验资料完整性...")
            submission, completeness = agent.input_processor.process_submission(raw_data)

            # 阶段2
            progress.progress(20, text="[2/7] 匹配国奖模板...")
            agent.current_template = agent.template_matcher.match_template(competition)

            # 阶段3
            progress.progress(35, text="[3/7] 解析项目素材，构建知识库...")
            customer_kb = agent.input_processor.build_customer_knowledge_base()
            agent.current_data_pool = agent.material_parser.parse_and_build_pool(
                customer_kb, agent.current_template.chapters)

            # 阶段4+5
            progress.progress(55, text="[4/7] 按国奖框架逐章撰写正文...")
            agent.current_document = agent.content_generator.generate_all_chapters(
                agent.current_template, agent.current_data_pool)

            # 阶段6
            progress.progress(70, text="[5/7] 自动生成图表（封面/架构/流程图/配图）...")
            user_visual = agent._load_visual_style(color_theme)
            from modules.diagram_generator import DiagramGenerator
            dg = DiagramGenerator(visual_style=user_visual)
            tech_name = agent.current_data_pool.tech_pool.get("technology_name", "")
            diagrams = dg.generate_all_diagrams_for_document(
                project_name=project_name, competition_name=competition,
                tech_name=tech_name, tech_modules=[], innovations=innovations)

            # 阶段7
            progress.progress(90, text="[6/7] 排版美化，导出多格式文件...")
            from modules.layout_engine import LayoutEngine
            from modules.output_exporter import OutputExporter
            layout = LayoutEngine(user_visual)
            exporter = OutputExporter()
            agent.current_export = exporter.export_all(
                document=agent.current_document, layout_engine=layout)

            progress.progress(100, text="[7/7] 生成完成！")

        # ── 结果展示 ──
        st.success(
            f"策划书生成完毕！"
            f"共 {agent.current_document.total_word_count} 字 · "
            f"{len(agent.current_template.chapters)} 章 · "
            f"{len(diagrams)} 张图表"
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总字数", f"{agent.current_document.total_word_count} 字")
        col2.metric("章节数", f"{len(agent.current_template.chapters)} 章")
        col3.metric("图表数", f"{len(diagrams)} 张")
        col4.metric("数据来源", f"{agent.current_data_pool.numeric_entities and len(agent.current_data_pool.numeric_entities) or 0} 组")

        tab1, tab2, tab3 = st.tabs(["策划书正文", "下载文件", "缺失清单"])

        with tab1:
            st.markdown(agent.current_document.get_full_text())

        with tab2:
            st.markdown("### 下载策划书文件")
            export_dir = agent.current_export.output_dir
            files = sorted(export_dir.glob("*"))
            cols = st.columns(3)
            for i, f in enumerate(files):
                if f.is_file():
                    with cols[i % 3]:
                        label = f.name
                        if f.suffix == ".md":
                            label = f"[MD] {f.name}"
                        elif f.suffix == ".html":
                            label = f"[HTML] {f.name}"
                        elif f.suffix == ".docx":
                            label = f"[DOCX] {f.name}"
                        with open(f, "rb") as fh:
                            st.download_button(label, fh.read(), f.name, use_container_width=True)

        with tab3:
            st.markdown(agent.current_document.get_missing_report())

st.sidebar.markdown("---")
st.sidebar.caption(
    "双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版\n\n"
    "Powered by Claude Agent SDK"
)
