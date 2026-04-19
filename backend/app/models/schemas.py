"""
Data Models - 数据模型定义

定义API请求/响应的数据结构
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class MeetingPhaseEnum(str, Enum):
    """会议阶段"""
    PHASE_0 = "议题接收"
    PHASE_1 = "信息补全"
    PHASE_2 = "选席"
    PHASE_3 = "第一轮发言"
    PHASE_4 = "交锋"
    PHASE_5 = "决议"
    PHASE_6 = "可视化报告"


class TopicTypeEnum(str, Enum):
    """议题类型"""
    VALUATION = "估值分析"
    TREND = "趋势判断"
    FUNDAMENTAL = "基本面分析"
    TECHNICAL = "技术分析"
    GROWTH = "成长投资"
    RISK = "风险评估"
    COMPREHENSIVE = "综合分析"
    PORTFOLIO = "投资组合"


# ========== Request Models ==========

class StartMeetingRequest(BaseModel):
    """开始会议请求"""
    topic: str = Field(..., description="投资议题", example="格力当前价格值不值买入？")
    user_id: Optional[str] = Field(None, description="用户ID")


class AnswerQuestionsRequest(BaseModel):
    """回答澄清问题请求"""
    answers: Dict[str, str] = Field(..., description="问题答案")


class GenerateReportRequest(BaseModel):
    """生成报告请求"""
    meeting_id: str = Field(..., description="会议ID")


# ========== Response Models ==========

class AdvisorInfo(BaseModel):
    """顾问信息"""
    name: str
    title: str
    type: str
    philosophy: str
    style: str
    avatar: str


class AdvisorOpinionResponse(BaseModel):
    """顾问意见响应"""
    advisor_name: str
    opinion: str
    reasoning: str
    confidence: float
    red_flag: bool = False
    red_flag_reason: str = ""
    key_points: List[str] = []


class TensionPair(BaseModel):
    """张力对"""
    advisor1: str
    advisor2: str
    tension: str


class CrossfireDialog(BaseModel):
    """交锋对话"""
    topic: str
    advisor1: str
    response1: str
    advisor2: str
    response2: str


class Phase0Response(BaseModel):
    """Phase 0 响应"""
    phase: str = "PHASE_0"
    restated_topic: str
    topic_type: TopicTypeEnum
    key_info: Dict[str, str]


class Phase1Response(BaseModel):
    """Phase 1 响应"""
    phase: str = "PHASE_1"
    questions: List[str]
    need_user_input: bool = True


class Phase2Response(BaseModel):
    """Phase 2 响应"""
    phase: str = "PHASE_2"
    advisors: List[str]
    tension_pairs: List[TensionPair]


class Phase3Response(BaseModel):
    """Phase 3 响应"""
    phase: str = "PHASE_3"
    opinions: List[AdvisorOpinionResponse]


class Phase4Response(BaseModel):
    """Phase 4 响应"""
    phase: str = "PHASE_4"
    crossfire_dialogs: List[CrossfireDialog]


class RiskMap(BaseModel):
    """风险地图"""
    low: List[str] = []
    medium: List[str] = []
    high: List[str] = []
    red_flag: str = ""


class ActionAdvice(BaseModel):
    """行动建议"""
    short_term: List[str] = []
    mid_term: List[str] = []
    long_term: List[str] = []


class Resolution(BaseModel):
    """决议"""
    consensus: List[str] = []
    divergence: List[str] = []
    risk_map: RiskMap
    action_advice: ActionAdvice
    overall_judgment: str


class Phase5Response(BaseModel):
    """Phase 5 响应"""
    phase: str = "PHASE_5"
    resolution: Resolution


class Phase6Response(BaseModel):
    """Phase 6 响应"""
    phase: str = "PHASE_6"
    report_url: str
    report_html: Optional[str] = None


# ========== Meeting State ==========

class MeetingStateResponse(BaseModel):
    """会议状态响应"""
    meeting_id: str
    phase: MeetingPhaseEnum
    topic: str
    topic_type: TopicTypeEnum
    selected_advisors: List[str] = []
    opinions: List[AdvisorOpinionResponse] = []
    resolution: Optional[Resolution] = None
    created_at: datetime
    updated_at: datetime


# ========== WebSocket Message ==========

class WSMessage(BaseModel):
    """WebSocket消息"""
    type: str  # "phase_update", "advisor_opinion", "crossfire", "resolution", "error"
    phase: Optional[str] = None
    data: Optional[Any] = None
    message: Optional[str] = None


# ========== List Advisors ==========

class ListAdvisorsResponse(BaseModel):
    """列出顾问响应"""
    advisors: List[AdvisorInfo]
    tension_pairs: List[TensionPair]