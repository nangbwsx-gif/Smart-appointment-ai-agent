"""
FastAPI应用程序

主应用程序入口，配置中间件、路由和异常处理
自动初始化知识库和技师数据
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from services.knowledge_service import KnowledgeService
from services.technician_service import TechnicianService
from services.recommendation_service import RecommendationService
from typing import List, Optional
import logging
import asyncio

# 导入路由
from api import api_routers  #将所有API接口的地址拿来 后面会统一注册进FASTAPI
from api.core.exceptions import api_exception_handler, general_exception_handler, BusinessException #错误处理规则
from web import router as web_router # 网页界面的地址表

# 配置日志
logging.basicConfig(level=logging.INFO)  # 给系统装监控和记录规则
logger = logging.getLogger(__name__)     # 使用logger记录日志，方便后续排查问题

# Pydantic模型
from pydantic import BaseModel  # 会自动校验请求 类似于ts的接口 用来定义规则

class KnowledgeRequest(BaseModel):  # 新增知识
    content: str  # 内容
    category: str # 分类
    keywords: List[str] = []  # 关键词

class SearchRequest(BaseModel): # 搜索知识
    query: str           # 搜索词 
    top_k: int = 5       # 返回结果数量 
    category: Optional[str] = None # 分类

async def initialize_system():
    """系统启动时自动初始化"""
    try:
        logger.info("🚀 正在初始化智能预约系统...")
        
        # 初始化知识库服务
        logger.info("📚 初始化知识库服务...")
        knowledge_service = KnowledgeService()
        await knowledge_service.initialize()  # 这是异步初始化，可能要读库、建索引，很慢，值得等
        
        # 初始化技师服务
        logger.info("👨‍⚕️ 初始化技师服务...")
        technician_service = TechnicianService()
        technician_service.initialize_default_technicians() # 同步方法，在内存里快速初始化默认技师，很快，没必要异步
        
        # 初始化推荐服务
        logger.info("🎯 启动推荐调度服务...")
        recommendation_service = RecommendationService()
        if recommendation_service.start_scheduler():
            logger.info("✅ 推荐调度服务启动成功")
        else:
            logger.warning("⚠️ 推荐调度服务启动失败")
        
        logger.info("✅ 系统初始化完成！")
        
    except Exception as e:  # Exception是所有异常的基类，捕获所有异常 
        logger.error(f"❌ 系统初始化失败: {e}")
        raise    # 把异常上报

def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="智能预约AI代理",
        description="提供预约管理、智能咨询、用户行为分析等功能的API服务",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # 添加CORS中间件
    # 如果前后端被浏览器同源策略限制，前端无法访问后端API，就需要加这个中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境中应该设置具体的域名
        allow_credentials=True, #  允许带凭证（cookie/token）
        allow_methods=["*"],  # 允许所有请求方法
        allow_headers=["*"],   # 允许所有请求头
    )

    # 注册异常处理器
    # BusinessException 是“业务规则没通过”的信号 
    # api_exception_handler 是 FastAPI 收到这个信号后调用的“统一客服话术” 
    app.add_exception_handler(BusinessException, api_exception_handler) 
    app.add_exception_handler(Exception, general_exception_handler)

    # 注册API路由
    for router in api_routers:
        app.include_router(router)

    # 注册Web界面路由
    app.include_router(web_router)

    # 静态文件
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

    # 添加启动事件
    @app.on_event("startup")
    async def startup_event():
        """应用启动时自动初始化系统"""
        await initialize_system()

    return app

# 创建应用实例
app = create_app()

if __name__ == "__main__":
    import uvicorn  # uvicorn是FastAPI的启动器 / 服务器
    uvicorn.run(app, host="127.0.0.1", port=8001)
