# 全自动竞赛策划智能体

输入项目资料 → 自动生成国奖级竞赛策划书（Word + PPT + PDF + 图表）

## 快速开始

### 网页版（推荐）

打开 https://jiuqiu.streamlit.app → 填资料 → 点生成 → 下载

### 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

### AI 增强（可选）

去 [platform.deepseek.com](https://platform.deepseek.com) 免费注册获取 API 密钥，填入侧边栏「AI 密钥」即可启用 AI 生成。不填也能用离线模板。

## 支持赛事

互联网+、挑战杯、节能减排、创青春、三创赛 等 8 个主流赛事

## 输出文件

| 文件 | 用途 |
|------|------|
| final_plan.docx | Word 可编辑版（推荐） |
| final_plan.html | 网页预览版（含图表） |
| final_plan.pdf | PDF 提交版 |
| defense.pptx | 答辩 PPT |
| plagiarism_report.md | 查重预检报告 |
| executive_summary.md | 执行摘要 + 路演稿 |
| competitor_analysis.md | 竞品对标分析 |

## 项目结构

```
├── app.py              # Streamlit 界面
├── main.py             # CLI 入口
├── modules/            # 核心模块
│   ├── content_generator.py   # 内容生成
│   ├── diagram_generator.py   # 图表生成
│   ├── ppt_generator.py       # PPT 生成
│   ├── plagiarism_checker.py  # 查重预检
│   └── defense_prep.py        # 答辩预演
├── knowledge_base/     # 国奖模板库（8 赛事）
├── tests/              # 单元测试
└── requirements.txt    # 依赖
```

## 测试

```bash
python tests/test_basic.py
```
