"""
简化的任务分类API

只保留第一版核心功能
"""
from fastapi import APIRouter, HTTPException
from .core.response_models import (
    TaskClassificationRequest,
    TaskClassificationResponse,
    DataResponse
)

router = APIRouter(prefix="/api/task", tags=["任务分类"])


@router.post("/classify", response_model=DataResponse)
async def classify_task(request: TaskClassificationRequest):
    """分类任务"""
    try:
        # 简化实现 - 直接导入需要的agent
        # TaskClassificationAgent 需要预约与咨询两个 agent 才能构造
        from agents.task_classification_agent import TaskClassificationAgent
        from agents.appointment_agent import AppointmentAgent
        from agents.consultant_agent import ConsultantAgent
        agent = TaskClassificationAgent(AppointmentAgent(), ConsultantAgent())
        result = await agent.classify_task(request.text)
        
        return DataResponse(
            message="任务分类成功",
            data=result
        )
    except Exception as e:
        # 服务端异常不是客户端参数问题，用 500 而不是 400
        raise HTTPException(status_code=500, detail=str(e))
