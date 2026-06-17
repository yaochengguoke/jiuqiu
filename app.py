"""
全自动竞赛策划智能体 - Streamlit Web 应用
本地运行: streamlit run app.py
云端部署: 推送到 GitHub → connect Streamlit Cloud
"""

import sys, json, io, zipfile, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from main import CompetitionAgent
from config import SUPPORTED_COMPETITIONS, SUPPORTED_THEMES

st.set_page_config(page_title="竞赛策划智能体", page_icon="[Award]", layout="wide")
st.title("[Award] 全自动竞赛策划智能体")
st.caption("提交项目资料 → 自动生成国奖级竞赛策划书")

# ── Sidebar: 资料输入 ──
with st.sidebar:
    st.header("[INFO] 项目资料")

    competition = st.selectbox("赛事组别", SUPPORTED_COMPETITIONS)
    project_name = st.text_input("项目名称", placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化")

    with st.expander("项目核心资料", expanded=True):
        project_brief = st.text_area("项目简介【必填】", height=120,
            placeholder="请描述项目的核心内容、技术亮点、市场前景...")
        tech_principles = st.text_area("技术原理与创新（可选）", height=100)
        innovations_str = st.text_input("核心创新点（逗号分隔）",
            placeholder="创新点1,创新点2,创新点3")
        market_data = st.text_area("市场调研数据（可选）", height=80)
        cooperation = st.text_input("合作/落地情况（可选）")

    with st.expander("团队信息"):
        leader = st.text_input("项目负责人")
        advisor = st.text_input("指导教师姓名")
        advisor_title = st.text_input("指导教师职称/资历")
        team_text = st.text_area("团队成员（每行：姓名,专业,学历,分工,成就）", height=100,
            placeholder="张三,计算机,博士研究生,技术负责人,SCI论文5篇")

    with st.expander("文稿定制"):
        pages = st.number_input("目标页数", 30, 150, 80)
        color_theme = st.selectbox("配色方案",
            list(SUPPORTED_THEMES.keys()),
            format_func=lambda x: SUPPORTED_THEMES[x])

    with st.expander("佐证材料"):
        patents = st.text_input("专利情况")
        evidence_text = st.text_area("其他佐证", height=60)

    generate = st.button("[ROCKET] 开始生成策划书", type="primary", use_container_width=True)

# ── Main: 生成逻辑 ──
if generate:
    if not project_name or not project_brief:
        st.error("项目名称和项目简介为必填项！")
    else:
        # 构建数据
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
        past_awards = [a.strip() for a in evidence_text.split('\n')] if evidence_text else []

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
            "evidence": {"patent_certificates": [patents] if patents else []},
        }

        with st.spinner("智能体运行中，约需30秒..."):
            progress = st.progress(0)
            status = st.empty()

            agent = CompetitionAgent()
            submission, completeness = agent.input_processor.process_submission(raw_data)
            status.text(f"资料完整度: {completeness.score:.0%}")
            progress.progress(15)

            agent.current_template = agent.template_matcher.match_template(competition)
            status.text(f"模板: {agent.current_template.competition_name}")
            progress.progress(30)

            customer_kb = agent.input_processor.build_customer_knowledge_base()
            agent.current_data_pool = agent.material_parser.parse_and_build_pool(
                customer_kb, agent.current_template.chapters)
            status.text(f"数据实体: {len(agent.current_data_pool.numeric_entities)}组")
            progress.progress(45)

            agent.current_document = agent.content_generator.generate_all_chapters(
                agent.current_template, agent.current_data_pool)
            status.text(f"正文: {agent.current_document.total_word_count}字")
            progress.progress(65)

            user_visual = agent._load_visual_style(color_theme)
            from modules.diagram_generator import DiagramGenerator
            dg = DiagramGenerator(visual_style=user_visual)
            tech_name = agent.current_data_pool.tech_pool.get("technology_name", "")
            diagrams = dg.generate_all_diagrams_for_document(
                project_name=project_name, competition_name=competition,
                tech_name=tech_name, tech_modules=[], innovations=innovations)
            status.text(f"图表: {len(diagrams)}张")
            progress.progress(80)

            from modules.layout_engine import LayoutEngine
            from modules.output_exporter import OutputExporter
            layout = LayoutEngine(user_visual)
            exporter = OutputExporter()
            agent.current_export = exporter.export_all(
                document=agent.current_document, layout_engine=layout)

            status.text("[OK] 生成完成！")
            progress.progress(100)

        # ── 结果展示 ──
        st.success(f"策划书生成成功！{agent.current_document.total_word_count}字 / {len(diagrams)}张图")

        c1, c2, c3 = st.columns(3)
        c1.metric("总字数", f"{agent.current_document.total_word_count}字")
        c2.metric("图表数", f"{len(diagrams)}张")
        c3.metric("缺失项", f"{len(agent.current_document.missing_sections)}处")

        tab1, tab2 = st.tabs(["策划书正文", "下载文件"])

        with tab1:
            st.markdown(agent.current_document.get_full_text())

        with tab2:
            export_dir = agent.current_export.output_dir
            files = sorted(export_dir.glob("*"))
            for f in files:
                if f.is_file():
                    with open(f, "rb") as fh:
                        st.download_button(f"[Download] {f.name}", fh.read(), f.name)

st.sidebar.markdown("---")
st.sidebar.caption("双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版")
