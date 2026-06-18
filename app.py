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
    page_title="竞赛策划智能体",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Apple 官网风格 ──
st.markdown("""
<style>
    :root { --blue: #0071e3; --gray: #f5f5f7; --text: #1d1d1f; --secondary: #86868b; --border: #d2d2d7; }
    .stApp { background: var(--gray); }
    /* 主区域卡片 */
    .main .block-container { padding: 2rem 3rem; max-width: 900px; }
    /* 侧边栏 */
    [data-testid="stSidebar"] { background: rgba(245,245,247,0.8); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); border-right: 0.5px solid rgba(0,0,0,0.08); }
    [data-testid="stSidebar"] label { color: var(--text) !important; }
    [data-testid="stSidebar"] [data-testid="stExpander"] { background: #fff; border-radius: 18px; border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 2px 8px rgba(0,0,0,0.04); margin-bottom: 0.5rem; }
    [data-testid="stSidebar"] hr { border-color: rgba(0,0,0,0.06); margin: 1rem 0; }
    /* 输入框 - 仅颜色不碰尺寸 */
    .stTextInput input, .stTextArea textarea { border-radius: 10px !important; border-color: #d2d2d7 !important; background: #fff !important; }
    .stTextInput input:focus, .stTextArea textarea:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 3px rgba(0,113,227,0.12) !important; }
    /* 按钮 - pill */
    .stButton > button {
        background: var(--blue) !important; color: #fff !important; border: none !important;
        border-radius: 980px !important; padding: 0.6rem 1.6rem !important;
        font-size: 0.9rem !important; font-weight: 500 !important;
        letter-spacing: -0.2px; transition: all 0.15s ease !important;
    }
    .stButton > button:hover { background: #0077ED !important; filter: brightness(1.05); box-shadow: 0 4px 16px rgba(0,113,227,0.2); }
    /* 进度条 */
    .stProgress > div { background: #e8e8ed !important; border-radius: 980px; height: 6px !important; }
    .stProgress > div > div > div { background: var(--blue) !important; border-radius: 980px; }
    /* 信息框 */
    [data-testid="stAlert"] { border-radius: 18px !important; border: 1px solid rgba(0,0,0,0.06) !important; background: #fff !important; box-shadow: 0 2px 8px rgba(0,0,0,0.04); padding: 1.25rem 1.5rem !important; }
    /* 下载按钮 */
    .stDownloadButton > button { border-radius: 980px !important; font-size: 0.85rem !important; }
    /* 响应式 */
    @media (max-width: 768px) { .main .block-container { padding: 1rem; } h1 { font-size: 1.8rem !important; } }
</style>
""", unsafe_allow_html=True)

# ── 工具函数 ──
def _get_download_label(filename: str) -> str:
    """将英文文件名映射为中文下载标签"""
    mapping = {
        "final_plan.md": "策划书正文 (Markdown)",
        "final_plan.html": "策划书正文 (网页版)",
        "final_plan.docx": "策划书正文 (Word)",
        "quality_report.md": "质量检查报告",
        "missing_checklist.md": "待补充信息清单",
        "client_supplement_guide.md": "客户补充资料引导问卷",
        "financial_questionnaire.md": "财务预测补充问卷",
        "defense_prep_report.md": "答辩预演手册",
        "DATA_PRIVACY.txt": "数据隐私承诺书",
        "change_log.md": "修改日志",
        "metadata.json": "元数据",
    }
    return mapping.get(filename, filename)

# ── Hero ──
st.markdown("""
<div style="text-align:center;padding:2.5rem 1rem 1.5rem;">
    <h1 style="font-size:3rem;font-weight:700;color:#1d1d1f;letter-spacing:-0.8px;margin:0;line-height:1.1;">
        竞赛策划智能体
    </h1>
    <p style="font-size:1.2rem;color:#86868b;margin-top:0.6rem;font-weight:400;letter-spacing:-0.2px;">
        输入项目资料，自动生成国奖级竞赛策划书
    </p>
</div>
""", unsafe_allow_html=True)

# ── 侧边栏 ──
with st.sidebar:
    st.markdown('<p style="font-size:0.75rem;font-weight:600;color:#86868b;text-transform:uppercase;letter-spacing:1px;margin-bottom:1rem;">项目资料</p>', unsafe_allow_html=True)

    competition = st.selectbox(
        "赛事组别",
        SUPPORTED_COMPETITIONS,
        help="选择您要参加的比赛，系统将自动匹配对应的国奖模板"
    )

    project_name = st.text_input(
        "项目名称 【必填】",
        placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化",
    )

    with st.expander("项目核心资料", expanded=True):
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

    with st.expander("团队信息"):
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

    with st.expander("文稿定制", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            pages = st.number_input("目标页数", 30, 150, 80)
        with col2:
            color_theme = st.selectbox(
                "配色方案",
                list(SUPPORTED_THEMES.keys()),
                format_func=lambda x: SUPPORTED_THEMES[x],
            )

    with st.expander("佐证材料"):
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

    generate = st.button("生成策划书", type="primary", use_container_width=True)

# ── 示例数据 ──
DEMO_DATA = {
    "project_name": "晶源新材——钙钛矿光伏电池关键材料国产化",
    "project_brief": "钙钛矿太阳能电池效率十年间从3.8%跃升至26.1%，但核心材料高纯度碘化铅长期依赖进口，进口试剂纯度仅99.99%且价格高达每克800-1200元。晶源新材团队自主研发了梯度结晶纯化工艺，将碘化铅纯度提升至99.999%（5N级），杂质离子浓度控制在10ppm以下。产品通过中国赛宝实验室验证，电池效率达25.3%（NREL认证），优于进口试剂制备的24.1%。已申请发明专利5项，发表SCI论文4篇，在苏州建成年产10吨级中试线，产品向天合光能、晶科能源等头部企业送样测试反馈良好。",
    "tech_principles": "核心技术包含三大模块：\n1. 溶剂络合分离：利用PbI₂与DMSO/DMF混合体系形成络合物，低温选择性溶解，杂质从500ppm降至50ppm以下。\n2. 温控梯度析出：基于PbI₂溶解度温度差异（25→100℃变化5倍），控制降温速率1-5℃/min，晶种诱导使粒径均匀控制在50-200μm。\n3. 多级重结晶联用：3次循环重结晶+活性炭吸附+0.22μm微孔过滤，最终纯度99.999%。",
    "innovations_str": "溶剂络合选择性分离,温控梯度析出,多级重结晶联用",
    "market_data": "据QYResearch报告，2023年全球钙钛矿光伏材料市场规模约4.2亿美元，预计2030年突破50亿美元，CAGR超42%。中国占全球需求45%，高纯碘化铅进口依赖度超80%。",
    "leader": "周明辉",
    "team_text": "吴子涵,材料物理与化学,博士研究生,纯化工艺负责人,发表SCI论文6篇\n赵子昂,化学工程,硕士研究生,中试放大负责人,全国化工设计竞赛一等奖\n林心怡,工商管理,硕士研究生,市场商务负责人,挑战杯省赛金奖",
    "advisor": "孙丽华",
    "advisor_title": "教授、博士生导师、国家杰出青年科学基金获得者",
    "past_awards_str": "2025年挑战杯省赛特等奖\n全国大学生化学实验竞赛一等奖",
    "patents": "5项发明专利（2项已授权）",
}

# ── 空状态提示 ──
if "generated" not in st.session_state:
    st.session_state.generated = False

if not st.session_state.generated:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.info("在左侧填写项目资料，点击「生成策划书」，右侧下载文件。")
    with col_b:
        if st.button("查看示例", use_container_width=True, type="secondary"):
            st.session_state.run_demo = True

    if st.session_state.get("run_demo"):
        st.success("正在生成演示案例...")
        with st.spinner(""):
            progress = st.progress(0, text="正在初始化...")
            agent = CompetitionAgent()
            progress.progress(30, text="生成中...")
            agent.run_demo()
            progress.progress(100, text="完成！")
            st.session_state.generated = True
            st.session_state.demo_result = agent
            st.rerun()

    with st.expander("这是什么？"):
        st.markdown("""
        ### 全自动竞赛策划智能体

        一个 AI 驱动的竞赛策划书自动生成系统，专为大学生顶级竞赛设计。

        **核心能力：**
        - **双库驱动**：国奖模板库 + 客户专属知识库
        - **1:1 仿写国奖结构**：章节、字数、话术完全对标
        - **零虚构**：所有内容来自客户资料，绝不编造
        - **全自动制图**：封面、架构图、流程图、配图一键生成
        - **多格式输出**：Markdown + HTML + Word 三种格式

        **适用赛事：** 互联网+、挑战杯、节能减排、创青春、三创赛 等 8 个主流赛事
        """)

# ── 显示演示结果 ──
if st.session_state.get("demo_result"):
    agent = st.session_state.demo_result
    st.success(
        f"演示案例生成完毕！"
        f"共 {agent.current_document.total_word_count} 字 · "
        f"{len(agent.current_template.chapters)} 章 · "
        f"{len(agent.current_document.chapters)} 章正文"
    )
    tab1, tab2, tab3 = st.tabs(["策划书正文", "下载文件", "下载图片"])
    with tab1:
        st.markdown(agent.current_document.get_full_text())
    with tab2:
        export_dir = agent.current_export.output_dir
        for f in sorted(export_dir.glob("*")):
            if f.is_file():
                with open(f, "rb") as fh:
                    st.download_button(_get_download_label(f.name), fh.read(), f.name)
    with tab3:
        st.markdown("### 下载生成的图片")
        st.warning("云端服务器无中文字体，图片中文可能显示为方块。建议在本地运行获取完美图片。")
        import glob as _glob
        img_files = sorted(_glob.glob("outputs/current/generated_images/*.png"))
        if img_files:
            cols = st.columns(3)
            for i, f in enumerate(img_files):
                with cols[i % 3]:
                    with open(f, "rb") as fh:
                        st.download_button(f.replace("\\","/").split("/")[-1],
                                         fh.read(), f.replace("\\","/").split("/")[-1],
                                         use_container_width=True)

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

        with st.spinner(""):
            progress = st.progress(0, text="正在初始化引擎...")
            status = st.empty()

            agent = CompetitionAgent()

            # 阶段1
            progress.progress(10, text="[1/7] 校验资料完整性...")
            submission, completeness = agent.input_processor.process_submission(raw_data)
            status.info(f"资料完整度 {completeness.score:.0%}，{completeness.level.value}")

            # 阶段2
            progress.progress(20, text="[2/7] 匹配国奖模板...")
            agent.current_template = agent.template_matcher.match_template(competition)
            status.info(f"已匹配「{agent.current_template.competition_name}」模板，共 {len(agent.current_template.chapters)} 章")

            # 阶段3
            progress.progress(35, text="[3/7] 解析项目素材，提取关键数据...")
            customer_kb = agent.input_processor.build_customer_knowledge_base()
            agent.current_data_pool = agent.material_parser.parse_and_build_pool(
                customer_kb, agent.current_template.chapters)
            status.info(f"已提取 {len(agent.current_data_pool.numeric_entities)} 组数据实体")

            # 阶段4+5
            progress.progress(50, text="[4/7] 按国奖框架逐章撰写正文...")
            agent.current_document = agent.content_generator.generate_all_chapters(
                agent.current_template, agent.current_data_pool)
            status.info(f"正文 {agent.current_document.total_word_count} 字，共 {len(agent.current_document.chapters)} 章")

            # 阶段6
            progress.progress(75, text="[5/7] 自动绘制图表（封面/架构/流程图/配图）...")
            user_visual = agent._load_visual_style(color_theme)
            from modules.diagram_generator import DiagramGenerator
            dg = DiagramGenerator(visual_style=user_visual)
            tech_name = agent.current_data_pool.tech_pool.get("technology_name", "")
            diagrams = dg.generate_all_diagrams_for_document(
                project_name=project_name, competition_name=competition,
                tech_name=tech_name, tech_modules=[], innovations=innovations)
            status.info(f"已生成 {len(diagrams)} 张图表")

            # 阶段7
            progress.progress(90, text="[6/7] 排版美化 + 导出文件...")
            from modules.layout_engine import LayoutEngine
            from modules.output_exporter import OutputExporter
            layout = LayoutEngine(user_visual)
            exporter = OutputExporter()
            agent.current_export = exporter.export_all(
                document=agent.current_document, layout_engine=layout)
            status.info(f"已导出 Markdown + HTML + Word 三种格式")

            progress.progress(100, text="[7/7] 策划书生成完毕！")

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

        tab1, tab2, tab3, tab4 = st.tabs(["策划书正文", "下载文件", "下载图片", "缺失清单"])

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
                        with open(f, "rb") as fh:
                            st.download_button(_get_download_label(f.name), fh.read(), f.name, use_container_width=True)

        with tab3:
            st.markdown("### 下载生成的图片")
            st.caption("以下图片已自动生成，可单独下载后插入策划书对应位置。")
            import glob as _glob
            img_files = sorted(_glob.glob("outputs/current/generated_images/*.png"))
            if img_files:
                cols = st.columns(3)
                for i, f in enumerate(img_files):
                    with cols[i % 3]:
                        name = f.replace("\\", "/").split("/")[-1]
                        with open(f, "rb") as fh:
                            st.download_button(f"[Chart] {name}", fh.read(), name,
                                             use_container_width=True)
            else:
                st.info("暂无图片，请先生成策划书。")

        with tab4:
            st.markdown(agent.current_document.get_missing_report())

# ── 底部品牌 ──
st.markdown("""
<div style="text-align:center;padding:3rem 0 2rem;color:#86868b;font-size:0.85rem;">
    <p style="margin:0;">双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版</p>
    <p style="margin:0.3rem 0 0;font-size:0.75rem;color:#aeaeb2;">Powered by Claude</p>
</div>
""", unsafe_allow_html=True)
