"""
简化的预约API

只保留第一版核心功能
"""
from fastapi import APIRouter, HTTPException
from .core.response_models import (
    AppointmentRequest,
    AppointmentResponse,
    DataResponse
)

router = APIRouter(prefix="/api/appointment", tags=["预约管理"])


@router.post("/create", response_model=DataResponse)
async def create_appointment(request: AppointmentRequest):
    """创建预约"""
    try:
        # 简化实现 - 直接导入需要的服务
        from agents.appointment_agent import AppointmentAgent
        agent = AppointmentAgent(session_id=request.user_id)
        # AppointmentAgent 只有流式入口，这里把请求字段拼成一句话并收集 token
        text = f"我想预约{request.service_type}，时间是{request.preferred_time}"
        if request.notes:
            text += f"，备注：{request.notes}"
        result = ""
        async for token in agent.run_stream(user_input=text):
            result += token
        
        return DataResponse(
            message="预约创建成功",
            data=result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
