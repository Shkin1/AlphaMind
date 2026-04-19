"""
Meeting Host - 会议主持人

负责协调投研会的6阶段流程
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import openai
from openai import AsyncOpenAI
import os
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class MeetingPhase(Enum):
    """会议阶段"""
    PHASE_0 = "议题接收"
    PHASE_1 = "信息补全"
    PHASE_2 = "选席"
    PHASE_3 = "第一轮发言"
    PHASE_4 = "交锋"
    PHASE_5 = "决议"
    PHASE_6 = "可视化报告"


class TopicType(Enum):
    """议题类型"""
    VALUATION = "估值分析"
    TREND = "趋势判断"
    FUNDAMENTAL = "基本面分析"
    TECHNICAL = "技术分析"
    GROWTH = "成长投资"
    RISK = "风险评估"
    COMPREHENSIVE = "综合分析"
    PORTFOLIO = "投资组合"


@dataclass
class MeetingState:
    """会议状态"""
    meeting_id: str
    phase: MeetingPhase = MeetingPhase.PHASE_0
    topic: str = ""
    topic_type: TopicType = TopicType.COMPREHENSIVE
    clarification_questions: List[str] = field(default_factory=list)
    user_answers: Dict[str, str] = field(default_factory=dict)
    selected_advisors: List[str] = field(default_factory=list)
    tension_pairs: List[Dict] = field(default_factory=list)
    opinions: List[Dict] = field(default_factory=list)
    crossfire_dialogs: List[Dict] = field(default_factory=list)
    resolution: Dict = field(default_factory=dict)
    stock_data: Dict = field(default_factory=dict)
    # 新增字段
    round_number: int = 0
    max_rounds: int = 20
    quiz_answers: Dict[str, str] = field(default_factory=dict)


class MeetingHost:
    """会议主持人"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

        logger.info(f"[MeetingHost] 初始化: base_url={self.base_url}, model={self.model}, api_key={'已设置' if api_key else '未设置'}")

        if not api_key:
            logger.warning("[MeetingHost] OPENAI_API_KEY未设置，将使用模拟模式")
            self.async_client = None
        else:
            try:
                self.async_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=self.base_url,
                    timeout=30.0  # 30秒超时
                )
                logger.info("[MeetingHost] AsyncOpenAI客户端初始化成功")
            except Exception as e:
                logger.error(f"[MeetingHost] OpenAI客户端初始化失败: {e}")
                self.async_client = None

    def get_system_prompt(self) -> str:
        """获取系统提示词 - 投资圆桌主持人"""
        return """你是"投资圆桌"的主持人，你不是10位投资专家中的任何一位，你是管理整个投资讨论流程的人。

## 你的职责
1. 引导用户清晰阐述投资议题
2. 用专家视角提出关键的澄清问题
3. 根据议题类型选择最相关的4-6位专家出席
4. 管理发言顺序和辩论节奏，确保观点充分碰撞
5. 综合所有观点，提炼结构化的"投资决策备忘录"

## 你的风格
- 冷静、中立、聚焦于逻辑和事实
- 不预设立场，不偏袒任何一位专家
- 确保每位专家都用其标志性的投资语言和框架发言
- 最终输出必须 actionable（可执行）

## 10位专家档案（用于选席）
1. **本杰明·格雷厄姆** - 价值投资之父，安全边际、内在价值
2. **沃伦·巴菲特** - 护城河、长期持有、优秀企业
3. **查理·芒格** - 多元思维、逆向思考、心理偏见
4. **彼得·林奇** - 草根调研、PEG、投资你所了解的
5. **张坤** - 深度研究、集中持股、商业模式
6. **王琛** - 均衡配置、宏观视角、风险预算
7. **史蒂夫·尼森** - 蜡烛图、技术分析、时机判断
8. **埃德温·勒菲弗** - 市场心理、交易纪律、投机智慧
9. **林君叡** - 量化投资、因子模型、系统化决策
10. **顶级私募专家** - 绝对收益、灵活策略、实战派

## 议题类型与专家选择
- **个股/基金研判**: 格雷厄姆、巴菲特、张坤、彼得·林奇、尼森
- **组合与配置**: 王琛、私募专家、林君叡、巴菲特
- **市场与行业判断**: 勒菲弗、王琛、彼得·林奇、芒格
- **买卖时机**: 尼森、勒菲弗、私募专家
- **风险与心态**: 芒格、格雷厄姆、勒菲弗
- **综合分析**: 选择4-6位覆盖核心视角

## 张力对设计（观点碰撞）
- 格雷厄姆(价值) vs 尼森(技术) - 买入时机分歧
- 巴菲特(长期) vs 私募专家(灵活) - 持有策略分歧
- 芒格(理性) vs 勒菲弗(心理) - 人性因素分歧
- 张坤(集中) vs 王琛(分散) - 仓位策略分歧

## 输出要求
- Phase 0: 简洁复述问题，判断议题类型
- Phase 1: 提出3-5个关键澄清问题，注明谁会问这个问题
- Phase 2: 列出出席专家、张力对、发言顺序
- Phase 5: 结构化的投资决策备忘录（共识、分歧、风险地图、行动选项）
"""

    async def _call_api(self, messages: list, temperature: float = 0.3, max_tokens: int = 500) -> str:
        """异步API调用"""
        if self.async_client is None:
            logger.warning("API客户端未初始化，返回模拟响应")
            return self._mock_response(messages)

        try:
            logger.info(f"[MeetingHost] 调用API: model={self.model}, base_url={self.base_url}")
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.info(f"[MeetingHost] API响应成功: {len(content)}字符")
            return content
        except Exception as e:
            logger.error(f"[MeetingHost] API调用失败: {type(e).__name__}: {str(e)}")
            # 返回模拟响应而不是抛出异常
            logger.warning("[MeetingHost] 使用模拟响应继续流程")
            return self._mock_response(messages)

    def _mock_response(self, messages: list) -> str:
        """模拟响应（用于测试）"""
        last_message = messages[-1]["content"] if messages else ""

        if "Phase 0" in last_message:
            return """【复述问题】用户询问该股票当前估值是否合理
【议题类型】估值分析
【关键信息】股票:格力电器; 时间范围:当前"""
        elif "Phase 1" in last_message:
            return """【澄清问题】
1. 您的持有周期是多长？短期投资还是长期持有？
2. 您对家电行业的整体看法如何？
3. 您的风险承受能力如何？
4. 除了估值，您还关注哪些方面？"""
        elif "Phase 2" in last_message:
            return """【选席结果】
顾问1: 本杰明·格雷厄姆
顾问2: 沃伦·巴菲特
顾问3: 张坤
顾问4: 王琛
顾问5: 史蒂夫·尼森

【张力对】
张力对1: 本杰明·格雷厄姆 vs 史蒂夫·尼森 - 价值派与技术派的碰撞
张力对2: 沃伦·巴菲特 vs 王琛 - 长期持有与量化分析的对比"""
        elif "Phase 5" in last_message:
            return """【共识】
- 该公司基本面良好
- 行业地位稳固

【分歧】
- 短期估值高低存在争议
- 技术走势判断不一

【风险地图】
- 低风险: 行业龙头地位稳固
- 中风险: 房地产市场影响家电需求
- 高风险: 原材料价格波动

【行动建议】
- 短期: 可逐步建仓
- 中期: 关注业绩发布
- 长期: 适合长期持有

【总体判断】
综合分析认为该股票具有较好的投资价值，建议根据个人风险偏好决定仓位。"""
        return "模拟响应内容"

    async def phase_0_receive_topic(self, state: MeetingState) -> Dict:
        """Phase 0: 议题接收"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
用户输入: {state.topic}

请完成Phase 0:
1. 复述核心问题（用简洁语言）
2. 判断议题类型
3. 提取关键信息（股票名称、代码等）

输出格式:
【复述问题】...
【议题类型】估值分析/趋势判断/基本面分析/技术分析/成长投资/风险评估/综合分析/投资组合
【关键信息】股票:xxx; 时间范围:xxx; 其他:xxx
"""
            }
        ]

        # 直接调用async方法
        content = await self._call_api(messages, 0.3, 500)
        result = self._parse_phase_0(content)

        state.phase = MeetingPhase.PHASE_1
        state.topic_type = result.get("topic_type", TopicType.COMPREHENSIVE)

        return {
            "phase": "PHASE_0",
            "result": result,
            "next_phase": "PHASE_1"
        }

    async def phase_1_info_completion(self, state: MeetingState) -> Dict:
        """Phase 1: 信息补全"""
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
议题: {state.topic}
议题类型: {state.topic_type.value}

请完成Phase 1:
提出3-5个关键澄清问题，帮助顾问们更好地分析。

问题应该:
- 与议题类型相关
- 帮助获取缺失的关键信息
- 引导用户思考深层问题

输出格式:
【澄清问题】
1. ...
2. ...
3. ...
4. ... (可选)
5. ... (可选)
"""
            }
        ]

        content = await self._call_api(messages, 0.5, 500)
        questions = self._parse_questions(content)

        state.phase = MeetingPhase.PHASE_2
        state.clarification_questions = questions

        return {
            "phase": "PHASE_1",
            "questions": questions,
            "next_phase": "PHASE_2",
            "need_user_input": True
        }

    async def phase_2_select_seats(self, state: MeetingState) -> Dict:
        """Phase 2: 选席"""
        context = f"""
议题: {state.topic}
议题类型: {state.topic_type.value}
用户补充信息: {json.dumps(state.user_answers, ensure_ascii=False) if state.user_answers else '无'}
"""

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
{context}

请完成Phase 2:
选择5-7位最合适的顾问参与讨论，并标注核心张力对。

选席原则:
- 根据议题类型选择核心顾问
- 确保存在观点碰撞（张力对）
- 考虑用户补充信息

输出格式:
【选席结果】
顾问1: xxx
顾问2: xxx
顾问3: xxx
顾问4: xxx
顾问5: xxx
顾问6: xxx (可选)
顾问7: xxx (可选)

【张力对】
张力对1: xxx vs xxx - 对立原因
张力对2: xxx vs xxx - 对立原因
张力对3: xxx vs xxx - 对立原因 (可选)
"""
            }
        ]

        content = await self._call_api(messages, 0.5, 800)
        result = self._parse_seats(content)

        state.phase = MeetingPhase.PHASE_3
        state.selected_advisors = result["advisors"]
        state.tension_pairs = result["tension_pairs"]

        return {
            "phase": "PHASE_2",
            "advisors": result["advisors"],
            "tension_pairs": result["tension_pairs"],
            "next_phase": "PHASE_3"
        }

    async def phase_5_resolution(self, state: MeetingState) -> Dict:
        """Phase 5: 决议"""
        opinions_text = "\n".join([
            f"- {op['advisor_name']}: {op['opinion'][:100] if op.get('opinion') else ''}..."
            for op in state.opinions
        ]) if state.opinions else "暂无顾问意见"

        crossfire_text = "\n".join([
            f"【{d['topic']}】{d['advisor1']}: {d['response1'][:50] if d.get('response1') else ''}... | {d['advisor2']}: {d['response2'][:50] if d.get('response2') else ''}..."
            for d in state.crossfire_dialogs
        ]) if state.crossfire_dialogs else "暂无交锋"

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
议题: {state.topic}

【顾问意见汇总】
{opinions_text}

【交锋要点】
{crossfire_text}

请完成Phase 5:
综合所有顾问意见，生成最终决议。

输出格式:
【共识】
- 顾问们一致认同的观点（如有）

【分歧】
- 存在争议的关键问题

【风险地图】
- 低风险: ...
- 中风险: ...
- 高风险: ...
- 【红牌警告】: 致命风险点（如有）

【行动建议】
- 短期: ...
- 中期: ...
- 长期: ...

【总体判断】
给出综合评估和最终建议
"""
            }
        ]

        content = await self._call_api(messages, 0.3, 1000)
        resolution = self._parse_resolution(content)

        state.phase = MeetingPhase.PHASE_6
        state.resolution = resolution

        return {
            "phase": "PHASE_5",
            "resolution": resolution,
            "next_phase": "PHASE_6"
        }

    def _parse_phase_0(self, content: str) -> Dict:
        """解析Phase 0结果"""
        result = {
            "restated_topic": "",
            "topic_type": TopicType.COMPREHENSIVE,
            "key_info": {}
        }

        if not content:
            return result

        lines = content.split('\n')
        for line in lines:
            if '【复述问题】' in line:
                result["restated_topic"] = line.split('】')[-1].strip()
            elif '【议题类型】' in line:
                type_str = line.split('】')[-1].strip()
                for t in TopicType:
                    if t.value in type_str:
                        result["topic_type"] = t
                        break
            elif '【关键信息】' in line:
                info_str = line.split('】')[-1].strip()
                for item in info_str.split(';'):
                    if ':' in item:
                        key, val = item.split(':', 1)
                        result["key_info"][key.strip()] = val.strip()

        return result

    def _parse_questions(self, content: str) -> List[str]:
        """解析澄清问题"""
        questions = []
        if not content:
            return ["您的持有周期是多长？", "您对该行业的看法如何？"]

        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and (line.startswith(('1.', '2.', '3.', '4.', '5.')) or
                        line.startswith(('1、', '2、', '3、', '4、', '5、'))):
                q = line.lstrip('12345.、 ').strip()
                if q:
                    questions.append(q)
        return questions[:5] if questions else ["您的持有周期是多长？", "您对该行业的看法如何？"]

    def _parse_seats(self, content: str) -> Dict:
        """解析选席结果"""
        advisors = []
        tension_pairs = []

        if not content:
            return {
                "advisors": ["沃伦·巴菲特", "张坤", "本杰明·格雷厄姆", "王琛", "史蒂夫·尼森"],
                "tension_pairs": [{"advisor1": "本杰明·格雷厄姆", "advisor2": "史蒂夫·尼森", "reason": "价值派与技术派"}]
            }

        lines = content.split('\n')
        in_tension = False

        for line in lines:
            line = line.strip()
            if '【张力对】' in line:
                in_tension = True
                continue
            elif '【选席结果】' in line:
                in_tension = False
                continue

            if in_tension:
                if 'vs' in line:
                    parts = line.split('-')
                    if len(parts) >= 1:
                        pair_match = parts[0].split('vs')
                        if len(pair_match) == 2:
                            # 提取纯名称（去掉括号内容，支持中文和英文括号）
                            adv1_raw = pair_match[0].strip()
                            adv2_raw = pair_match[1].strip()
                            # 处理英文括号
                            adv1 = adv1_raw.split('(')[0].split('（')[0].strip()
                            adv2 = adv2_raw.split('(')[0].split('（')[0].strip()
                            tension_pairs.append({
                                "advisor1": adv1,
                                "advisor2": adv2,
                                "reason": parts[-1].strip() if len(parts) > 1 else ""
                            })
            else:
                if '顾问' in line and ':' in line:
                    # 提取顾问名称（去掉括号内容，支持中文和英文括号）
                    full_name = line.split(':')[-1].strip()
                    # 先处理英文括号，再处理中文括号
                    pure_name = full_name.split('(')[0].split('（')[0].strip()
                    # 如果还有横线分隔的描述，也去掉
                    if '-' in pure_name:
                        pure_name = pure_name.split('-')[0].strip()
                    if pure_name:
                        advisors.append(pure_name)

        # 如果没解析到，使用默认
        if not advisors:
            advisors = ["沃伦·巴菲特", "张坤", "本杰明·格雷厄姆", "王琛", "史蒂夫·尼森"]

        return {
            "advisors": advisors[:7],
            "tension_pairs": tension_pairs[:3]
        }

    def _parse_resolution(self, content: str) -> Dict:
        """解析决议"""
        resolution = {
            "consensus": [],
            "divergence": [],
            "risk_map": {
                "low": [],
                "medium": [],
                "high": [],
                "red_flag": ""
            },
            "action_advice": {
                "short_term": [],
                "mid_term": [],
                "long_term": []
            },
            "overall_judgment": ""
        }

        if not content:
            return resolution

        lines = content.split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if '【共识】' in line:
                current_section = 'consensus'
            elif '【分歧】' in line:
                current_section = 'divergence'
            elif '【风险地图】' in line:
                current_section = 'risk_map'
            elif '【红牌警告】' in line:
                resolution["risk_map"]["red_flag"] = line.split('】')[-1].strip()
            elif '【行动建议】' in line:
                current_section = 'action_advice'
            elif '短期' in line:
                current_section = 'short_term'
            elif '中期' in line:
                current_section = 'mid_term'
            elif '长期' in line:
                current_section = 'long_term'
            elif '【总体判断】' in line:
                current_section = 'overall'
            elif '低风险' in line:
                resolution["risk_map"]["low"].append(line.split(':')[-1].strip())
            elif '中风险' in line:
                resolution["risk_map"]["medium"].append(line.split(':')[-1].strip())
            elif '高风险' in line:
                resolution["risk_map"]["high"].append(line.split(':')[-1].strip())
            elif current_section and line.startswith('-'):
                item = line.lstrip('- ').strip()
                if current_section == 'consensus':
                    resolution["consensus"].append(item)
                elif current_section == 'divergence':
                    resolution["divergence"].append(item)
                elif current_section == 'short_term':
                    resolution["action_advice"]["short_term"].append(item)
                elif current_section == 'mid_term':
                    resolution["action_advice"]["mid_term"].append(item)
                elif current_section == 'long_term':
                    resolution["action_advice"]["long_term"].append(item)
                elif current_section == 'overall':
                    resolution["overall_judgment"] += item + " "

        return resolution