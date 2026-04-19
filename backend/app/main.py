"""
FastAPI Main Entry - SSE流式版本

投研会 API 服务 - 支持全屏聊天、逐字输出、智能发言
"""

# 首先加载环境变量
from dotenv import load_dotenv
import os
import sys
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# 加载.env
env_paths = [
    Path.cwd() / '.env',
    Path(__file__).parent.parent / '.env',
]
for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"已加载环境变量: {env_path}")
        break

api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_API_BASE", "")
model = os.getenv("OPENAI_MODEL", "")
logger.info(f"API配置: base_url={base_url}, model={model}, api_key={'已设置' if api_key else '未设置'}")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional, List
import json
import asyncio

from .services.meeting_service import meeting_service
from .services.report_generator import report_generator
from .agents.advisor_registry import AdvisorRegistry
from .models.schemas import (
    StartMeetingRequest, AnswerQuestionsRequest,
    ListAdvisorsResponse, AdvisorInfo, TensionPair
)

# 创建应用
app = FastAPI(
    title="AlphaMind 投研会",
    description="AI投资专家圆桌会议系统 - 智能发言、逐字输出",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
frontend_dir = Path(__file__).parent.parent.parent / 'frontend'
css_dir = frontend_dir / 'css'
js_dir = frontend_dir / 'js'

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
if css_dir.exists():
    app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
if js_dir.exists():
    app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")


# ========== Pydantic Models ==========

class QuizAnswerRequest(BaseModel):
    answers: Dict[str, str]


class CollectionChoiceRequest(BaseModel):
    choices: List[str]


# ========== API Routes ==========

@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端页面"""
    index_path = frontend_dir / 'index.html'
    if index_path.exists():
        return FileResponse(str(index_path))
    return HTMLResponse(content="<h1>AlphaMind 投研会</h1>")


@app.get("/meeting.html", response_class=HTMLResponse)
async def meeting_page():
    """返回投研会议页面"""
    meeting_path = frontend_dir / 'meeting.html'
    if meeting_path.exists():
        return FileResponse(str(meeting_path))
    return HTMLResponse(content="<h1>会议页面不存在</h1>")


@app.get("/api/advisors")
async def list_advisors():
    """列出所有顾问"""
    advisors_info = AdvisorRegistry.get_advisor_info()
    tension_pairs = AdvisorRegistry.get_tension_pairs()

    advisors = [
        AdvisorInfo(
            name=info["name"],
            title=info["title"],
            type=info["type"],
            philosophy=info["philosophy"],
            style=info["style"],
            avatar=info["avatar"]
        )
        for info in advisors_info
    ]

    pairs = [
        TensionPair(
            advisor1=pair["advisor1"],
            advisor2=pair["advisor2"],
            tension=pair["tension"]
        )
        for pair in tension_pairs
    ]

    return ListAdvisorsResponse(advisors=advisors, tension_pairs=pairs)


@app.post("/api/meeting/start")
async def start_meeting(request: StartMeetingRequest):
    """开始投研会 - 创建会议"""
    state = meeting_service.create_meeting(request.topic)
    logger.info(f"创建会议: id={state.meeting_id}, topic={request.topic}")

    return {
        "meeting_id": state.meeting_id,
        "topic": state.topic,
        "phase": state.phase.value,
        "message": "会议已创建，请连接SSE开始讨论"
    }


@app.get("/api/meeting/{meeting_id}/quiz")
async def get_quiz_questions(meeting_id: str):
    """获取澄清选择题"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    questions = meeting_service.get_quiz_questions()
    return {
        "meeting_id": meeting_id,
        "questions": questions
    }


@app.post("/api/meeting/{meeting_id}/quiz")
async def submit_quiz_answers(meeting_id: str, request: QuizAnswerRequest):
    """提交选择题答案"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    result = meeting_service.submit_quiz_answers(meeting_id, request.answers)
    logger.info(f"提交选择题: meeting_id={meeting_id}, answers={request.answers}")

    return {
        "meeting_id": meeting_id,
        "success": True,
        "message": "答案已提交"
    }


class CollectionChoiceRequest(BaseModel):
    choices: List[str]


@app.post("/api/meeting/{meeting_id}/collect")
async def submit_collection_choices(meeting_id: str, request: CollectionChoiceRequest):
    """提交采集选项"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    result = meeting_service.submit_collection_choices(meeting_id, request.choices)
    logger.info(f"提交采集选项: meeting_id={meeting_id}, choices={request.choices}")

    return {
        "meeting_id": meeting_id,
        "success": True,
        "message": "采集选项已提交"
    }


@app.get("/api/meeting/{meeting_id}/discuss")
async def discussion_stream(meeting_id: str):
    """SSE流 - Phase 0-1，等待选择题"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    logger.info(f"讨论SSE连接: meeting_id={meeting_id}")

    async def generate():
        try:
            yield f": ping\n\n"
            async for message in meeting_service.discussion_stream(meeting_id):
                yield message
        except Exception as e:
            logger.error(f"SSE流错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@app.get("/api/meeting/{meeting_id}/continue")
async def continue_discussion(meeting_id: str):
    """SSE流 - 用户提交选择题后继续讨论"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    logger.info(f"继续讨论SSE: meeting_id={meeting_id}")

    async def generate():
        try:
            yield f": ping\n\n"
            async for message in meeting_service.continue_discussion(meeting_id):
                yield message
        except Exception as e:
            logger.error(f"继续讨论SSE错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


@app.get("/api/meeting/{meeting_id}/stream")
async def meeting_stream_legacy(meeting_id: str):
    """SSE流 - 兼容旧版本（完整意见推送）"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    logger.info(f"SSE连接(legacy): meeting_id={meeting_id}")

    async def generate():
        try:
            yield f": ping\n\n"

            # Phase 0-2
            msg0 = await meeting_service.run_phase_0(meeting_id)
            yield f"data: {json.dumps(msg0, ensure_ascii=False)}\n\n"

            msg1 = await meeting_service.run_phase_1(meeting_id)
            yield f"data: {json.dumps(msg1, ensure_ascii=False)}\n\n"

            msg2 = await meeting_service.run_phase_2(meeting_id)
            yield f"data: {json.dumps(msg2, ensure_ascii=False)}\n\n"

            # 使用新讨论流
            async for message in meeting_service.discussion_stream(meeting_id):
                yield message

        except Exception as e:
            logger.error(f"SSE流错误: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.get("/api/meeting/{meeting_id}")
async def get_meeting_state(meeting_id: str):
    """获取会议状态"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    return {
        "meeting_id": state.meeting_id,
        "topic": state.topic,
        "phase": state.phase.value,
        "topic_type": state.topic_type.value,
        "selected_advisors": state.selected_advisors,
        "opinions": state.opinions,
        "resolution": state.resolution,
        "stock_data": state.stock_data,
        "round_number": getattr(state, 'round_number', 0),
        "quiz_answers": getattr(state, 'quiz_answers', {})
    }


@app.post("/api/meeting/{meeting_id}/report")
async def generate_report(meeting_id: str):
    """生成HTML报告"""
    state = meeting_service.get_meeting(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="会议不存在")

    report_data = {
        "meeting_id": state.meeting_id,
        "topic": state.topic,
        "topic_type": state.topic_type.value,
        "stock_data": state.stock_data,
        "selected_advisors": state.selected_advisors,
        "opinions": state.opinions,
        "resolution": state.resolution
    }

    html_content = report_generator.generate_report(report_data)
    logger.info(f"生成报告: meeting_id={meeting_id}")

    return {
        "meeting_id": meeting_id,
        "report_html": html_content
    }


@app.get("/api/meeting/list")
async def list_meetings():
    """列出所有会议"""
    return meeting_service.get_all_meetings()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AlphaMind 投研会 v2.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)