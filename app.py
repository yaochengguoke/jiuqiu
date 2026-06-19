"""
全自动竞赛策划智能体 - Streamlit Web 应用
"""

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from main import CompetitionAgent
from config import SUPPORTED_COMPETITIONS, SUPPORTED_THEMES

st.set_page_config(page_title="竞赛策划智能体", page_icon="🏆", layout="wide", initial_sidebar_state="expanded")

# ── 极简白风格 ──
st.markdown("""<style>
    .stApp { background: #FFFFFF; }
    .main .block-container { padding: 2rem 3rem; max-width: 900px; }
    [data-testid="stSidebar"] { background: #FAFBFC; border-right: 1px solid #E5E7EB; }
    [data-testid="stSidebar"] label { color: #1F2937 !important; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%); border-radius: 12px; border: 1px solid #E5E7EB; border-top: 3px solid #111827; box-shadow: 0 1px 3px rgba(0,0,0,0.04); margin-bottom: 0.5rem; }
    .stTextInput input, .stTextArea textarea { border-radius: 8px !important; border: 1px solid #E5E7EB !important; background: #FAFBFC !important; color: #1F2937 !important; }
    .stTextInput input:focus, .stTextArea textarea:focus { border-color: #111827 !important; box-shadow: 0 0 0 4px rgba(17,24,39,0.08) !important; }
    .stButton > button { background: #111827 !important; color: #fff !important; border: none !important; border-radius: 8px !important; padding: 0.6rem 1.6rem !important; font-size: 0.9rem !important; font-weight: 500 !important; transition: all 0.3s cubic-bezier(0.4,0,0.2,1) !important; }
    .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(17,24,39,0.25) !important; }
    .stProgress > div { background: #E5E7EB !important; border-radius: 20px !important; height: 6px !important; }
    .stProgress > div > div > div { background: linear-gradient(90deg, #111827, #3B82F6) !important; border-radius: 20px !important; }
    [data-testid="stAlert"] { border-radius: 12px !important; border: 1px solid #E5E7EB !important; background: #FAFBFC !important; }
    .stDownloadButton > button { border-radius: 8px !important; font-size: 0.85rem !important; }
    .required label::after { content: " *"; color: #e53e3e; font-weight: 700; }
    @media (max-width: 768px) { .main .block-container { padding: 1rem; } }
</style>""", unsafe_allow_html=True)

# ── 工具 ──
def _label(fn):
    m = {"final_plan.md":"策划书正文(Markdown)","final_plan.html":"网页预览版","final_plan.docx":"Word可编辑版",
         "quality_report.md":"质量检查报告","missing_checklist.md":"待补充清单","client_supplement_guide.md":"补充资料引导",
         "financial_questionnaire.md":"财务补充问卷","defense_prep_report.md":"答辩预演手册","DATA_PRIVACY.txt":"数据隐私承诺"}
    return m.get(fn, fn)

# ── Session state init ──
if "generated" not in st.session_state:
    st.session_state.generated = False

# ── Hero ──
st.markdown("""<div style="text-align:center;padding:2rem 1rem 1rem;">
    <h1 style="font-size:3rem;font-weight:700;color:#111827;letter-spacing:-0.8px;margin:0;">⚡ 竞赛策划智能体</h1>
    <p style="font-size:1.1rem;color:#6B7280;margin-top:0.5rem;">输入项目资料，自动生成国奖级竞赛策划书</p>
</div>""", unsafe_allow_html=True)

# ── 侧边栏 ──
with st.sidebar:
    st.markdown('<p style="font-size:0.75rem;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:1px;">项目资料</p>', unsafe_allow_html=True)

    competition = st.selectbox("赛事组别", SUPPORTED_COMPETITIONS)

    # 必填项加 *
    project_name = st.text_input("项目名称 *", placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化")

    with st.expander("项目核心资料", expanded=True):
        project_brief = st.text_area("项目简介 *", height=120, placeholder="请描述：项目做什么、核心技术、成果、市场前景")
        tech_principles = st.text_area("技术原理与核心创新", height=90, placeholder="越详细生成质量越高")
        innovations_str = st.text_input("核心创新点", placeholder="逗号分隔，例：AI预测调度,微通道冷板,泵阀联动")
        market_data = st.text_area("市场调研数据", height=70, placeholder="市场规模、增长率、竞争格局等")
        cooperation = st.text_input("项目合作 / 落地应用", placeholder="已与XX达成合作，在XX完成验证")

    with st.expander("团队信息"):
        leader = st.text_input("项目负责人 *")
        team_text = st.text_area("团队成员", height=90, placeholder="每行一人：姓名,专业,学历,分工,成就")
        advisor = st.text_input("指导教师 *")
        advisor_title = st.text_input("指导教师职称 / 资历")
        past_awards_str = st.text_input("团队过往获奖", placeholder="逗号分隔")

    with st.expander("文稿定制", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            pages = st.number_input("目标页数", 30, 150, 80)
        with c2:
            color_theme = st.selectbox("配色方案", list(SUPPORTED_THEMES.keys()), format_func=lambda x: SUPPORTED_THEMES[x])

    with st.expander("佐证材料"):
        patents = st.text_input("专利 / 软著", placeholder="例：发明专利5项（2项已授权）")
        evidence_text = st.text_area("其他佐证", height=50, placeholder="产品照片描述、检测报告等")

    generate = st.button("生成策划书", type="primary", use_container_width=True)

# ── 空状态提示 ──
if not st.session_state.generated:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info("在左侧填写项目资料，点击「生成策划书」，或点「查看示例」体验演示。")
    with col_b:
        if st.button("查看示例", use_container_width=True, type="secondary"):
            st.session_state.run_demo = True

    if st.session_state.get("run_demo"):
        st.success("正在生成演示案例...")
        agent = CompetitionAgent()
        agent.run_demo()
        st.session_state.demo_result = agent
        st.session_state.generated = True
        st.session_state.run_demo = False
        st.rerun()

    with st.expander("这是什么？"):
        st.markdown("""### 全自动竞赛策划智能体
AI 驱动的竞赛策划书自动生成系统。
- **双库驱动**：国奖模板库 + 客户专属知识库
- **1:1 仿写国奖结构**：章节、字数、话术完全对标
- **零虚构**：所有内容来自客户资料，绝不编造
- **全自动制图**：封面、架构图、流程图、配图一键生成
- **多格式输出**：Markdown + HTML + Word 三种格式""")

# ── 演示结果 ──
if st.session_state.get("demo_result"):
    a = st.session_state.demo_result
    st.success(f"已生成 · {a.current_document.total_word_count}字 · {len(a.current_template.chapters)}章")
    t1, t2 = st.tabs(["策划书正文", "下载文件"])
    with t1: st.markdown(a.current_document.get_full_text())
    with t2:
        st.markdown("### 推荐下载")
        for key in ["final_plan.docx", "final_plan.html"]:
            fp = a.current_export.output_dir / key
            if fp.exists():
                with open(fp, "rb") as fh: st.download_button(_label(key), fh.read(), key)
        with st.expander("其他文件"):
            for f in sorted(a.current_export.output_dir.glob("*")):
                if f.is_file() and f.name not in ["final_plan.docx", "final_plan.html"]:
                    with open(f, "rb") as fh: st.download_button(_label(f.name), fh.read(), f.name)

# ── 生成逻辑 ──
if generate:
    if not project_name or not project_brief:
        st.error("请填写项目名称和项目简介")
    else:
        st.session_state.generated = True
        team_members = []
        if team_text:
            for line in team_text.strip().split('\n'):
                p = [x.strip() for x in line.split(',')]
                if len(p) >= 2: team_members.append({"name":p[0],"major":p[1] if len(p)>1 else "","degree":p[2] if len(p)>2 else "","role":p[3] if len(p)>3 else "","achievements":p[4] if len(p)>4 else ""})
        innovations = [i.strip() for i in innovations_str.split(',')] if innovations_str else []
        past_awards = [a.strip() for a in past_awards_str.split(',') if a.strip()] if past_awards_str else []
        evidence_list = [e.strip() for e in evidence_text.split('\n') if e.strip()] if evidence_text else []

        raw_data = {
            "competition_info": {"competition_name": competition},
            "project_material": {"project_name":project_name,"project_brief":project_brief,"tech_principles":tech_principles,"innovations":innovations,"market_data":market_data,"cooperation_info":cooperation},
            "team_info": {"project_leader":leader,"team_members":team_members,"advisor_name":advisor,"advisor_title":advisor_title,"past_awards":past_awards},
            "doc_requirement": {"target_pages":pages,"color_theme":color_theme},
            "evidence": {"patent_certificates":[patents] if patents.strip() else [],"product_photos":evidence_list},
        }

        with st.status("正在生成策划书...", expanded=True) as status:
            agent = CompetitionAgent()

            status.update(label="校验资料 + 匹配模板...", state="running")
            submission, _ = agent.input_processor.process_submission(raw_data)
            agent.current_template = agent.template_matcher.match_template(competition)
            kb = agent.input_processor.build_customer_knowledge_base()
            agent.current_data_pool = agent.material_parser.parse_and_build_pool(kb, agent.current_template.chapters)

            total_chapters = len(agent.current_template.chapters)
            def chapter_cb(cur, total, name):
                status.update(label=f"撰写正文 ({cur}/{total})：{name}", state="running")

            status.update(label=f"撰写正文 (0/{total_chapters})", state="running")
            agent.current_document = agent.content_generator.generate_all_chapters(
                agent.current_template, agent.current_data_pool, progress_callback=chapter_cb)

            status.update(label="生成图表...", state="running")
            user_visual = agent._load_visual_style(color_theme)
            from modules.diagram_generator import DiagramGenerator
            dg = DiagramGenerator(visual_style=user_visual)
            diagrams = dg.generate_all_diagrams_for_document(project_name=project_name, competition_name=competition, tech_name=agent.current_data_pool.tech_pool.get("technology_name",""), tech_modules=[], innovations=innovations)

            status.update(label="排版导出...", state="running")
            from modules.layout_engine import LayoutEngine
            from modules.output_exporter import OutputExporter
            agent.current_export = OutputExporter().export_all(document=agent.current_document, layout_engine=LayoutEngine(user_visual))

            status.update(label="生成完毕", state="complete")
        st.success(f"已生成 · {agent.current_document.total_word_count} 字 · {len(agent.current_template.chapters)} 章 · {len(diagrams)} 张图表")

        # 改动4：下载区分优先级
        exp = agent.current_export.output_dir
        st.markdown("### 推荐下载")
        c1, c2 = st.columns(2)
        for i, (col, key) in enumerate(zip([c1, c2], ["final_plan.docx", "final_plan.html"])):
            with col:
                fp = exp / key
                if fp.exists():
                    with open(fp, "rb") as fh: st.download_button(_label(key), fh.read(), key, use_container_width=True)
        with st.expander("其他文件"):
            for f in sorted(exp.glob("*")):
                if f.is_file() and f.name not in ["final_plan.docx", "final_plan.html"]:
                    with open(f, "rb") as fh: st.download_button(_label(f.name), fh.read(), f.name)

        with st.expander("查看正文"): st.markdown(agent.current_document.get_full_text())

# ── 底部 ──
st.markdown("""<div style="text-align:center;padding:3rem 0 2rem;color:#86868b;font-size:0.85rem;">
    <p style="margin:0;color:#6B7280;">双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版</p>
    <p style="margin:0.3rem 0 0;font-size:0.75rem;color:#9CA3AF;">Powered by Claude</p>
</div>""", unsafe_allow_html=True)
