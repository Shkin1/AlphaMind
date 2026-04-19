"""
Meeting Service - 会议流程服务

支持：
- 智能发言机制（混合模式：第一轮全员，后续轮规则判断）
- SSE流式传输
- 澄清问题弹框
- 信息采集（博查+Akshare）
- 共识检测
- 最多20轮讨论
"""

import uuid
import random
import json
import logging
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

logger = logging.getLogger(__name__)

from ..agents.advisor_registry import AdvisorRegistry
from ..agents.meeting_host import MeetingHost, MeetingState, MeetingPhase, TopicType
from ..services.data_collector import collector_manager, CollectedData

# 所有10位顾问
ALL_ADVISORS = [
    "本杰明·格雷厄姆",
    "沃伦·巴菲特",
    "查理·芒格",
    "彼得·林奇",
    "张坤",
    "王琛",
    "史蒂夫·尼森",
    "埃德温·勒菲弗",
    "林君叡",
    "顶级私募专家"
]

# 澄清问题模板
QUIZ_QUESTIONS = [
    {
        "id": "time_horizon",
        "question": "你的投资周期是？",
        "options": ["短期(<1年)", "中期(1-3年)", "长期(>3年)"],
        "default": "长期(>3年)"
    },
    {
        "id": "position_intent",
        "question": "你对这只股票的意向是？",
        "options": ["考虑买入", "持有观察", "考虑卖出", "仅做分析"],
        "default": "仅做分析"
    },
    {
        "id": "risk_tolerance",
        "question": "你的风险承受能力？",
        "options": ["保守(厌恶亏损)", "均衡", "激进(追求高收益)"],
        "default": "均衡"
    }
]

# 采集选项
COLLECTION_OPTIONS = [
    {
        "id": "bocha",
        "name": "博查网页采集",
        "description": "搜索股票相关新闻、研报、公告",
        "available": True
    },
    {
        "id": "akshare",
        "name": "Akshare数据采集",
        "description": "获取股票实时行情、财务数据",
        "available": True
    }
]


class SmartDiscussionEngine:
    """智能发言引擎 - 混合模式"""

    def __init__(self):
        self.all_advisors = ALL_ADVISORS

    def get_speakers_for_round(self, round_num: int, opinions: List[dict],
                                selected_advisors: List[str]) -> List[str]:
        """判断本轮谁想发言"""
        # 第一轮：全员发言
        if round_num == 1:
            return selected_advisors

        # 后续轮：规则判断 + 随机补充
        speakers = []
        recent_opinions = opinions[-5:] if len(opinions) >= 5 else opinions

        for advisor_name in selected_advisors:
            advisor = AdvisorRegistry.get_advisor(advisor_name)
            if not advisor:
                continue

            has_conflict = self._check_rule_conflict(advisor, recent_opinions)
            if has_conflict:
                speakers.append(advisor_name)
            elif random.random() < 0.2:
                speakers.append(advisor_name)

        return speakers[:5]

    def _check_rule_conflict(self, advisor, recent_opinions: List[dict]) -> bool:
        """规则判断：顾问是否与最近观点有冲突"""
        for op in recent_opinions:
            speaker_name = op.get("advisor_name", "")
            if speaker_name in advisor.personality.conflict_with:
                return True
            op_sentiment = self._quick_sentiment(op.get("opinion", ""))
            my_expected = self._get_expected_sentiment(advisor)
            if op_sentiment and my_expected and op_sentiment != my_expected:
                return True
        return False

    def _quick_sentiment(self, text: str) -> Optional[str]:
        """快速判断观点倾向"""
        if "看好" in text or "值得" in text or "买入" in text or "持有" in text:
            return "看好"
        if "谨慎" in text or "风险" in text or "观望" in text:
            return "谨慎"
        if "回避" in text or "不建议" in text or "卖出" in text:
            return "回避"
        return None

    def _get_expected_sentiment(self, advisor) -> Optional[str]:
        """获取顾问默认倾向"""
        type_map = {
            "value": "看好", "growth": "看好", "quant": "谨慎",
            "risk": "看好", "technical": None, "trading": None, "pe": None
        }
        return type_map.get(advisor.personality.type.value, None)

    def check_consensus(self, opinions: List[dict]) -> dict:
        """检测是否达成共识"""
        views = {"看好": 0, "谨慎": 0, "回避": 0, "观望": 0}
        for op in opinions:
            sentiment = self._quick_sentiment(op.get("opinion", ""))
            if sentiment:
                views[sentiment] += 1
            else:
                views["观望"] += 1

        total = sum(views.values())
        if total == 0:
            return {"has_consensus": False, "consensus_view": None, "ratio": 0, "distribution": views}

        max_view = max(views, key=views.get)
        return {
            "has_consensus": views[max_view] / total > 0.6,
            "consensus_view": max_view,
            "ratio": views[max_view] / total,
            "distribution": views
        }


class MeetingService:
    """会议流程服务"""

    _active_meetings: Dict[str, MeetingState] = {}

    def __init__(self):
        self.host = MeetingHost()
        self.discussion_engine = SmartDiscussionEngine()
        AdvisorRegistry.initialize()

    def create_meeting(self, topic: str) -> MeetingState:
        """创建新会议"""
        meeting_id = str(uuid.uuid4())[:8]
        state = MeetingState(
            meeting_id=meeting_id,
            topic=topic,
            phase=MeetingPhase.PHASE_0,
            topic_type=TopicType.COMPREHENSIVE
        )
        state.round_number = 0
        state.max_rounds = 20
        state.quiz_answers = {}
        state.collection_choices = []
        state.collected_data = {}
        self._active_meetings[meeting_id] = state
        return state

    def get_meeting(self, meeting_id: str) -> Optional[MeetingState]:
        """获取会议状态"""
        return self._active_meetings.get(meeting_id)

    def get_quiz_questions(self) -> List[dict]:
        """获取澄清选择题"""
        return QUIZ_QUESTIONS

    def get_collection_options(self) -> List[dict]:
        """获取采集选项"""
        # 检查采集器可用性
        options = []
        for opt in COLLECTION_OPTIONS:
            collector = collector_manager.get_collector(opt["id"])
            available = collector.is_available() if collector else False
            options.append({
                **opt,
                "available": available
            })
        return options

    def submit_quiz_answers(self, meeting_id: str, answers: dict) -> dict:
        """提交选择题答案"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}
        state.quiz_answers = answers
        return {"success": True}

    def submit_collection_choices(self, meeting_id: str, choices: List[str]) -> dict:
        """提交采集选项"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}
        state.collection_choices = choices
        state.phase = MeetingPhase.PHASE_2
        return {"success": True}

    def extract_stock_name(self, topic: str) -> Optional[str]:
        """从议题提取股票名称"""
        stock_keywords = ['格力', '格力电器', '茅台', '贵州茅台', '比亚迪', '宁德时代',
                          '平安', '中国平安', '腾讯', '招商银行', '五粮液', '美的', '美的集团',
                          '海尔', '海尔智家', '隆基', '隆基绿能', '中芯', '中芯国际']

        for keyword in stock_keywords:
            if keyword in topic:
                return keyword
        return None

    async def execute_collection(self, meeting_id: str) -> Dict:
        """执行信息采集"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}

        stock_name = self.extract_stock_name(state.topic)
        results = {}

        for choice in state.collection_choices:
            collector = collector_manager.get_collector(choice)
            if not collector or not collector.is_available():
                continue

            try:
                if choice == "akshare" and stock_name:
                    # 采集股票数据
                    realtime_result = await collector.collect(stock_name, data_type="realtime")
                    if realtime_result.content and not realtime_result.error:
                        results["stock_data"] = realtime_result.content
                        state.stock_data = realtime_result.content

                elif choice == "bocha" and stock_name:
                    # 采集新闻资讯
                    news_result = await collector.collect(
                        f"{stock_name} 最新动态 研报分析",
                        data_type="news"
                    )
                    if news_result.content and not news_result.error:
                        results["news"] = news_result.content

            except Exception as e:
                logger.error(f"[采集] {choice}失败: {e}")
                results[choice] = {"error": str(e)}

        state.collected_data = results
        return results

    async def run_phase_0(self, meeting_id: str) -> Dict:
        """Phase 0: 议题接收 + 提取关键词"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}

        topic_lower = state.topic.lower()
        if any(k in topic_lower for k in ['估值', '贵不贵', '值不值得']):
            state.topic_type = TopicType.VALUATION
        elif any(k in topic_lower for k in ['趋势', '走势', '涨跌']):
            state.topic_type = TopicType.TREND
        else:
            state.topic_type = TopicType.COMPREHENSIVE

        # 提取股票名称
        stock_name = self.extract_stock_name(state.topic)

        return {
            "type": "phase_update",
            "phase": "PHASE_0",
            "data": {
                "restated_topic": state.topic,
                "topic_type": state.topic_type.value,
                "stock_name": stock_name,
                "key_info": {"股票": stock_name or "未识别"}
            }
        }

    async def run_phase_1(self, meeting_id: str) -> Dict:
        """Phase 1: 澄清问题 + 采集选项"""
        return {
            "type": "phase_update",
            "phase": "PHASE_1",
            "data": {
                "quiz_questions": QUIZ_QUESTIONS,
                "collection_options": self.get_collection_options(),
                "message": "请选择投资偏好和信息采集方式"
            }
        }

    async def run_phase_2(self, meeting_id: str) -> Dict:
        """Phase 2: 执行采集"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}

        # 执行采集
        collection_results = await self.execute_collection(meeting_id)

        return {
            "type": "phase_update",
            "phase": "PHASE_2",
            "data": {
                "collection_results": collection_results,
                "stock_data": state.stock_data,
                "message": "信息采集完成"
            }
        }

    async def run_phase_3(self, meeting_id: str) -> Dict:
        """Phase 3: 全员入场"""
        state = self.get_meeting(meeting_id)
        if not state:
            return {"error": "会议不存在"}

        state.selected_advisors = ALL_ADVISORS
        state.tension_pairs = [
            {"advisor1": "沃伦·巴菲特", "advisor2": "史蒂夫·尼森", "tension": "价值派与技术派"},
            {"advisor1": "本杰明·格雷厄姆", "advisor2": "林君叡", "tension": "安全边际与成长投资"},
        ]
        state.phase = MeetingPhase.PHASE_3
        state.round_number = 1

        return {
            "type": "phase_update",
            "phase": "PHASE_3",
            "data": {
                "advisors": state.selected_advisors,
                "tension_pairs": state.tension_pairs,
                "stock_data": state.stock_data,
                "collected_news": state.collected_data.get("news", {}),
                "message": f"已邀请{len(state.selected_advisors)}位顾问参与讨论"
            }
        }

    async def discussion_stream(self, meeting_id: str) -> AsyncGenerator[str, None]:
        """SSE流 - Phase 0-1，等待用户选择"""
        state = self.get_meeting(meeting_id)
        if not state:
            yield f"data: {json.dumps({'type': 'error', 'message': '会议不存在'}, ensure_ascii=False)}\n\n"
            return

        # Phase 0
        msg = await self.run_phase_0(meeting_id)
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        # Phase 1 - 澄清问题 + 采集选项
        msg = await self.run_phase_1(meeting_id)
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        # 等待用户选择
        yield f"data: {json.dumps({'type': 'waiting_for_selection'}, ensure_ascii=False)}\n\n"

    async def continue_discussion(self, meeting_id: str) -> AsyncGenerator[str, None]:
        """用户提交后继续：采集 -> 讨论"""
        state = self.get_meeting(meeting_id)
        if not state:
            yield f"data: {json.dumps({'type': 'error', 'message': '会议不存在'}, ensure_ascii=False)}\n\n"
            return

        # Phase 2: 执行采集
        msg = await self.run_phase_2(meeting_id)
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        # Phase 3: 全员入场
        msg = await self.run_phase_3(meeting_id)
        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

        # 智能讨论循环
        context = {
            "topic": state.topic,
            "topic_type": state.topic_type.value,
            "quiz_answers": state.quiz_answers,
            "stock_data": state.stock_data,
            "collected_news": state.collected_data.get("news", {}),
            "opinions": [],
            "round_number": 0
        }

        for round_num in range(1, state.max_rounds + 1):
            state.round_number = round_num
            context["round_number"] = round_num

            # 检测共识
            consensus = self.discussion_engine.check_consensus(state.opinions)
            if consensus["has_consensus"] and round_num > 1:
                yield f"data: {json.dumps({'type': 'round_summary', 'data': {'round': round_num, 'consensus_reached': True, 'consensus_view': consensus['consensus_view']}}, ensure_ascii=False)}\n\n"
                break

            # 获取发言者
            speakers = self.discussion_engine.get_speakers_for_round(round_num, state.opinions, state.selected_advisors)
            if not speakers:
                continue

            for advisor_name in speakers:
                try:
                    advisor = AdvisorRegistry.get_advisor(advisor_name)
                    if not advisor:
                        continue

                    # 发送"正在发言"提示
                    yield f"data: {json.dumps({'type': 'advisor_speaking', 'advisor_name': advisor_name, 'round': round_num}, ensure_ascii=False)}\n\n"

                    # 更新context中的历史观点
                    context["opinions"] = state.opinions.copy()

                    # 调用顾问分析
                    opinion = await advisor.analyze(context, state.stock_data)

                    # 推送完整意见
                    yield f"data: {json.dumps({'type': 'advisor_opinion', 'phase': 'PHASE_3', 'data': {'advisor_name': advisor_name, 'opinion': opinion.opinion, 'confidence': opinion.confidence, 'round': round_num}}, ensure_ascii=False)}\n\n"

                    state.opinions.append({"advisor_name": advisor_name, "opinion": opinion.opinion, "round": round_num})

                except Exception as e:
                    logger.error(f"[Round {round_num}] {advisor_name} 发言失败: {e}")

            # 每轮总结
            round_consensus = self.discussion_engine.check_consensus(state.opinions)
            yield f"data: {json.dumps({'type': 'round_summary', 'data': {'round': round_num, 'speakers_count': len(speakers), 'distribution': round_consensus['distribution']}}, ensure_ascii=False)}\n\n"

        # 决议 - 生成完整决议
        # 发送加载提示
        yield f"data: {json.dumps({'type': 'resolution_generating', 'message': '正在生成综合决议...'}, ensure_ascii=False)}\n\n"

        # 调用 AI 生成完整决议
        try:
            resolution_result = await self.host.phase_5_resolution(state)
            state.resolution = resolution_result.get("resolution", {})
            state.phase = MeetingPhase.PHASE_6
        except Exception as e:
            logger.error(f"[决议生成失败] {e}")
            # 使用默认决议
            state.resolution = {
                "consensus": ["顾问们对议题进行了深入讨论"],
                "divergence": ["部分观点存在分歧"],
                "risk_map": {"low": [], "medium": [], "high": [], "red_flag": ""},
                "action_advice": {"short_term": [], "mid_term": [], "long_term": []},
                "overall_judgment": "综合分析完成，建议结合个人情况做出决策。"
            }

        # 发送完整决议数据
        consensus = self.discussion_engine.check_consensus(state.opinions)
        yield f"data: {json.dumps({
            'type': 'resolution',
            'phase': 'PHASE_5',
            'data': {
                'consensus': state.resolution.get('consensus', []),
                'divergence': state.resolution.get('divergence', []),
                'risk_map': state.resolution.get('risk_map', {}),
                'action_advice': state.resolution.get('action_advice', {}),
                'overall_judgment': state.resolution.get('overall_judgment', ''),
                'consensus_view': consensus['consensus_view'],
                'ratio': consensus['ratio'],
                'total_opinions': len(state.opinions),
                'distribution': consensus['distribution']
            }
        }, ensure_ascii=False)}\n\n"

        # 完成
        yield f"data: {json.dumps({'type': 'complete'}, ensure_ascii=False)}\n\n"

    def get_all_meetings(self) -> List[Dict]:
        """获取所有会议"""
        return [{"meeting_id": m.meeting_id, "topic": m.topic, "phase": m.phase.value} for m in self._active_meetings.values()]


meeting_service = MeetingService()