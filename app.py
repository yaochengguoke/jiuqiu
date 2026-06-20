"""
全自动竞赛策划智能体 - Streamlit Web 应用
"""

import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from main import CompetitionAgent
from config import SUPPORTED_COMPETITIONS, SUPPORTED_THEMES

st.set_page_config(page_title="AI竞赛策划智能体", page_icon="🏆", layout="wide", initial_sidebar_state="expanded")

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
    m = {"final_plan.md":"策划书正文(Markdown)","final_plan.html":"网页预览版","final_plan.docx":"Word可编辑版","final_plan.pdf":"PDF提交版",
         "quality_report.md":"质量检查报告","missing_checklist.md":"待补充清单","plagiarism_report.md":"查重预检报告","executive_summary.md":"执行摘要+路演稿",
         "client_supplement_guide.md":"补充资料引导","financial_questionnaire.md":"财务补充问卷","defense_prep_report.md":"答辩预演手册","defense.pptx":"答辩PPT","DATA_PRIVACY.txt":"数据隐私承诺","competitor_analysis.md":"竞品对标分析"}
    return m.get(fn, fn)

# ── Session state init ──
if "generated" not in st.session_state:
    st.session_state.generated = False
# API密钥持久化
if st.session_state.get("_api_key"):
    import os as _os
    k = st.session_state._api_key
    _os.environ["DEEPSEEK_API_KEY" if not k.startswith("sk-ant") else "ANTHROPIC_API_KEY"] = k

def _show_downloads(out_dir):
    """分类展示下载文件"""
    icons = {"项目核心文稿": "📄", "调研辅助材料": "📊", "合规/财务/检测": "🛡️", "配置文件": "⚙️"}
    subtitles = {"项目核心文稿": "用于申报提交与答辩展示", "调研辅助材料": "竞品对标与资料补全参考", "合规/财务/检测": "查重、隐私、财务合规文件", "配置文件": "系统元数据与变更记录"}
    categories = {
        "项目核心文稿": ["final_plan.docx", "final_plan.html", "final_plan.md", "final_plan.pdf", "executive_summary.md", "defense_prep_report.md", "defense.pptx"],
        "调研辅助材料": ["competitor_analysis.md", "client_supplement_guide.md", "missing_checklist.md"],
        "合规/财务/检测": ["DATA_PRIVACY.txt", "financial_questionnaire.md", "plagiarism_report.md", "quality_report.md"],
        "配置文件": ["metadata.json", "change_log.md"],
    }
    all_handled = set()
    for files in categories.values():
        all_handled.update(files)
    
    for cat_name, cat_files in categories.items():
        existing = [(f, out_dir / f) for f in cat_files if (out_dir / f).exists()]
        if existing:
            icon = icons.get(cat_name, "")
            sub = subtitles.get(cat_name, "")
            st.markdown(f'<div class="download-cat">{icon} {cat_name}<span>{sub}</span></div>', unsafe_allow_html=True)
            cols = st.columns(min(len(existing), 3))
            for i, (fname, fpath) in enumerate(existing):
                with cols[i % 3]:
                    with open(fpath, "rb") as fh:
                        st.download_button(_label(fname), fh.read(), fname, use_container_width=True)
    
    remaining = [f for f in sorted(out_dir.glob("*")) if f.is_file() and f.name not in all_handled]
    if remaining:
        with st.expander("其他文件"):
            cols = st.columns(3)
            for i, f in enumerate(remaining):
                with cols[i % 3]:
                    with open(f, "rb") as fh:
                        st.download_button(_label(f.name), fh.read(), f.name, use_container_width=True)



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
    with st.expander("📂 导入资料 · 🤖 AI 生成配置", expanded=False):
        st.caption("上传 JSON / Word / TXT 文件，自动填充下方表单")
        uploaded = st.file_uploader("选择文件", type=["json", "txt", "docx"], label_visibility="collapsed",
                                     key="import_file")
        if uploaded and not st.session_state.get("_import_done"):
            try:
                st.session_state._import_done = True
                if uploaded.name.endswith('.json'):
                    data = json.loads(uploaded.read())
                    if "project_material" in data:
                        st.session_state.project_name = data["project_material"].get("project_name", "")
                        st.session_state.project_brief = data["project_material"].get("project_brief", "")
                        st.session_state.tech_principles = data["project_material"].get("tech_principles", "")
                        st.session_state.market_data = data["project_material"].get("market_data", "")
                        st.session_state.leader = data["team_info"].get("project_leader", "")
                        st.session_state.advisor = data["team_info"].get("advisor_name", "")
                        st.success("配置加载成功，表单已自动填充")
                        st.rerun()
                elif uploaded.name.endswith('.docx'):
                    from docx import Document
                    text = '\n'.join([p.text for p in Document(uploaded).paragraphs])
                    st.session_state.project_brief = text[:2000]
                    st.success("Word 解析完成")
                    st.rerun()
                else:
                    st.session_state.project_brief = uploaded.read().decode('utf-8')[:2000]
                    st.success("文本已加载")
                    st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")
                st.session_state._import_done = False
        st.markdown('<p style="font-size:0.7rem;color:#9CA3AF;margin:0.3rem 0;">🤖 接入 AI 模型（可选，免费试用）</p>', unsafe_allow_html=True)
        api_key = st.text_input("API 密钥", type="password", placeholder="DeepSeek 或 Anthropic 密钥", label_visibility="collapsed")
        st.caption("去 platform.deepseek.com 免费注册获取，输入后直接生成勿刷新")
        if api_key:
            st.session_state._api_key = api_key
            import os, urllib.request, json as _json
            if api_key.startswith("sk-ant"):
                os.environ["ANTHROPIC_API_KEY"] = api_key
                st.success("Anthropic 密钥已设置")
            else:
                os.environ["DEEPSEEK_API_KEY"] = api_key
                # 快速验证密钥
                try:
                    req = urllib.request.Request("https://api.deepseek.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"})
                    urllib.request.urlopen(req, timeout=10)
                    st.success("DeepSeek 密钥验证通过，AI 已就绪")
                except Exception as e:
                    st.error(f"密钥无效: {str(e)[:60]}")
                    st.session_state._api_key = ""

    st.markdown('<hr style="margin:0.6rem 0;border-color:#E5E7EB;">', unsafe_allow_html=True)
    project_name = st.text_input("项目名称 *", value=st.session_state.get("project_name",""), placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化")
    st.markdown('<p style="font-size:0.7rem;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;margin:0 0 0.3rem;">✏️ 手动填写</p>', unsafe_allow_html=True)
    with st.expander("项目核心资料", expanded=True):
        project_brief = st.text_area("项目简介 *", value=st.session_state.get("project_brief",""), height=120, placeholder="请描述：项目做什么、核心技术、成果、市场前景")
        tech_principles = st.text_area("技术原理与核心创新", value=st.session_state.get("tech_principles",""), height=90, placeholder="越详细生成质量越高")
        innovations_str = st.text_input("核心创新点", placeholder="逗号分隔，例：AI预测调度,微通道冷板,泵阀联动")
        market_data = st.text_area("市场调研数据", value=st.session_state.get("market_data",""), height=70, placeholder="市场规模、增长率、竞争格局等")
        cooperation = st.text_input("项目合作 / 落地应用", placeholder="已与XX达成合作，在XX完成验证")

    with st.expander("团队信息"):
        leader = st.text_input("项目负责人 *", value=st.session_state.get("leader",""))
        team_text = st.text_area("团队成员", height=90, placeholder="每行一人：姓名,专业,学历,分工,成就")
        advisor = st.text_input("指导教师 *", value=st.session_state.get("advisor",""))
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

    fields_check = [project_name, project_brief, leader, advisor, tech_principles, market_data]
    filled = sum(1 for v in fields_check if v and (isinstance(v, str) and len(v.strip()) > 0))
    st.markdown(f'<p style="font-size:0.72rem;color:#9CA3AF;text-align:center;margin:0.3rem 0;">已填写 {filled}/{len(fields_check)} 项核心字段</p>', unsafe_allow_html=True)
    generate = st.button("生成策划书", type="primary", use_container_width=True)
    st.caption("生成后请立即下载，勿刷新或点击其他位置")

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
        st.markdown("""### 竞赛策划智能体
AI 驱动的竞赛策划书自动生成系统，支持 8 个主流赛事。

**核心能力**
- 双库驱动 + 1:1 国奖仿写 + 绝对零虚构
- 自动生成 6 种图表（封面/架构/流程/配图/画布/路线）
- 输出 5 种格式（Word/HTML/PDF/Markdown/PPT）
- 支持 DeepSeek & Anthropic 双 AI 引擎

**智能增强（P0）**
- 查重预检：模板句 + n-gram 重复 + 风险评分
- 答辩预演：评委提问清单 + 答辩技巧 + 一键生成答辩 PPT
- 执行摘要：300 字摘要 + 1 分钟路演稿
- 竞品对标分析：自动提取竞品名 + 参数对比表
- 资料完整度分级引导补全

**交互体验**
- 📂 文件导入：JSON/Word/TXT 自动填充表单
- 🤖 AI 增强：接入 API 密钥后自动启用 AI 生成
- ⚡ 后台加速：PDF/PPT 后台线程生成，正文先出
- 📥 分类下载：核心文稿 / 调研材料 / 合规检测
- 💾 结果持久化：下载后内容不消失""")

# ── 演示结果 ──
if st.session_state.get("demo_result"):
    a = st.session_state.demo_result
    out = a.current_export.output_dir
    # ensure reports
    from modules.plagiarism_checker import PlagiarismChecker
    from modules.defense_prep import DefensePrep
    from utils.helpers import ensure_dir, write_text_file
    ft = a.current_document.get_full_text()
    ensure_dir(out)
    pc = PlagiarismChecker()
    write_text_file(out / "plagiarism_report.md", PlagiarismChecker().format_markdown(pc.check(ft)))
    dp = DefensePrep()
    write_text_file(out / "executive_summary.md", dp.generate_summary(ft, a.current_document.project_name))
    write_text_file(out / "defense_prep_report.md", dp.print_report(dp.generate_defense_prep(ft, a.current_document.project_name)))
    # 生成PPT
    from modules.ppt_generator import PPTGenerator
    pptg = PPTGenerator()
    ppt_path = out / "defense.pptx"
    pptg.generate_ppt(ft, a.current_document.project_name, ppt_path)
    # 竞品对标
    ca = pptg.format_competitor_table(pptg.analyze_competitors(ft))
    if ca:
        write_text_file(out / "competitor_analysis.md", ca)
    # PDF via fpdf2
    try:
        from modules.output_exporter import OutputExporter
        OutputExporter()._export_pdf(ft, out)
    except: pass

    st.success(f"已生成 · {a.current_document.total_word_count}字 · {len(a.current_template.chapters)}章")
    t1, t2 = st.tabs(["策划书正文", "下载文件"])
    with t1: st.markdown(ft)
    with t2:
        _show_downloads(out)

# ── 生成逻辑 ──
if generate:
    # 输入校验
    errors = []
    if not project_name or len(project_name.strip()) < 4:
        errors.append("项目名称至少4个字符")
    if not project_brief or len(project_brief.strip()) < 20:
        errors.append("项目简介至少20个字符，请描述项目核心内容")
    if not competition:
        errors.append("请选择赛事组别")
    if errors:
        for e in errors:
            st.error(e)
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

            status.update(label="生成图表+排版导出...", state="running")
            user_visual = agent._load_visual_style(color_theme)
            from modules.diagram_generator import DiagramGenerator
            dg = DiagramGenerator(visual_style=user_visual)
            diagrams = dg.generate_all_diagrams_for_document(project_name=project_name, competition_name=competition, tech_name=agent.current_data_pool.tech_pool.get("technology_name",""), tech_modules=[], innovations=innovations)
            from modules.layout_engine import LayoutEngine
            from modules.output_exporter import OutputExporter
            agent.current_export = OutputExporter().export_all(document=agent.current_document, layout_engine=LayoutEngine(user_visual))

            # 耗时任务放后台线程
            import threading
            full_text = agent.current_document.get_full_text()
            out = agent.current_export.output_dir
            def bg_tasks():
                from utils.helpers import ensure_dir, write_text_file
                ensure_dir(out)
                from modules.plagiarism_checker import PlagiarismChecker
                pc = PlagiarismChecker()
                write_text_file(out / "plagiarism_report.md", pc.format_markdown(pc.check(full_text)))
                from modules.defense_prep import DefensePrep
                dp = DefensePrep()
                write_text_file(out / "executive_summary.md", dp.generate_summary(full_text, agent.current_document.project_name))
                write_text_file(out / "defense_prep_report.md", dp.print_report(dp.generate_defense_prep(full_text, agent.current_document.project_name)))
                from modules.ppt_generator import PPTGenerator
                pptg = PPTGenerator()
                pptg.generate_ppt(full_text, agent.current_document.project_name, out / "defense.pptx")
                ca = pptg.format_competitor_table(pptg.analyze_competitors(full_text))
                if ca: write_text_file(out / "competitor_analysis.md", ca)
            th = threading.Thread(target=bg_tasks); th.start()

            status.update(label="生成完毕", state="complete")

        st.session_state._result = agent
        st.rerun()

# 持久化显示（生成后不会消失）
if st.session_state.get("_result"):
    a = st.session_state._result
    st.success(f"已生成 · {a.current_document.total_word_count} 字 · {len(a.current_template.chapters)} 章")
    _show_downloads(a.current_export.output_dir)
    with st.expander("查看正文"): st.markdown(a.current_document.get_full_text())

# ── 底部 ──
st.markdown("""<div style="text-align:center;padding:3rem 0 2rem;color:#86868b;font-size:0.85rem;">
    <p style="margin:0;color:#6B7280;">双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版</p>
    <p style="margin:0.3rem 0 0;font-size:0.75rem;color:#9CA3AF;">Powered by Claude</p>
</div>""", unsafe_allow_html=True)
