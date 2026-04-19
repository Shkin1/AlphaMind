"""
Agent Base Class - 投资顾问基类

所有投资顾问继承此基类，实现独特的投资哲学和分析方法
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import openai
from openai import AsyncOpenAI
import os
import asyncio
import logging

logger = logging.getLogger(__name__)


class AdvisorType(Enum):
    """顾问类型分类"""
    VALUE = "value"           # 价值投资
    GROWTH = "growth"         # 成长投资
    TECHNICAL = "technical"   # 技术分析
    QUANT = "quant"           # 量化分析
    RISK = "risk"             # 风险投资
    TRADING = "trading"       # 交易
    PRIVATE_EQUITY = "pe"     # 私募


@dataclass
class AdvisorPersonality:
    """顾问人格设定"""
    name: str                          # 姓名
    title: str                         # 头衔/称号
    type: AdvisorType                  # 类型
    philosophy: str                    # 投资哲学
    style: str                         # 说话风格
    quotes: List[str] = field(default_factory=list)  # 经典语录
    analysis_methods: List[str] = field(default_factory=list)  # 分析方法
    conflict_with: List[str] = field(default_factory=list)  # 张力对立顾问
    avatar: str = ""                   # 头像标识
    language_style: str = "chinese"    # 语言风格 (chinese/english/mixed)


@dataclass
class AdvisorOpinion:
    """顾问意见"""
    advisor_name: str
    opinion: str                       # 核心观点
    reasoning: str                     # 推理过程
    confidence: float = 0.7            # 置信度 0-1
    red_flag: bool = False             # 是否红牌警告
    red_flag_reason: str = ""          # 红牌原因
    key_points: List[str] = field(default_factory=list)  # 关键点


# 全局共享的OpenAI客户端（避免每个顾问都创建一个）
_shared_async_client = None
_shared_model = None


def get_shared_async_client():
    """获取共享的AsyncOpenAI客户端"""
    global _shared_async_client, _shared_model

    if _shared_async_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
        _shared_model = os.getenv("OPENAI_MODEL", "gpt-4o")

        if api_key:
            try:
                _shared_async_client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url,
                    timeout=60.0
                )
                logger.info(f"共享AsyncOpenAI客户端初始化成功: {base_url}")
            except Exception as e:
                logger.error(f"AsyncOpenAI客户端初始化失败: {e}")
                _shared_async_client = None
        else:
            logger.warning("OPENAI_API_KEY未设置")

    return _shared_async_client, _shared_model


class BaseAdvisor(ABC):
    """投资顾问基类"""

    def __init__(self):
        self.personality: AdvisorPersonality = self._define_personality()
        # 使用懒加载，不在这里创建客户端

    def get_async_client(self):
        """获取AsyncOpenAI客户端"""
        return get_shared_async_client()

    def get_system_prompt(self) -> str:
        """获取系统提示词 - 简洁版"""
        quotes_sample = self.personality.quotes[:2]  # 只取2条语录
        methods_text = "、".join(self.personality.analysis_methods[:3])  # 只取3个方法
        conflicts_text = "、".join(self.personality.conflict_with[:2])  # 只取2个对立

        return f"""你是{self.personality.name}，{self.personality.title}。

核心哲学: {self.personality.philosophy[:200]}
风格: {self.personality.style[:100]}
方法: {methods_text}
对立观点: {conflicts_text}

行为准则:
1. 严格保持{self.personality.name}的语气和思维方式
2. 用核心哲学分析问题，给出专业判断
3. 关键时刻可引用经典语录
4. 发现致命风险标注【红牌警告】
5. 语言: {self.personality.language_style}
"""

    async def _call_api(self, messages: list, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """异步API调用"""
        client, model = self.get_async_client()

        if client is None:
            logger.warning(f"[{self.personality.name}] API客户端未初始化，返回模拟响应")
            return self._mock_response(messages)

        try:
            logger.debug(f"[{self.personality.name}] 调用API: model={model}")
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            content = response.choices[0].message.content
            logger.debug(f"[{self.personality.name}] API响应成功")
            return content
        except Exception as e:
            logger.error(f"[{self.personality.name}] API调用失败: {e}")
            return self._mock_response(messages)

    def _mock_response(self, messages: list) -> str:
        """模拟响应（用于测试或API失败时）"""
        return f"""【核心观点】基于我的投资哲学，我认为这是一个值得关注的机会，但需要谨慎评估。
【推理过程】作为{self.personality.name}，我关注的是{self.personality.philosophy[:50]}...
【置信度】中
【关键点】
- 基本面分析很重要
- 需要关注长期价值
- 风险控制不可忽视
"""

    async def analyze(self, context: Dict[str, Any], stock_data: Optional[Dict] = None) -> AdvisorOpinion:
        """
        分析投资问题 - 简化版，支持记忆
        """
        # 构建简洁消息
        prompt = f"议题: {context.get('topic', '')}\n"
        prompt += f"类型: {context.get('topic_type', '综合分析')}\n"

        # 用户偏好
        quiz_answers = context.get('quiz_answers', {})
        if quiz_answers:
            prompt += f"用户偏好: 投资周期={quiz_answers.get('time_horizon', '长期')}, 意向={quiz_answers.get('position_intent', '分析')}, 风险承受={quiz_answers.get('risk_tolerance', '均衡')}\n"

        if stock_data:
            prompt += f"股票: {stock_data.get('name')} 价格:{stock_data.get('price', '未知')}元\n"

        # 历史观点记忆 - 关键改进：传递所有之前的发言
        opinions = context.get('opinions', []) or context.get('other_opinions', [])
        if opinions:
            prompt += "\n【之前发言记录】\n"
            # 只取最近5条，避免太长
            recent_opinions = opinions[-5:] if len(opinions) > 5 else opinions
            for op in recent_opinions:
                speaker = op.get('advisor_name', '顾问')
                content = op.get('opinion', '')
                # 截取前150字，避免太长
                prompt += f"- {speaker}: {content[:150]}{'...' if len(content) > 150 else ''}\n"

            # 找出对立顾问的观点，特别标注
            for conflict in self.personality.conflict_with:
                conflict_op = next(
                    (op for op in recent_opinions if conflict in op.get('advisor_name', '')),
                    None
                )
                if conflict_op:
                    prompt += f"\n【观点碰撞】{conflict}认为: {conflict_op.get('opinion', '')[:100]}...\n请用你的哲学回应:\n"

        # 当前轮次
        round_num = context.get('round_number', 1)
        if round_num == 1:
            prompt += "\n这是第一轮发言，请给出你的初始观点。"
        else:
            prompt += f"\n这是第{round_num}轮发言，请参考之前观点，发表你的看法（可补充、反驳或提出新视角）。"

        prompt += "\n直接发言，像真实会议一样自然表达，给出明确判断(看好/谨慎/回避):"

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": prompt}
        ]

        content = await self._call_api(messages, 0.7, 800)  # 增加token限制，避免截断
        return self._parse_opinion(content)

    def _build_analysis_prompt(self, context: Dict[str, Any], stock_data: Optional[Dict] = None) -> str:
        """构建分析提示词 - 强调专业性和交锋"""
        prompt = f"""你正在参加一场投资专家圆桌会议，讨论议题：{context.get('topic', '')}

议题类型：{context.get('topic_type', '综合分析')}
"""

        if stock_data:
            prompt += f"""
【关键数据】
股票：{stock_data.get('name', '未知')} ({stock_data.get('code', '未知')})
现价：{stock_data.get('price', '未知')}元
趋势：{stock_data.get('trend', '未知')}
支撑位：{stock_data.get('support_level', '未知')}元
阻力位：{stock_data.get('resistance_level', '未知')}元
"""

        # 如果有其他顾问观点，要求进行交锋
        if context.get('other_opinions'):
            prompt += "\n【已发言顾问观点】\n"
            for op in context['other_opinions']:
                advisor = op['advisor_name']
                view = op.get('opinion', '')[:150]
                prompt += f"- {advisor}: {view}...\n"

            # 找出对立顾问的观点
            for conflict in self.personality.conflict_with:
                conflict_op = next(
                    (op for op in context['other_opinions'] if conflict in op['advisor_name']),
                    None
                )
                if conflict_op:
                    prompt += f"""
【观点碰撞】{conflict}认为：{conflict_op.get('opinion', '')[:100]}...
作为{self.personality.name}，你需要用你的投资哲学回应这个观点。
如果同意，可以补充你的视角；如果不同意，有力反驳。
"""

        prompt += f"""
现在，作为{self.personality.name}，请发表你的专业分析。

【发言要求】
1. 用你独特的投资哲学分析这个议题
2. 如有对立观点，进行有理有据的交锋
3. 给出明确判断：看好/谨慎/回避，并说明理由
4. 用你的风格说话，体现专业性

【输出格式】
直接发言，不要标注格式标签。像真实会议发言一样，自然流畅地表达你的观点。
"""
        return prompt

    def _parse_opinion(self, content: str) -> AdvisorOpinion:
        """解析顾问意见 - 适应自然发言格式"""
        opinion = AdvisorOpinion(
            advisor_name=self.personality.name,
            opinion="",
            reasoning="",
            confidence=0.7,
            red_flag=False,
            red_flag_reason="",
            key_points=[]
        )

        if not content:
            opinion.opinion = "基于我的投资哲学，这需要深入分析后才能判断。"
            opinion.reasoning = "需更多数据和深入调研。"
            return opinion

        # 直接使用整个发言作为opinion
        opinion.opinion = content.strip()

        # 从发言中提取关键信息
        content_lower = content.lower()

        # 检测红牌警告
        if "红牌" in content or "致命风险" in content or "重大风险" in content:
            opinion.red_flag = True
            # 提取红牌原因
            if "红牌警告" in content:
                parts = content.split("红牌警告")
                if len(parts) > 1:
                    opinion.red_flag_reason = parts[1].split("\n")[0].strip()

        # 判断置信度
        if any(word in content_lower for word in ["确信", "强烈", "高置信", "非常看好", "坚定"]):
            opinion.confidence = 0.9
        elif any(word in content_lower for word in ["谨慎", "观望", "不确定", "存疑", "风险"]):
            opinion.confidence = 0.5

        # 提取关键点（从发言中找要点）
        key_points = []
        if "首先" in content:
            parts = content.split("首先")
            if len(parts) > 1:
                key_points.append(parts[1].split("\n")[0][:50].strip())
        if "其次" in content:
            parts = content.split("其次")
            if len(parts) > 1:
                key_points.append(parts[1].split("\n")[0][:50].strip())
        if "最后" in content:
            parts = content.split("最后")
            if len(parts) > 1:
                key_points.append(parts[1].split("\n")[0][:50].strip())

        # 如果没找到，从整体提取
        if not key_points and len(content) > 50:
            sentences = content.replace("\n", " ").split(".")
            for s in sentences[:3]:
                if len(s.strip()) > 10:
                    key_points.append(s.strip()[:50])

        opinion.key_points = key_points[:5] if key_points else ["需进一步分析"]
        opinion.reasoning = content[:100] if len(content) > 100 else content

        return opinion

    async def crossfire(self, opponent_name: str, opponent_opinion: str,
                        topic: str, stock_data: Optional[Dict] = None) -> str:
        """
        与其他顾问交锋辩论

        Args:
            opponent_name: 对方顾问名称
            opponent_opinion: 对方观点
            topic: 讨论议题
            stock_data: 股票数据

        Returns:
            str: 交锋回应
        """
        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            {"role": "user", "content": f"""
## 议题
{topic}

## {opponent_name}的观点
{opponent_opinion}

## 你的任务
作为{self.personality.name}，请对{opponent_name}的观点进行回应。
- 可以表示赞同、部分赞同或反对
- 用你的投资哲学反驳或补充
- 保持你独特的说话风格
- 引用数据或你的经典语录来支持你的观点
- 如有必要，可以提出新的分析角度

请直接给出你的回应（不要标注格式）：
"""
            }
        ]

        content = await self._call_api(messages, 0.8, 500)
        return content if content else f"我对此有不同的看法..."

    def __repr__(self):
        return f"<{self.personality.name} - {self.personality.title}>"