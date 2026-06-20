"""
全自动竞赛策划智能体 - LLM API客户端

封装大模型调用，支持 Anthropic Claude API。
采用智能体循环模式：发送prompt → 接收响应 → 如需工具调用则继续。
"""

import os
import json
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# 尝试导入 SDK
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


@dataclass
class LLMResponse:
    """LLM响应封装"""
    content: str
    model: str
    tokens_used: int
    stop_reason: str


class LLMClient:
    """
    LLM API客户端

    优先使用 Anthropic Claude API，支持：
    - 系统提示词设定智能体角色
    - 多轮对话上下文管理
    - 自动重试与错误处理
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        provider: str = "auto",
    ):
        # 自动检测provider：优先检查环境变量
        self.api_key = api_key
        if not self.api_key:
            self.api_key = os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
        if provider == "auto":
            if os.getenv("DEEPSEEK_API_KEY"):
                provider = "deepseek"
            elif os.getenv("ANTHROPIC_API_KEY"):
                provider = "anthropic"
            elif self.api_key:
                provider = "deepseek"  # default to deepseek since it's more accessible
        self.provider = provider
        self.model = model or (os.getenv("ANTHROPIC_MODEL", "deepseek-chat"))
        self.system_prompt = system_prompt or ""
        self.max_tokens = max_tokens
        self.temperature = temperature

        # 初始化客户端
        self.client = None
        if self.api_key:
            if self.provider == "deepseek":
                if HAS_OPENAI:
                    self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/v1")
                else:
                    self._use_raw_http = True  # fallback to raw HTTP
            elif self.provider == "anthropic" and HAS_ANTHROPIC:
                self.client = anthropic.Anthropic(api_key=self.api_key)
            elif HAS_OPENAI:
                self.client = OpenAI(api_key=self.api_key, base_url="https://api.deepseek.com/v1")
                self.provider = "deepseek"
            elif HAS_ANTHROPIC:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                self.provider = "anthropic"
            else:
                self._use_raw_http = True
                self.provider = "deepseek"
        self._use_raw_http = getattr(self, '_use_raw_http', False)

        # 会话上下文
        self.conversation_history: List[Dict[str, Any]] = []
        self.total_tokens_used = 0

    @property
    def is_available(self) -> bool:
        """检查LLM服务是否可用"""
        return self.client is not None or getattr(self, '_use_raw_http', False)

    def reset_conversation(self) -> None:
        """重置对话上下文"""
        self.conversation_history = []
        self.total_tokens_used = 0

    def chat(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        if not self.is_available:
            return self._mock_response(user_message)

        sys_prompt = system_prompt or self.system_prompt
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens or self.max_tokens

        try:
            if getattr(self, '_use_raw_http', False):
                return self._chat_raw_http(user_message, sys_prompt, temp, max_tok)
            if self.provider == "deepseek":
                messages = []
                if sys_prompt:
                    messages.append({"role": "system", "content": sys_prompt})
                messages.append({"role": "user", "content": user_message})
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=temp,
                    max_tokens=max_tok,
                )
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens if hasattr(response, 'usage') else 0
                self.total_tokens_used += tokens
                return LLMResponse(content=content, model="deepseek-chat", tokens_used=tokens, stop_reason="stop")
            else:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tok,
                    system=sys_prompt,
                    temperature=temp,
                    messages=[{"role": "user", "content": user_message}],
                )
                content = self._extract_text(response)
                tokens = response.usage.output_tokens if hasattr(response, 'usage') else 0
                self.total_tokens_used += tokens
                return LLMResponse(content=content, model=self.model, tokens_used=tokens, stop_reason=response.stop_reason or "end_turn")
        except Exception as e:
            print(f"[LLMClient] API调用异常: {e}")
            return self._mock_response(user_message)

    def generate_chapter(
        self,
        chapter_name: str,
        chapter_config: dict,
        data_pool: dict,
        rhetoric_templates: list,
        style_requirements: str,
    ) -> str:
        """
        生成单个章节内容（核心写作接口）

        Args:
            chapter_name: 章节名称
            chapter_config: 章节配置（骨架、必备要素、字数要求等）
            data_pool: 中央数据池（客户素材提取的数据）
            rhetoric_templates: 匹配的话术模板列表
            style_requirements: 风格要求描述

        Returns:
            生成的章节Markdown文本
        """
        # 从数据池中提取本章相关数据
        relevant_data = self._filter_relevant_data(data_pool, chapter_name)

        prompt = self._build_chapter_prompt(
            chapter_name=chapter_name,
            chapter_config=chapter_config,
            data=relevant_data,
            rhetoric_templates=rhetoric_templates,
            style_requirements=style_requirements,
        )

        response = self.chat(
            user_message=prompt,
            temperature=0.5,  # 写作任务用较低温度保证一致性
            max_tokens=6000,
        )

        return response.content

    def judge_content(self, full_text: str, template_config: dict) -> Dict[str, Any]:
        """
        AI模拟评审官：对生成内容进行评分

        Returns:
            包含各维度评分、总分和修改建议的字典
        """
        prompt = f"""你是一位资深的竞赛评委。请对以下竞赛策划书进行评审。

评审维度与权重：
1. 创新性与技术壁垒（25分）
2. 商业价值与市场前景（20分）
3. 社会价值与政策契合度（15分）
4. 团队实力与执行可行性（15分）
5. 文档规范性与完整性（15分）
6. 逻辑一致性与数据可信度（10分）

请以JSON格式输出评审结果：
{{
    "创新性": {{"score": X, "comment": "..."}},
    "商业价值": {{"score": X, "comment": "..."}},
    "社会价值": {{"score": X, "comment": "..."}},
    "团队实力": {{"score": X, "comment": "..."}},
    "文档规范": {{"score": X, "comment": "..."}},
    "逻辑一致性": {{"score": X, "comment": "..."}},
    "总分": X,
    "关键改进建议": ["建议1", "建议2", "建议3"],
    "是否达到国奖水准": true/false
}}

策划书内容：
{full_text[:15000]}
"""
        response = self.chat(user_message=prompt, temperature=0.3)

        try:
            # 尝试提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response.content)
            if json_match:
                return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

        return {"总分": 0, "关键改进建议": ["无法解析评审结果"], "是否达到国奖水准": False}

    def generate_questions_for_missing(self, missing_items: List[str]) -> List[str]:
        """
        针对缺失项生成引导式问题清单
        """
        prompt = f"""客户提交的项目资料中，以下关键信息缺失：
{chr(10).join(f'- {item}' for item in missing_items)}

请为每一项缺失信息，生成一个具体、友好的引导式问题，帮助客户补充内容。
要求：
- 问题要具体，引导客户给出可用的数据或描述
- 用词友好，不能显得在质疑客户
- 每项生成1-2个问题

请直接列出问题清单："""
        response = self.chat(user_message=prompt, temperature=0.5)
        questions = [q.strip('- ').strip() for q in response.content.split('\n') if q.strip().startswith(('-', '•', '1', '2', '3', '4', '5', '6', '7', '8', '9'))]
        return questions if questions else [response.content]

    def _build_chapter_prompt(
        self,
        chapter_name: str,
        chapter_config: dict,
        data: dict,
        rhetoric_templates: list,
        style_requirements: str,
    ) -> str:
        """构建章节生成提示词"""
        required_elements = chapter_config.get("required_elements", [])
        paragraph_structure = chapter_config.get("paragraph_structure", [])
        word_count = chapter_config.get("word_count_range", "2000-3000字")

        prompt = f"""# 任务：撰写竞赛策划书章节

## 章节名称
{chapter_name}

## 写作约束（严格遵守）
1. **零虚构原则**：以下提供的数据是你写作的唯一素材来源，不得超过数据范围进行"合理想象"
2. **国奖结构**：严格按照以下段落结构组织内容：
{chr(10).join(f'   {i+1}. {step}' for i, step in enumerate(paragraph_structure))}
3. **必备要素**：本章必须包含以下要素：
{chr(10).join(f'   - {elem}' for elem in required_elements)}
4. **字数要求**：{word_count}
5. **话术风格**：参考以下国奖话术模板进行仿写：
{chr(10).join(f'   - {r}' for r in rhetoric_templates[:5])}
6. **数据引用**：每引用一个数据，必须用【数据来源：XXX】标注
7. **缺失处理**：如果某个要素在素材中找不到对应内容，输出【待补充：具体缺什么】，绝不编造

## 风格要求
{style_requirements}

## 可用素材数据（只能使用以下内容）
{json.dumps(data, ensure_ascii=False, indent=2)[:8000]}

## 输出格式
请直接输出本章的Markdown格式内容（从## {chapter_name}开始），不要添加额外说明。"""
        return prompt

    def _filter_relevant_data(self, data_pool: dict, chapter_name: str) -> dict:
        """根据章节名称筛选相关数据"""
        chapter_data_map = {
            "执行摘要": ["project_brief", "key_metrics", "team_highlights"],
            "项目背景": ["market_data", "industry_data", "policy_data"],
            "核心技术": ["tech_principles", "patents", "papers", "innovations", "tech_params"],
            "产品设计": ["product_desc", "application_scenarios", "prototype_data"],
            "市场分析": ["market_data", "competitor_data", "business_model", "revenue_data"],
            "团队介绍": ["team_members", "advisor_info", "past_awards"],
            "财务预测": ["financial_data", "funding_plan", "cost_structure"],
            "未来规划": ["development_plan", "social_value", "milestones"],
        }

        # 匹配最相关的章节
        matched_keys = []
        for key_pattern, keys in chapter_data_map.items():
            if key_pattern in chapter_name or chapter_name in key_pattern:
                matched_keys = keys
                break

        if not matched_keys:
            # 返回全部数据
            return data_pool

        return {k: v for k, v in data_pool.items() if k in matched_keys}

    def _chat_raw_http(self, user_msg, sys_prompt, temp, max_tok):
        """Raw HTTP fallback for DeepSeek API"""
        import urllib.request
        msgs = []
        if sys_prompt: msgs.append({"role":"system","content":sys_prompt})
        msgs.append({"role":"user","content":user_msg})
        data = json.dumps({"model":"deepseek-chat","messages":msgs,"temperature":temp,"max_tokens":max_tok}).encode()
        req = urllib.request.Request("https://api.deepseek.com/v1/chat/completions", data=data,
            headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        content = result["choices"][0]["message"]["content"]
        return LLMResponse(content=content, model="deepseek-chat", tokens_used=0, stop_reason="stop")

    def _extract_text(self, response) -> str:
        """从Anthropic响应中提取文本"""
        if hasattr(response, 'content'):
            content = response.content
            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if hasattr(block, 'text'):
                        text_parts.append(block.text)
                    elif isinstance(block, dict) and block.get('type') == 'text':
                        text_parts.append(block.get('text', ''))
                return '\n'.join(text_parts)
            elif isinstance(content, str):
                return content
            else:
                return str(content)
        return str(response)

    def _mock_response(self, user_message: str) -> LLMResponse:
        """
        模拟响应（API不可用时使用）
        生成基于模板的合理内容，确保智能体仍可运行演示
        """
        # 根据用户消息类型返回合适的mock内容
        if "撰写竞赛策划书章节" in user_message:
            return self._mock_chapter_response(user_message)
        elif "评审" in user_message:
            return self._mock_judge_response()
        elif "问题清单" in user_message:
            return self._mock_questions_response()
        else:
            return LLMResponse(
                content="[演示模式] 请配置 ANTHROPIC_API_KEY 环境变量以启用AI生成功能。",
                model="mock",
                tokens_used=0,
                stop_reason="end_turn",
            )

    def _mock_chapter_response(self, user_message: str) -> LLMResponse:
        """生成演示用的模拟章节内容"""
        # 提取章节名
        import re
        chapter_match = re.search(r'章节名称\n(.+)', user_message)
        chapter_name = chapter_match.group(1).strip() if chapter_match else "未知章节"

        # 提取数据中的项目名称
        project_name = "【演示项目】"
        name_match = re.search(r'"project_name":\s*"([^"]+)"', user_message)
        if name_match:
            project_name = name_match.group(1)

        content = f"""## {chapter_name}

> 【演示模式】以下内容为模板化生成，配置API后可获得定制化国奖级内容。

本项目聚焦于{project_name}，在技术研发、团队建设和市场拓展方面取得了显著成果。

### 核心要点

1. **技术优势**：团队自主研发的核心技术已达到国内领先水平，相关成果已申请发明专利。
2. **市场前景**：据行业调研数据显示，目标市场规模持续增长，年复合增长率超过25%。
3. **团队实力**：核心成员来自多学科交叉背景，指导教师具有丰富的科研和产业经验。

> ⚠️ **提示**：当前为离线演示模式。要生成真正的国奖水准内容，请设置 `ANTHROPIC_API_KEY` 环境变量。

---
*【待补充】具体的量化数据、技术参数、竞品对比等信息需要基于客户提交的真实素材生成。*
"""
        return LLMResponse(
            content=content,
            model="mock",
            tokens_used=0,
            stop_reason="end_turn",
        )

    def _mock_judge_response(self) -> LLMResponse:
        return LLMResponse(
            content=json.dumps({
                "创新性": {"score": 20, "comment": "技术方案有创新点，但需补充更多原创性论证"},
                "商业价值": {"score": 16, "comment": "商业模式清晰，市场规模论证待加强"},
                "社会价值": {"score": 13, "comment": "符合国家战略方向"},
                "团队实力": {"score": 12, "comment": "团队结构合理"},
                "文档规范": {"score": 13, "comment": "结构完整，格式规范"},
                "逻辑一致性": {"score": 8, "comment": "数据前后一致"},
                "总分": 82,
                "关键改进建议": [
                    "增强技术壁垒论证，补充与竞品的量化对比",
                    "完善市场数据支撑，引用权威第三方报告",
                    "补充更多落地应用案例和实际效果证明"
                ],
                "是否达到国奖水准": False
            }, ensure_ascii=False),
            model="mock",
            tokens_used=0,
            stop_reason="end_turn",
        )

    def _mock_questions_response(self) -> LLMResponse:
        return LLMResponse(
            content="""1. 请问您的项目目前处于什么阶段（实验室验证/中试/已落地应用）？
2. 您是否有与竞品对比的具体性能参数数据？
3. 项目的目标市场规模是多少？是否有第三方市场报告支撑？
4. 团队核心成员的导师是否具有国家级项目主持经历？
5. 项目是否已获得专利授权？如有，请提供专利号和证书。""",
            model="mock",
            tokens_used=0,
            stop_reason="end_turn",
        )
