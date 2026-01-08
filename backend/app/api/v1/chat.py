from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional, List
import json
import uuid
import logging
import time
from datetime import datetime
import jwt
import os

from app.services.chat_service import ChatService
from app.services.multi_agent_system import get_agent_coordinator
from app.utils.rag_pipeline import RAGPipeline
from app.managers.session_manager import session_manager
from app.managers.logger_manager import logger_manager
from app.managers.mysql_manager import mysql_manager
from app.managers.redis_manager import redis_manager
from app.managers.prometheus_manager import prometheus_metrics
from app.core.security import verify_token, is_token_blacklisted
import asyncio
import logging as logger
from app.models import ChatRequest, ChatResponse, SessionCreateRequest, SessionResponse, SessionListResponse, SessionRenameRequest

router = APIRouter()
security = HTTPBearer()

# 初始化服务
chat_service = ChatService()

# 初始化RAG管道 - 添加错误处理和日志
rag_pipeline = None
try:
    rag_pipeline = RAGPipeline()
    rag_status = rag_pipeline.is_available()
    logger.info(f"RAG管道初始化完成: {rag_status}")
except Exception as e:
    logger.error(f"RAG管道初始化失败: {e}", exc_info=True)
    rag_pipeline = None

# 初始化多Agent系统
agent_coordinator = None
def get_multi_agent_coordinator():
    global agent_coordinator
    if agent_coordinator is None:
        if rag_pipeline is None:
            logger.error("无法创建Agent协调器：RAG管道未初始化")
            raise RuntimeError("RAG管道未初始化，无法创建Agent协调器")
        agent_coordinator = get_agent_coordinator(rag_pipeline)
        logger.info("Agent协调器初始化成功")
    return agent_coordinator

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# 配置日志
logger = logging.getLogger(__name__)

# 处理流式响应的函数
async def handle_stream_response(
    manager: "ConnectionManager",
    session_id: str,
    user_id: str,
    user_input: str,
    agent_coordinator,
    response_metadata: dict,
    ai_timestamp: datetime,
    logger_manager,
    prometheus_metrics,
    trace_id: str
):
    """处理多Agent系统的流式响应 - 真正的并行流式输出"""
    stream_start_time = time.time()
    stream_id = str(uuid.uuid4())
    
    # 数据库操作相关变量
    total_content = ""
    chunk_index = 0
    
    try:
        # 记录流式响应开始（仅开发环境）
        if os.getenv('NODE_ENV') != 'production':
            await logger_manager.log_system_event(
                event_type="STREAM_RESPONSE_START",
                message=f"用户 {user_id} 开始流式响应",
                details={
                    "session_id": session_id,
                    "user_id": user_id,
                    "user_input": user_input,
                    "stream_id": stream_id
                },
                trace_id=trace_id
            )
        
        # 发送流式响应开始消息
        await manager.send_personal_message(
            json.dumps({
                "type": "stream_start",
                "stream_id": stream_id,
                "timestamp": ai_timestamp.isoformat(),
                "metadata": response_metadata
            }),
            session_id
        )
        
        # 初始化保存任务相关变量
        background_save_task = None
        save_started = False
        
        # 获取多agent系统的流式响应 - 真正的流式输出
        stream_iter = agent_coordinator.stream_response(user_input, session_id, trace_id)
        
        # 尝试获取第一个chunk来判断是否为完整答案（缓存命中）
        try:
            first_chunk = await stream_iter.__anext__()
            
            # 如果第一个chunk就是完整答案（缓存命中），直接返回
            if len(first_chunk) > 50 and not first_chunk.startswith("我正在为您处理") and not first_chunk.startswith("正在查询"):
                logger.info(f"检测到缓存命中，直接返回完整答案: {first_chunk[:50]}...")
                
                # 直接发送完整答案
                await manager.send_personal_message(
                    json.dumps({
                        "type": "response", 
                        "content": first_chunk, 
                        "sender": "assistant", 
                        "timestamp": ai_timestamp.isoformat(),
                        "metadata": response_metadata
                    }),
                    session_id
                )
                
                # 缓存命中的答案不需要保存到数据库和Redis
                stream_duration = time.time() - stream_start_time
                logging.debug(f"缓存命中直接返回: 用户 {user_id}, stream_id: {stream_id}, 耗时: {stream_duration:.3f}s")
                return
            else:
                # 正常流式输出
                chunk_index += 1
                total_content += first_chunk
                
                # 发送第一个流式消息块
                stream_message = {
                    "type": "stream_message",
                    "stream_id": stream_id,
                    "content": first_chunk,
                    "chunk_index": chunk_index,
                    "is_final": False,
                    "timestamp": ai_timestamp.isoformat()
                }
                
                await manager.send_personal_message(
                    json.dumps(stream_message),
                    session_id
                )
                
                # 继续处理剩余的流式输出
                async for chunk in stream_iter:
                    chunk_index += 1
                    total_content += chunk
                    
                    # 发送流式消息块 - 立即输出给前端
                    stream_message = {
                        "type": "stream_message",
                        "stream_id": stream_id,
                        "content": chunk,
                        "chunk_index": chunk_index,
                        "is_final": False,
                        "timestamp": ai_timestamp.isoformat()
                    }
                    
                    await manager.send_personal_message(
                        json.dumps(stream_message),
                        session_id
                    )
                    
                    # 控制流式输出速度，避免过载
                    await asyncio.sleep(0.05)
                    
        except StopAsyncIteration:
            # 如果没有生成任何内容
            logger.warning(f"流式响应没有生成内容: 用户 {user_id}, stream_id: {stream_id}")
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "stream_id": stream_id,
                    "message": "抱歉，暂时无法生成回答，请稍后再试。",
                    "timestamp": datetime.now().isoformat()
                }),
                session_id
            )
            return
        
        # 等待后台保存任务完成（如果还没完成的话）
        if background_save_task:
            try:
                await background_save_task
                logging.debug(f"后台保存任务完成: 用户 {user_id}, stream_id: {stream_id}")
            except Exception as save_error:
                logging.error(f"后台保存任务失败: {save_error}")
        
        # 检查是否有引用信息
        has_references = False
        references = []
        if "参考" in total_content or "reference" in total_content.lower():
            has_references = True
            # 这里可以根据实际需求提取引用信息
            references = []
        
        # 发送流式响应完成消息 - 立即发送，不等待任何操作
        final_message = {
            "type": "stream_end",
            "stream_id": stream_id,
            "content": total_content,
            "chunk_index": chunk_index,
            "total_chunks": chunk_index,
            "is_final": True,
            "has_references": has_references,
            "references": references,
            "timestamp": ai_timestamp.isoformat(),
            "metadata": response_metadata
        }
        
        await manager.send_personal_message(
            json.dumps(final_message),
            session_id
        )
        
        # 记录流式响应完成（仅开发环境）
        stream_duration = time.time() - stream_start_time
        if os.getenv('NODE_ENV') != 'production':
            await logger_manager.log_performance('stream_response_complete', stream_duration, {
                'session_id': session_id,
                'user_id': user_id,
                'stream_id': stream_id,
                'total_chunks': chunk_index,
                'content_length': len(total_content)
            })
        
        # 如果还没有启动后台保存任务，则在这里执行
        if not save_started:
            try:
                await _background_save_ai_response(
                    user_id=user_id,
                    session_id=session_id,
                    user_input=user_input,
                    total_content=total_content,
                    response_metadata=response_metadata,
                    logger_manager=logger_manager,
                    prometheus_metrics=prometheus_metrics
                )
            except Exception as save_error:
                logging.error(f"最终保存操作失败: {save_error}")
        
        logging.debug(f"流式响应完成: 用户 {user_id}, stream_id: {stream_id}, 耗时: {stream_duration:.3f}s, 块数: {chunk_index}")
        
    except Exception as e:
        stream_duration = time.time() - stream_start_time
        
        # 记录流式响应失败
        await logger_manager.log_error('stream_response_error', str(e), {
            'session_id': session_id,
            'user_id': user_id,
            'stream_id': stream_id,
            'duration': stream_duration
        }, trace_id=trace_id)
        
        # 记录流式响应失败指标
        prometheus_metrics.record_chat_event('stream_response_failed', session_id=session_id, user_id=user_id)
        
        logging.error(f"流式响应处理失败: {e}")
        
        # 发送错误消息
        try:
            await manager.send_personal_message(
                json.dumps({
                    "type": "error",
                    "stream_id": stream_id,
                    "message": "抱歉，生成流式回答时出现错误，请稍后再试。",
                    "timestamp": datetime.now().isoformat()
                }),
                session_id
            )
        except Exception as send_error:
            logging.error(f"发送流式错误消息失败: {send_error}")


async def _background_save_ai_response(
    user_id: str,
    session_id: str,
    user_input: str,
    total_content: str,
    response_metadata: dict,
    logger_manager,
    prometheus_metrics
):
    """后台保存AI回复到数据库和缓存（并行执行）"""
    try:
        # 并行执行数据库保存和缓存操作
        save_tasks = []
        
        # 1. 保存到数据库
        try:
            from app.services.tools.database_tool import DatabaseTool
            db_tool = DatabaseTool()
            save_tasks.append(
                db_tool.save_ai_response(
                    user_id=user_id,
                    session_id=session_id,
                    user_message=user_input,
                    ai_message=total_content,
                    metadata=response_metadata
                )
            )
        except Exception as db_error:
            logging.error(f"准备数据库保存任务失败: {db_error}")
        
        # 2. 保存到Redis缓存（如果有相关内容）
        try:
            if redis_manager and len(total_content) > 50:  # 只缓存较长的回复
                # 这里可以添加缓存逻辑，类似于多Agent系统中的缓存逻辑
                save_tasks.append(
                    redis_manager.cache_response(user_input, total_content, ttl=300)
                )
        except Exception as cache_error:
            logging.error(f"准备缓存保存任务失败: {cache_error}")
        
        # 并行执行所有保存任务
        if save_tasks:
            await asyncio.gather(*save_tasks, return_exceptions=True)
            
            # 记录成功的数据库操作
            if prometheus_metrics:
                prometheus_metrics.record_db_operation('save_ai_response', 'chat_messages', 0.1)
        
    except Exception as e:
        logging.error(f"后台保存AI回复失败: {e}")
        
        # 记录失败指标
        if prometheus_metrics:
            prometheus_metrics.record_db_operation('save_ai_response', 'chat_messages', 0.1)

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_users: Dict[str, str] = {}  # session_id -> user_id
    
    async def connect(self, websocket: WebSocket, user_id: str, session_id: Optional[str] = None):
        """建立WebSocket连接"""
        start_time = time.time()
        
        try:
            await websocket.accept()
            
            if not session_id:
                session_id = str(uuid.uuid4())
            
            self.active_connections[session_id] = websocket
            self.user_sessions[user_id] = session_id
            self.session_users[session_id] = user_id
            
            connection_duration = time.time() - start_time
            
            # 记录系统日志（仅开发环境）
            if os.getenv('NODE_ENV') != 'production':
                await logger_manager.log_system_event(
                    event_type="WEBSOCKET_CONNECT",
                    message=f"用户 {user_id} 建立连接",
                    details={"session_id": session_id, "user_id": user_id, "connection_duration": connection_duration}
                )
            
            logging.info(f"用户 {user_id} 建立连接，session_id: {session_id}，耗时: {connection_duration:.3f}s")
            return session_id
            
        except Exception as e:
            connection_duration = time.time() - start_time
            
            # 记录WebSocket连接失败
            await logger_manager.log_error('websocket_connect_error', str(e), 
                                         {'user_id': user_id, 'session_id': session_id, 'duration': connection_duration}, 
                                         trace_id=str(uuid.uuid4()))
            
            # 记录WebSocket连接失败指标
            prometheus_metrics.record_websocket_event('connection_failed')
            
            logging.error(f"用户 {user_id} 建立连接失败: {e}")
            raise
    
    def disconnect(self, session_id: str):
        """断开WebSocket连接"""
        start_time = time.time()
        user_id = self.session_users.get(session_id)
        
        try:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            if user_id in self.user_sessions and self.user_sessions[user_id] == session_id:
                del self.user_sessions[user_id]
            if session_id in self.session_users:
                del self.session_users[session_id]
            
            disconnect_duration = time.time() - start_time
            
            if user_id:
                # 记录系统日志（仅开发环境）
                if os.getenv('NODE_ENV') != 'production':
                    logger_manager.log_system_event_sync(
                        event_type="WEBSOCKET_DISCONNECT",
                        message=f"用户 {user_id} 断开连接",
                        details={"session_id": session_id, "user_id": user_id, "disconnect_duration": disconnect_duration}
                    )
                
                logging.info(f"用户 {user_id} 断开连接，session_id: {session_id}，耗时: {disconnect_duration:.3f}s")
            
        except Exception as e:
            disconnect_duration = time.time() - start_time
            
            # 记录断开连接失败
            logger_manager.log_error_sync('websocket_disconnect_error', str(e), 
                                        {'user_id': user_id, 'session_id': session_id, 'duration': disconnect_duration})
            
            logging.error(f"用户 {user_id} 断开连接失败: {e}")
    
    async def send_personal_message(self, message: str, session_id: str):
        """发送个人消息"""
        start_time = time.time()
        user_id = self.session_users.get(session_id)
        
        try:
            if session_id in self.active_connections:
                send_duration = time.time() - start_time
                
                await self.active_connections[session_id].send_text(message)
                
                final_duration = time.time() - start_time
                
                # 记录消息发送成功（仅开发环境）
            if os.getenv('NODE_ENV') != 'production':
                await logger_manager.log_chat_event(
                    event_type="MESSAGE_SENT",
                    session_id=session_id,
                    user_id=user_id,
                    message_content=message[:100],  # 只记录前100个字符，避免日志过大
                    duration=final_duration,
                    trace_id=str(uuid.uuid4())
                )
                
                logging.debug(f"发送消息成功: {session_id}，耗时: {final_duration:.3f}s")
            else:
                # 记录消息发送失败 - 连接不存在
                await logger_manager.log_error('websocket_send_message_error', 'Connection not found', 
                                             {'session_id': session_id, 'user_id': user_id, 'duration': time.time() - start_time}, 
                                             trace_id=str(uuid.uuid4()))
                
                # 记录消息发送失败指标
                prometheus_metrics.record_chat_event('message_send_failed', session_id=session_id, user_id=user_id)
                
                logging.warning(f"发送消息失败: 连接不存在 {session_id}")
                
        except Exception as e:
            final_duration = time.time() - start_time
            
            # 记录消息发送异常
            await logger_manager.log_error('websocket_send_message_error', str(e), 
                                         {'session_id': session_id, 'user_id': user_id, 'duration': final_duration}, 
                                         trace_id=str(uuid.uuid4()))
            
            # 记录消息发送失败指标
            prometheus_metrics.record_chat_event('message_send_failed', session_id=session_id, user_id=user_id)
            
            logging.error(f"发送消息失败: {e}")
            self.disconnect(session_id)
    
    def get_session_user(self, session_id: str) -> Optional[str]:
        """获取会话对应的用户ID"""
        return self.session_users.get(session_id)

manager = ConnectionManager()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, user_id: str = Depends(verify_token)):
    """HTTP聊天接口"""
    start_time = time.time()
    
    try:
        
        user_message = request.message.strip()
        
        if not user_message:
            # 记录无效请求
            await logger_manager.log_auth_event('http_chat_invalid_request', username=user_id, success=False,
                                              details={'reason': 'empty_message', 'duration': time.time() - start_time})
            
            prometheus_metrics.record_chat_event('http_chat_invalid_request', user_id=user_id)
            
            raise HTTPException(status_code=400, detail="消息内容不能为空")
        
        # 记录HTTP聊天请求开始
        trace_id = str(uuid.uuid4())
        await logger_manager.log_chat_event(
            event_type="HTTP_CHAT_REQUEST",
            session_id=None,
            user_id=user_id,
            message_content=user_message[:100],
            duration=0,
            trace_id=trace_id
        )
        
        prometheus_metrics.record_chat_event('http_chat_request', user_id=user_id)
        prometheus_metrics.record_chat_message_size(len(user_message))
        
        # 创建或获取会话ID
        session_id = str(uuid.uuid4())
        
        # 使用多Agent系统生成回复
        agent_coordinator = get_multi_agent_coordinator()
        ai_response = await agent_coordinator.process_message(user_message, session_id, trace_id)
        ai_response = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
        has_knowledge = True  # 假设agent_coordinator总是能处理
        references = []  # agent_coordinator可能不提供references
        processing_time = time.time() - start_time
        
        duration = time.time() - start_time
        
        # 记录HTTP聊天响应
        await logger_manager.log_chat_event(
            event_type="HTTP_CHAT_RESPONSE",
            session_id=session_id,
            user_id=user_id,
            message_content=ai_response[:100],
            duration=duration,
            trace_id=trace_id
        )
        
        # 记录性能日志
        await logger_manager.log_performance('http_chat', duration, 
                                           {'user_id': user_id, 'message_length': len(user_message), 'response_length': len(ai_response)}, 
                                           trace_id=trace_id)
        
        # 记录聊天响应指标
        prometheus_metrics.record_chat_event('http_chat_response', user_id=user_id)
        prometheus_metrics.record_rag_query(duration, len(references), has_knowledge)
        
        return ChatResponse(
            response=ai_response,
            session_id=session_id,
            timestamp=datetime.now()
        )
        
    except HTTPException:
        duration = time.time() - start_time
        
        # 记录HTTP聊天失败
        await logger_manager.log_chat_event(
            event_type="HTTP_CHAT_FAILED",
            session_id=None,
            user_id=user_id,
            message_content=request.message[:100] if request.message else '',
            duration=duration,
            trace_id=trace_id
        )
        
        prometheus_metrics.record_chat_event('http_chat_failed', user_id=user_id)
        await logger_manager.log_performance('http_chat', duration, {'user_id': user_id, 'status': 'failed'}, trace_id=trace_id)
        
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录HTTP聊天异常
        await logger_manager.log_error('http_chat_error', str(e), 
                                     {'user_id': user_id, 'duration': duration}, 
                                     trace_id=trace_id)
        
        prometheus_metrics.record_chat_event('http_chat_error', user_id=user_id)
        await logger_manager.log_performance('http_chat', duration, {'user_id': user_id, 'status': 'error'}, trace_id=trace_id)
        
        logging.error(f"处理聊天请求时发生错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket聊天端点"""
    session_id = None
    user_id = None
    
    try:
        # 添加调试日志
        logging.info(f"WebSocket连接请求，query_params: {dict(websocket.query_params)}")
        
        # 验证token
        token = websocket.query_params.get("token")
        if not token:
            logging.warning("WebSocket连接失败：缺少token")
            await websocket.close(code=4001, reason="缺少认证token")
            return
        
        logging.info(f"收到token: {token[:20]}...")
        
        # 验证用户身份 - 使用与HTTP API一致的验证方式
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            logging.info(f"JWT payload解码成功: {payload}")
            
            # 检查令牌类型
            token_type = payload.get("type")
            if token_type != "access":
                logging.warning(f"无效的令牌类型: {token_type}")
                await websocket.close(code=4003, reason="无效的令牌类型")
                return
            
            # 检查黑名单 - 临时禁用黑名单检查
            # token_jti = payload.get("jti")
            # if token_jti and await is_token_blacklisted(token_jti):
            #     await websocket.close(code=4004, reason="令牌已被撤销")
            #     return
            
            user_id = payload.get("sub")
            if not user_id:
                logging.warning("JWT payload中没有sub字段")
                await websocket.close(code=4002, reason="无效的token")
                return
                
        except jwt.PyJWTError as e:
            logging.error(f"JWT解码失败: {e}")
            await websocket.close(code=4002, reason="无效的token")
            return
        
        logging.info(f"Token验证成功，用户ID: {user_id}")
        
        # 从查询参数获取session_id（如果支持断线重连）
        existing_session_id = websocket.query_params.get("session_id")
        
        # 建立WebSocket连接
        session_id = await manager.connect(websocket, user_id, existing_session_id)
        
        # 创建或更新会话记录
        session_start_time = time.time()
        try:
            await mysql_manager.create_session_if_not_exists(session_id, user_id)
            session_duration = time.time() - session_start_time
            
            # 记录会话创建日志
            await logger_manager.log_chat_event(
                event_type="SESSION_CREATED",
                session_id=session_id,
                user_id=user_id,
                message_content="WebSocket session created",
                duration=session_duration
            )
            
            # 记录会话创建指标
            prometheus_metrics.record_chat_event('session_created', session_id=session_id, user_id=user_id)
            prometheus_metrics.record_db_operation('session_create', True, session_duration)
            
            logging.info(f"会话记录创建成功: {session_id}，耗时: {session_duration:.3f}s")
            
        except Exception as e:
            session_duration = time.time() - session_start_time
            
            # 记录会话创建失败
            await logger_manager.log_error('session_creation_error', str(e), 
                                         {'session_id': session_id, 'user_id': user_id, 'duration': session_duration})
            
            # 记录会话创建失败指标
            prometheus_metrics.record_chat_event('session_creation_failed', session_id=session_id, user_id=user_id)
            prometheus_metrics.record_db_operation('session_create', False, session_duration)
            
            logging.error(f"创建会话记录失败: {e}")
        
        # 发送连接成功消息
        connect_send_start = time.time()
        try:
            await manager.send_personal_message(
                json.dumps({
                    "type": "connected", 
                    "message": "连接成功", 
                    "session_id": session_id, 
                    "timestamp": datetime.now().isoformat()
                }),
                session_id
            )
            
            connect_send_duration = time.time() - connect_send_start
            
            # 记录连接确认消息发送
            await logger_manager.log_chat_event(
                event_type="CONNECTION_CONFIRMATION_SENT",
                session_id=session_id,
                user_id=user_id,
                message_content="Connection successful",
                duration=connect_send_duration
            )
            
        except Exception as e:
            connect_send_duration = time.time() - connect_send_start
            
            await logger_manager.log_error('connection_confirmation_send_error', str(e), 
                                         {'session_id': session_id, 'user_id': user_id, 'duration': connect_send_duration})
            
            logging.error(f"发送连接确认消息失败: {e}")
        
        # 接收和处理消息
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            
            try:
                # 解析消息
                message_data = json.loads(data)
                
                if message_data.get("type") == "message":
                    user_message = message_data.get("content", "").strip()
                    
                    if user_message:
                        current_timestamp = datetime.now()
                        message_process_start = time.time()
                        
                        # 记录用户消息接收
                        await logger_manager.log_chat_event(
                            event_type="USER_MESSAGE_RECEIVED",
                            session_id=session_id,
                            user_id=user_id,
                            message_content=user_message[:100],
                            duration=0
                        )
                        
                        # 记录用户消息接收指标
                        prometheus_metrics.record_chat_event('user_message_received', session_id=session_id, user_id=user_id)
                        prometheus_metrics.record_chat_message_size(len(user_message))
                        
                        # 使用Redis缓存会话历史，提高性能
                        redis_cache_start = time.time()
                        redis_success = False
                        try:
                            redis_success = await redis_manager.add_message_to_session(
                                session_id=session_id,
                                role="user",
                                content=user_message,
                                user_id=user_id
                            )
                            redis_cache_duration = time.time() - redis_cache_start
                            
                            if redis_success:
                                logging.info(f"用户消息已缓存到Redis: {session_id}")
                                
                                # 记录Redis缓存成功（仅开发环境）
                                if os.getenv('NODE_ENV') != 'production':
                                    await logger_manager.log_performance('redis_cache_user_message', redis_cache_duration, 
                                                                       {'session_id': session_id, 'user_id': user_id, 'message_length': len(user_message)})
                            else:
                                logging.warning(f"Redis缓存失败，但继续处理消息: {session_id}")
                                
                                # 记录Redis缓存失败
                                await logger_manager.log_chat_event(
                                    event_type="REDIS_CACHE_FAILED",
                                    session_id=session_id,
                                    user_id=user_id,
                                    message_content="Redis cache failed for user message",
                                    duration=redis_cache_duration
                                )
                                
                                # 记录Redis操作失败指标
                                prometheus_metrics.record_redis_operation('cache_user_message', False, redis_cache_duration)
                                
                        except Exception as e:
                            redis_cache_duration = time.time() - redis_cache_start
                            
                            # 记录Redis缓存异常
                            await logger_manager.log_error('redis_cache_user_message_error', str(e), 
                                                         {'session_id': session_id, 'user_id': user_id, 'duration': redis_cache_duration})
                            
                            # 记录Redis操作异常指标
                            prometheus_metrics.record_redis_operation('cache_user_message', False, redis_cache_duration)
                            
                            logging.error(f"Redis缓存用户消息失败: {e}")
                        # Redis缓存失败不应影响正常处理，继续保存到数据库
                        
                        # 保存用户消息到数据库（持久化存储）
                        db_save_start = time.time()
                        try:
                            await mysql_manager.save_message(
                                session_id=session_id,
                                user_id=user_id,
                                role="user",
                                content=user_message,
                                metadata={
                                    "message_type": "websocket",
                                    "client_info": message_data.get("client_info", {}),
                                    "timestamp": current_timestamp.isoformat(),
                                    "redis_cached": redis_success
                                }
                            )
                            
                            db_save_duration = time.time() - db_save_start
                            logging.info(f"用户消息已保存到数据库: {session_id}")
                            
                            # 记录数据库保存成功（仅开发环境）
                            if os.getenv('NODE_ENV') != 'production':
                                await logger_manager.log_performance('db_save_user_message', db_save_duration, 
                                                                   {'session_id': session_id, 'user_id': user_id, 'message_length': len(user_message)})
                            
                        except Exception as e:
                            db_save_duration = time.time() - db_save_start
                            
                            # 记录数据库保存失败
                            await logger_manager.log_error('db_save_user_message_error', str(e), 
                                                         {'session_id': session_id, 'user_id': user_id, 'duration': db_save_duration})
                            
                            # 记录数据库操作失败指标
                            prometheus_metrics.record_db_operation('save_user_message', False, db_save_duration)
                            
                            logging.error(f"保存用户消息失败: {e}")
                        
                        # 发送用户消息确认
                        confirm_send_start = time.time()
                        try:
                            await manager.send_personal_message(
                                json.dumps({
                                    "type": "message", 
                                    "content": user_message, 
                                    "sender": "user", 
                                    "timestamp": current_timestamp.isoformat()
                                }),
                                session_id
                            )
                            
                            confirm_send_duration = time.time() - confirm_send_start
                            
                            # 记录用户消息确认发送（仅开发环境）
                            if os.getenv('NODE_ENV') != 'production':
                                await logger_manager.log_performance('send_user_message_confirmation', confirm_send_duration, 
                                                                   {'session_id': session_id, 'user_id': user_id})
                            
                        except Exception as e:
                            confirm_send_duration = time.time() - confirm_send_start
                            
                            await logger_manager.log_error('send_user_message_confirmation_error', str(e), 
                                                         {'session_id': session_id, 'user_id': user_id, 'duration': confirm_send_duration})
                            
                            logging.error(f"发送用户消息确认失败: {e}")
                            
                        # 记录整个消息处理的总耗时（仅开发环境）
                        if os.getenv('NODE_ENV') != 'production':
                            total_message_duration = time.time() - message_process_start
                            await logger_manager.log_performance('total_user_message_processing', total_message_duration, 
                                                               {'session_id': session_id, 'user_id': user_id, 'message_length': len(user_message)})
                        
                        # 使用多Agent系统生成AI回复（支持流式输出）
                        ai_generation_start = time.time()
                        try:
                            # 检查是否启用多Agent模式
                            enable_multi_agent = message_data.get("enable_multi_agent", True)
                            
                            # 初始化context_messages，确保在所有路径中都可用
                            context_messages = []
                            
                            if enable_multi_agent:
                                # 获取会话消息以构建上下文
                                context_fetch_start = time.time()
                                session_messages = await redis_manager.get_session_messages(session_id)
                                context_fetch_duration = time.time() - context_fetch_start
                                
                                # 构建上下文消息
                                for msg in session_messages:
                                    context_messages.append(f"{msg['role']}: {msg['content']}")
                                
                                # 将当前用户消息也加入上下文
                                context_messages.append(f"user: {user_message}")
                                
                                # 使用流式输出模式
                                trace_id = str(uuid.uuid4())
                                await handle_stream_response(
                                    manager=manager,
                                    session_id=session_id,
                                    user_id=user_id,
                                    user_input=user_message,
                                    agent_coordinator=get_multi_agent_coordinator(),
                                    response_metadata={"intent": "multi_agent"},
                                    ai_timestamp=current_timestamp,
                                    logger_manager=logger_manager,
                                    prometheus_metrics=prometheus_metrics,
                                    trace_id=trace_id
                                )
                                
                                # 流式输出处理完成后，继续处理下一个消息
                                continue
                            else:
                                # 传统RAG方式生成回复（保持向后兼容）
                                context_fetch_start = time.time()
                                session_messages = await redis_manager.get_session_messages(session_id)
                                context_fetch_duration = time.time() - context_fetch_start
                                
                                # 构建上下文消息
                                for msg in session_messages:
                                    context_messages.append(f"{msg['role']}: {msg['content']}")
                                
                                # 将当前用户消息也加入上下文
                                context_messages.append(f"user: {user_message}")
                                
                                # 如果有上下文信息，传递给聊天服务
                                context = "\n".join(context_messages[-10:]) if context_messages else user_message  # 只取最近10条消息
                                
                                # 记录上下文获取
                                await logger_manager.log_chat_event(
                                    event_type="CONTEXT_FETCHED",
                                    session_id=session_id,
                                    user_id=user_id,
                                    message_content=f"Context length: {len(context_messages)}",
                                    duration=context_fetch_duration
                                )
                                
                                # 记录上下文获取指标
                                prometheus_metrics.record_redis_operation('get_session_messages', True, context_fetch_duration)
                                prometheus_metrics.record_chat_event('context_fetched', session_id=session_id, user_id=user_id)
                                
                                # 使用多Agent系统生成回复
                                ai_response_generation_start = time.time()
                                agent_coordinator = get_multi_agent_coordinator()
                                ai_response = await agent_coordinator.process_message(user_message, session_id)
                                ai_response = ai_response.content if hasattr(ai_response, 'content') else str(ai_response)
                                has_knowledge = True  # 假设agent_coordinator总是能处理
                                references = []  # agent_coordinator可能不提供references
                                ai_response_duration = time.time() - ai_response_generation_start
                                
                                # 记录AI回复生成
                                await logger_manager.log_chat_event(
                                    event_type="AI_RESPONSE_GENERATED",
                                    session_id=session_id,
                                    user_id=user_id,
                                    message_content=ai_response[:100],
                                    duration=ai_response_duration
                                )
                                
                                # 记录RAG查询指标
                                prometheus_metrics.record_rag_query(
                                    ai_response_duration, 
                                    len(references), 
                                    has_knowledge
                                )
                                prometheus_metrics.record_chat_event('ai_response_generated', session_id=session_id, user_id=user_id)
                                
                                logging.debug(f"AI回复生成成功: {session_id}，耗时: {ai_response_duration:.3f}s")
                                
                                response_metadata = {
                                    "has_knowledge": has_knowledge,
                                    "sources_count": len(references),
                                    "success": True
                                }
                            
                            # 缓存AI回复到Redis
                            ai_redis_cache_start = time.time()
                            try:
                                redis_ai_success = await redis_manager.add_message_to_session(
                                    session_id=session_id,
                                    role="assistant",
                                    content=ai_response,
                                    user_id=user_id
                                )
                                
                                ai_redis_cache_duration = time.time() - ai_redis_cache_start
                                
                                if redis_ai_success:
                                    logging.info(f"AI回复已缓存到Redis: {session_id}")
                                    
                                    # 记录AI回复Redis缓存成功
                                    await logger_manager.log_performance('redis_cache_ai_response', ai_redis_cache_duration, 
                                                                       {'session_id': session_id, 'user_id': user_id, 'response_length': len(ai_response)})
                                    
                                    # 记录Redis操作指标
                                    prometheus_metrics.record_redis_operation('cache_ai_response', True, ai_redis_cache_duration)
                                    
                                else:
                                    logging.warning(f"Redis缓存AI回复失败: {session_id}")
                                    
                                    # 记录Redis缓存失败
                                    await logger_manager.log_chat_event(
                                        event_type="AI_RESPONSE_REDIS_CACHE_FAILED",
                                        session_id=session_id,
                                        user_id=user_id,
                                        message_content="Redis cache failed for AI response",
                                        duration=ai_redis_cache_duration
                                    )
                                    
                                    # 记录Redis操作失败指标
                                    prometheus_metrics.record_redis_operation('cache_ai_response', False, ai_redis_cache_duration)
                                    
                            except Exception as e:
                                ai_redis_cache_duration = time.time() - ai_redis_cache_start
                                
                                # 记录Redis缓存AI回复异常
                                await logger_manager.log_error('redis_cache_ai_response_error', str(e), 
                                                             {'session_id': session_id, 'user_id': user_id, 'duration': ai_redis_cache_duration})
                                
                                # 记录Redis操作异常指标
                                prometheus_metrics.record_redis_operation('cache_ai_response', False, ai_redis_cache_duration)
                                
                                logging.error(f"Redis缓存AI回复失败: {e}")
                            
                            # 保存AI回复到数据库（持久化存储）
                            ai_db_save_start = time.time()
                            ai_timestamp = datetime.now()
                            try:
                                await mysql_manager.save_message(
                                    session_id=session_id,
                                    user_id=user_id,
                                    role="assistant",
                                    content=ai_response,
                                    metadata={
                                        "message_type": "websocket",
                                        "model": "default",
                                        "context_length": len(context_messages),
                                        "timestamp": ai_timestamp.isoformat(),
                                        "ai_response_duration": ai_response_duration,
                                        "redis_cached": redis_ai_success if 'redis_ai_success' in locals() else False
                                    }
                                )
                                
                                ai_db_save_duration = time.time() - ai_db_save_start
                                logging.info(f"AI回复已保存到数据库: {session_id}")
                                
                                # 记录AI回复数据库保存成功
                                await logger_manager.log_performance('db_save_ai_response', ai_db_save_duration, 
                                                                   {'session_id': session_id, 'user_id': user_id, 'response_length': len(ai_response)})
                                
                                # 记录数据库操作指标
                                prometheus_metrics.record_db_operation('save_ai_response', True, ai_db_save_duration)
                                
                            except Exception as e:
                                ai_db_save_duration = time.time() - ai_db_save_start
                                
                                # 记录AI回复数据库保存失败
                                await logger_manager.log_error('db_save_ai_response_error', str(e), 
                                                             {'session_id': session_id, 'user_id': user_id, 'duration': ai_db_save_duration})
                                
                                # 记录数据库操作失败指标
                                prometheus_metrics.record_db_operation('save_ai_response', False, ai_db_save_duration)
                                
                                logging.error(f"保存AI回复失败: {e}")
                            
                            # 检查是否启用流式输出
                            stream_response = message_data.get("stream", True)
                            
                            if stream_response and enable_multi_agent:
                                # 流式输出模式
                                await handle_stream_response(
                                    manager=manager,
                                    session_id=session_id,
                                    user_id=user_id,
                                    user_input=user_message,
                                    agent_coordinator=get_multi_agent_coordinator(),
                                    response_metadata=response_metadata,
                                    ai_timestamp=ai_timestamp,
                                    logger_manager=logger_manager,
                                    prometheus_metrics=prometheus_metrics
                                )
                            else:
                                # 传统一次性输出模式
                                ai_send_start = time.time()
                                try:
                                    await manager.send_personal_message(
                                        json.dumps({
                                            "type": "response", 
                                            "content": ai_response, 
                                            "sender": "assistant", 
                                            "timestamp": ai_timestamp.isoformat(),
                                            "metadata": response_metadata
                                        }),
                                        session_id
                                    )
                                    
                                    ai_send_duration = time.time() - ai_send_start
                                    
                                    # 记录AI回复发送
                                    await logger_manager.log_performance('send_ai_response', ai_send_duration, 
                                                                       {'session_id': session_id, 'user_id': user_id, 'response_length': len(ai_response)})
                                    
                                    # 记录AI回复发送指标
                                    prometheus_metrics.record_chat_event('ai_response_sent', session_id=session_id, user_id=user_id)
                                    
                                except Exception as e:
                                    ai_send_duration = time.time() - ai_send_start
                                    
                                    await logger_manager.log_error('send_ai_response_error', str(e), 
                                                                 {'session_id': session_id, 'user_id': user_id, 'duration': ai_send_duration})
                                    
                                    logging.error(f"发送AI回复失败: {e}")
                            
                            # 记录整个AI回复处理的总耗时
                            total_ai_duration = time.time() - ai_generation_start
                            # 安全地获取context_messages长度，如果未定义则使用默认值
                            context_length = len(context_messages) if 'context_messages' in locals() else 0
                            await logger_manager.log_performance('total_ai_response_processing', total_ai_duration, 
                                                               {'session_id': session_id, 'user_id': user_id, 'response_length': len(ai_response), 'context_length': context_length})
                            
                        except Exception as e:
                            ai_generation_duration = time.time() - ai_generation_start
                            
                            # 记录AI回复生成失败
                            await logger_manager.log_error('ai_response_generation_error', str(e), 
                                                         {'session_id': session_id, 'user_id': user_id, 'duration': ai_generation_duration})
                            
                            # 记录AI回复生成失败指标
                            prometheus_metrics.record_chat_event('ai_response_generation_failed', session_id=session_id, user_id=user_id)
                            # 使用正确的RAG查询记录方法，设置合理的默认值
                            prometheus_metrics.record_rag_query(ai_generation_duration, 0, False)
                            
                            logging.error(f"生成AI回复失败: {e}")
                            
                            # 发送错误消息给用户
                            error_send_start = time.time()
                            try:
                                await manager.send_personal_message(
                                    json.dumps({
                                        "type": "error", 
                                        "message": "抱歉，处理您的问题时出现了错误，请稍后再试。",
                                        "timestamp": datetime.now().isoformat()
                                    }),
                                    session_id
                                )
                                
                                error_send_duration = time.time() - error_send_start
                                
                                await logger_manager.log_performance('send_error_message', error_send_duration, 
                                                                   {'session_id': session_id, 'user_id': user_id})
                                
                            except Exception as send_error:
                                error_send_duration = time.time() - error_send_start
                                
                                await logger_manager.log_error('send_error_message_failed', str(send_error), 
                                                             {'session_id': session_id, 'user_id': user_id, 'duration': error_send_duration})
                                
                                logging.error(f"发送错误消息失败: {send_error}")
                
                elif message_data.get("type") == "ping":
                    # 处理心跳检测
                    ping_start = time.time()
                    try:
                        await manager.send_personal_message(
                            json.dumps({
                                "type": "pong", 
                                "timestamp": datetime.now().isoformat()
                            }),
                            session_id
                        )
                        
                        ping_duration = time.time() - ping_start
                        
                        # 记录心跳响应
                        await logger_manager.log_chat_event(
                            event_type="PING_RESPONSE_SENT",
                            session_id=session_id,
                            user_id=user_id,
                            message_content="pong response",
                            duration=ping_duration
                        )
                        
                        # 记录心跳指标
                        prometheus_metrics.record_chat_event('ping_response_sent', session_id=session_id, user_id=user_id)
                        
                        logging.debug(f"心跳响应发送成功: {session_id}，耗时: {ping_duration:.3f}s")
                        
                    except Exception as e:
                        ping_duration = time.time() - ping_start
                        
                        await logger_manager.log_error('ping_response_error', str(e), 
                                                     {'session_id': session_id, 'user_id': user_id, 'duration': ping_duration})
                        
                        prometheus_metrics.record_chat_event('ping_response_failed', session_id=session_id, user_id=user_id)
                        
                        logging.error(f"心跳响应发送失败: {e}")
                        
            except json.JSONDecodeError:
                # 记录消息格式错误
                await logger_manager.log_chat_event(
                    event_type="MESSAGE_PARSE_ERROR",
                    session_id=session_id,
                    user_id=user_id,
                    message_content="Invalid JSON message format",
                    duration=0
                )
                
                # 记录消息解析错误指标
                prometheus_metrics.record_chat_event('message_parse_error', session_id=session_id, user_id=user_id)
                
                logging.warning(f"消息格式错误: {session_id}")
                
                try:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error", 
                            "message": "消息格式错误",
                            "timestamp": datetime.now().isoformat()
                        }),
                        session_id
                    )
                except Exception as send_error:
                    await logger_manager.log_error('send_parse_error_message_failed', str(send_error), 
                                                 {'session_id': session_id, 'user_id': user_id})
                    logging.error(f"发送格式错误消息失败: {send_error}")
                    
            except Exception as e:
                # 记录消息处理异常
                await logger_manager.log_error('message_processing_error', str(e), 
                                             {'session_id': session_id, 'user_id': user_id})
                
                # 记录消息处理失败指标
                prometheus_metrics.record_chat_event('message_processing_error', session_id=session_id, user_id=user_id)
                
                logging.error(f"处理消息时发生错误: {e}")
                
                try:
                    await manager.send_personal_message(
                        json.dumps({
                            "type": "error", 
                            "message": "服务器内部错误",
                            "timestamp": datetime.now().isoformat()
                        }),
                        session_id
                    )
                except Exception as send_error:
                    await logger_manager.log_error('send_server_error_message_failed', str(send_error), 
                                                 {'session_id': session_id, 'user_id': user_id})
                    logging.error(f"发送服务器错误消息失败: {send_error}")
                
    except WebSocketDisconnect:
        if session_id:
            # 记录WebSocket断开连接
            disconnect_start = time.time()
            try:
                # 更新会话的最后活动时间
                await mysql_manager.update_session_activity(session_id)
                update_duration = time.time() - disconnect_start
                
                # 记录会话活动更新
                await logger_manager.log_chat_event(
                    event_type="SESSION_ACTIVITY_UPDATED",
                    session_id=session_id,
                    user_id=user_id,
                    message_content="Session activity updated on disconnect",
                    duration=update_duration
                )
                
                # 记录数据库操作指标
                prometheus_metrics.record_db_operation('update_session_activity', True, update_duration)
                
                logging.info(f"会话活动已更新: {session_id}，耗时: {update_duration:.3f}s")
                
            except Exception as e:
                update_duration = time.time() - disconnect_start
                
                # 记录会话活动更新失败
                await logger_manager.log_error('session_activity_update_error', str(e), 
                                             {'session_id': session_id, 'user_id': user_id, 'duration': update_duration})
                
                # 记录数据库操作失败指标
                prometheus_metrics.record_db_operation('update_session_activity', False, update_duration)
                
                logging.error(f"更新会话活动失败: {e}")
            
            # 记录WebSocket断开连接事件
            await logger_manager.log_chat_event(
                event_type="WEBSOCKET_DISCONNECTED",
                session_id=session_id,
                user_id=user_id,
                message_content="WebSocket connection closed normally",
                duration=0
            )
            
            # 记录WebSocket断开指标
            prometheus_metrics.record_websocket_event('connection_disconnected_normally')
            
            manager.disconnect(session_id)
            
    except Exception as e:
        # 记录WebSocket连接异常
        await logger_manager.log_error('websocket_connection_error', str(e), 
                                     {'session_id': session_id, 'user_id': user_id})
        
        # 记录WebSocket连接异常指标
        prometheus_metrics.record_websocket_event('connection_error')
        
        logging.error(f"WebSocket连接异常: {e}")
        
        if session_id:
            # 更新会话的最后活动时间
            error_disconnect_start = time.time()
            try:
                await mysql_manager.update_session_activity(session_id)
                error_update_duration = time.time() - error_disconnect_start
                
                # 记录错误情况下会话活动更新
                await logger_manager.log_chat_event(
                    event_type="SESSION_ACTIVITY_UPDATED_ON_ERROR",
                    session_id=session_id,
                    user_id=user_id,
                    message_content="Session activity updated after connection error",
                    duration=error_update_duration
                )
                
                logging.info(f"错误情况下会话活动已更新: {session_id}，耗时: {error_update_duration:.3f}s")
                
            except Exception as update_error:
                error_update_duration = time.time() - error_disconnect_start
                
                await logger_manager.log_error('session_activity_update_on_error_failed', str(update_error), 
                                             {'session_id': session_id, 'user_id': user_id, 'duration': error_update_duration})
                
                logging.error(f"错误情况下更新会话活动失败: {update_error}")
                
                # 记录数据库操作失败指标
                prometheus_metrics.record_db_operation('update_session_activity_on_error', False, error_update_duration)
            manager.disconnect(session_id)


# 会话管理端点
@router.post("/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest = None, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """创建新会话"""
    start_time = time.time()
    
    try:
        # 验证token
        username = await verify_token(credentials)
        user_id = username
        
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        # 生成新的会话ID
        session_id = str(uuid.uuid4())
        current_time = datetime.now()
        
        # 创建会话记录
        success = await mysql_manager.create_session_if_not_exists(session_id, user_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="创建会话失败")
        
        # 构建会话响应
        session_response = SessionResponse(
            session_id=session_id,
            title=request.title if request and request.title else "新会话",
            start_time=current_time,
            message_count=0,
            status="active",
            last_message="新会话"
        )
        
        duration = time.time() - start_time
        
        # 记录会话创建事件
        await logger_manager.log_chat_event(
            event_type="SESSION_CREATED_API",
            session_id=session_id,
            user_id=user_id,
            message_content=f"API创建会话: {session_response.title}",
            duration=duration
        )
        
        # 记录性能日志
        await logger_manager.log_performance('create_session_api', duration, 
                                           {'user_id': user_id, 'session_id': session_id})
        
        # 记录会话创建指标
        prometheus_metrics.record_chat_event('session_created_api', session_id=session_id, user_id=user_id)
        
        logging.info(f"API创建会话成功: {session_id}，耗时: {duration:.3f}s")
        
        return session_response
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录会话创建失败
        await logger_manager.log_error('create_session_api_error', str(e), 
                                     {'user_id': user_id, 'duration': duration})
        
        prometheus_metrics.record_chat_event('session_creation_api_failed', user_id=user_id)
        
        logging.error(f"创建会话失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取用户的会话列表"""
    start_time = time.time()
    user_id = None
    
    try:
        # 验证token
        username = await verify_token(credentials)
        user_id = username
        
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        # 获取会话列表（从数据库）
        sessions_data = await mysql_manager.get_user_sessions(user_id)
        
        # 转换为响应格式
        sessions = []
        for session_data in sessions_data:
            # 处理datetime字段
            created_time = session_data.get('created_at')
            if isinstance(created_time, str):
                created_time = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
            
            end_time = session_data.get('last_activity')
            if end_time and isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # 处理会话标题
            session_metadata = session_data.get('session_metadata')
            title = "会话"
            if session_metadata:
                if isinstance(session_metadata, str):
                    try:
                        import json
                        metadata_dict = json.loads(session_metadata)
                        title = metadata_dict.get('title', '会话')
                    except:
                        title = session_metadata
                elif isinstance(session_metadata, dict):
                    title = session_metadata.get('title', '会话')
            
            session_response = SessionResponse(
                session_id=session_data.get('session_id'),
                title=title,
                start_time=created_time,
                end_time=end_time,
                message_count=session_data.get('message_count', 0),
                status=session_data.get('status', 'active'),
                last_message=session_data.get('last_message') or "无消息"
            )
            sessions.append(session_response)
        
        duration = time.time() - start_time
        
        # 记录会话列表获取事件
        await logger_manager.log_chat_event(
            event_type="SESSION_LIST_RETRIEVED",
            session_id=None,
            user_id=user_id,
            message_content=f"获取会话列表: {len(sessions)}个会话",
            duration=duration
        )
        
        # 记录性能日志
        await logger_manager.log_performance('get_sessions_api', duration, 
                                           {'user_id': user_id, 'session_count': len(sessions)})
        
        # 记录会话列表获取指标
        prometheus_metrics.record_chat_event('session_list_retrieved', user_id=user_id)
        
        logging.info(f"获取会话列表成功: {len(sessions)}个会话，耗时: {duration:.3f}s")
        
        return SessionListResponse(sessions=sessions, total=len(sessions))
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录会话列表获取失败
        await logger_manager.log_error('get_sessions_api_error', str(e), 
                                     {'user_id': user_id or 'unknown', 'duration': duration})
        
        prometheus_metrics.record_chat_event('session_list_retrieval_failed', user_id=user_id)
        
        logging.error(f"获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """删除会话"""
    start_time = time.time()
    
    try:
        # 验证token
        username = await verify_token(credentials)
        user_id = username
        
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        # 验证会话属于当前用户
        session_user_id = await mysql_manager.get_session_user_id(session_id)
        if session_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权删除此会话")
        
        # 删除会话
        success = await mysql_manager.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除会话失败")
        
        duration = time.time() - start_time
        
        # 记录会话删除事件
        await logger_manager.log_chat_event(
            event_type="SESSION_DELETED",
            session_id=session_id,
            user_id=user_id,
            message_content="会话已删除",
            duration=duration
        )
        
        # 记录性能日志
        await logger_manager.log_performance('delete_session_api', duration, 
                                           {'user_id': user_id, 'session_id': session_id})
        
        # 记录会话删除指标
        prometheus_metrics.record_chat_event('session_deleted', session_id=session_id, user_id=user_id)
        
        logging.info(f"删除会话成功: {session_id}，耗时: {duration:.3f}s")
        
        return {"message": "会话删除成功", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录会话删除失败
        await logger_manager.log_error('delete_session_api_error', str(e), 
                                     {'user_id': user_id, 'session_id': session_id, 'duration': duration})
        
        prometheus_metrics.record_chat_event('session_deletion_failed', session_id=session_id, user_id=user_id)
        
        logging.error(f"删除会话失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")

@router.put("/sessions/{session_id}")
async def rename_session(session_id: str, request: SessionRenameRequest, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """重命名会话"""
    start_time = time.time()
    
    try:
        # 验证token
        username = await verify_token(credentials)
        user_id = username
        
        if not user_id:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        
        # 验证会话属于当前用户
        session_user_id = await mysql_manager.get_session_user_id(session_id)
        if session_user_id != user_id:
            raise HTTPException(status_code=403, detail="无权修改此会话")
        
        # 重命名会话
        success = await mysql_manager.rename_session(session_id, request.title)
        
        if not success:
            raise HTTPException(status_code=500, detail="重命名会话失败")
        
        duration = time.time() - start_time
        
        # 记录会话重命名事件
        await logger_manager.log_chat_event(
            event_type="SESSION_RENAMED",
            session_id=session_id,
            user_id=user_id,
            message_content=f"会话重命名为: {request.title}",
            duration=duration
        )
        
        # 记录性能日志
        await logger_manager.log_performance('rename_session_api', duration, 
                                           {'user_id': user_id, 'session_id': session_id, 'new_title': request.title})
        
        # 记录会话重命名指标
        prometheus_metrics.record_chat_event('session_renamed', session_id=session_id, user_id=user_id)
        
        logging.info(f"重命名会话成功: {session_id} -> {request.title}，耗时: {duration:.3f}s")
        
        return {"message": "会话重命名成功", "session_id": session_id, "title": request.title}
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录会话重命名失败
        await logger_manager.log_error('rename_session_api_error', str(e), 
                                     {'user_id': user_id, 'session_id': session_id, 'duration': duration})
        
        prometheus_metrics.record_chat_event('session_rename_failed', session_id=session_id, user_id=user_id)
        
        logging.error(f"重命名会话失败: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")




