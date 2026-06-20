    tab1, tab2 = st.tabs(["📂 导入 / AI配置", "✏️ 手动填写"])

    with tab1:
        st.caption("上传文件自动填充，或输入API Key启用AI")
        uploaded = st.file_uploader("上传项目文件", type=["json", "txt", "docx"], label_visibility="collapsed")
        st.caption("支持 JSON 配置 / Word 文档 / TXT 文本")
        if uploaded:
            try:
                if uploaded.name.endswith('.json'):
                    data = json.loads(uploaded.read())
                    if "project_material" in data:
                        st.session_state.project_name = data["project_material"].get("project_name", "")
                        st.session_state.project_brief = data["project_material"].get("project_brief", "")
                        st.session_state.tech_principles = data["project_material"].get("tech_principles", "")
                        st.session_state.market_data = data["project_material"].get("market_data", "")
                        st.session_state.leader = data["team_info"].get("project_leader", "")
                        st.session_state.advisor = data["team_info"].get("advisor_name", "")
                        st.success("已自动填充")
                        st.rerun()
                elif uploaded.name.endswith('.docx'):
                    from docx import Document
                    text = '
'.join([p.text for p in Document(uploaded).paragraphs])
                    st.session_state.project_brief = text[:2000]
                    st.success("文档解析成功")
                    st.rerun()
                else:
                    st.session_state.project_brief = uploaded.read().decode('utf-8')[:2000]
                    st.success("文本已加载")
                    st.rerun()
            except Exception as e:
                st.error(f"导入失败: {e}")
        st.markdown('<hr style="margin:0.6rem 0;border-color:#E5E7EB;">', unsafe_allow_html=True)
        api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-... 启用AI国奖级生成", label_visibility="collapsed")
        if api_key:
            import os; os.environ["ANTHROPIC_API_KEY"] = api_key; st.success("AI已启用")

    with tab2:
    project_name = st.text_input("项目名称 *", placeholder="例：晶源新材——钙钛矿光伏电池关键材料国产化")

    st.markdown('<hr style="margin:0.8rem 0;border-color:#E5E7EB;">', unsafe_allow_html=True)
    st.markdown('<p style="font-size:0.7rem;color:#9CA3AF;text-transform:uppercase;letter-spacing:1px;margin:0 0 0.3rem;">✏️ 手动填写</p>', unsafe_allow_html=True)
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

    fields_check = [project_name, project_brief, leader, advisor, tech_principles, market_data]
    filled = sum(1 for v in fields_check if v and (isinstance(v, str) and len(v.strip()) > 0))
    st.markdown(f'<p style="font-size:0.72rem;color:#9CA3AF;text-align:center;margin:0.3rem 0;">已填写 {filled}/{len(fields_check)} 项核心字段</p>', unsafe_allow_html=True)
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
        st.markdown("""### 竞赛策划智能体
AI 驱动的竞赛策划书自动生成系统，支持 8 个主流赛事。

**核心能力**
- 双库驱动 + 1:1 国奖仿写 + 零虚构原则
- 自动生成封面、架构图、流程图、配图、商业画布、路线图
- 输出 Word / HTML / PDF / Markdown

**智能增强**
- 查重预检：模板句检测 + 长句重复 + 风险评分
- 答辩预演：评委提问 + 答辩技巧 + 答辩PPT
- 执行摘要：300字摘要 + 1分钟路演稿
- 竞品对标分析
- 资料完整度分级引导补全""")

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

            status.update(label="查重预检中...", state="running")
            from modules.plagiarism_checker import PlagiarismChecker
            from modules.defense_prep import DefensePrep
            from utils.helpers import ensure_dir, write_text_file
            full_text = agent.current_document.get_full_text()
            out = agent.current_export.output_dir; ensure_dir(out)
            pc = PlagiarismChecker()
            write_text_file(out / "plagiarism_report.md", pc.format_markdown(pc.check(full_text)))
            status.update(label="生成摘要+路演稿...", state="running")
            dp = DefensePrep()
            write_text_file(out / "executive_summary.md", dp.generate_summary(full_text, agent.current_document.project_name))
            status.update(label="生成答辩手册...", state="running")
            write_text_file(out / "defense_prep_report.md", dp.print_report(dp.generate_defense_prep(full_text, agent.current_document.project_name)))
            # 生成PPT+竞品对标
            from modules.ppt_generator import PPTGenerator
            pptg = PPTGenerator()
            pptg.generate_ppt(full_text, agent.current_document.project_name, out / "defense.pptx")
            ca = pptg.format_competitor_table(pptg.analyze_competitors(full_text))
            if ca: write_text_file(out / "competitor_analysis.md", ca)

            status.update(label="生成完毕", state="complete")
        st.success(f"已生成 · {agent.current_document.total_word_count} 字 · {len(agent.current_template.chapters)} 章 · {len(diagrams)} 张图表")

        # 分类下载
        _show_downloads(agent.current_export.output_dir)

        with st.expander("查看正文"): st.markdown(agent.current_document.get_full_text())

# ── 底部 ──
st.markdown("""<div style="text-align:center;padding:3rem 0 2rem;color:#86868b;font-size:0.85rem;">
    <p style="margin:0;color:#6B7280;">双库驱动 · 国奖模板 · 零虚构 · 全自动制图排版</p>
    <p style="margin:0.3rem 0 0;font-size:0.75rem;color:#9CA3AF;">Powered by Claude</p>
</div>""", unsafe_allow_html=True)
