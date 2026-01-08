from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict
import uuid
import time

from app.managers.mysql_manager import mysql_manager
from app.managers.logger_manager import logger_manager
from app.core.security import verify_token

router = APIRouter()
security = HTTPBearer()

@router.post("/feedback")
async def submit_feedback(
    feedback_data: Dict,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    提交用户反馈
    
    请求体格式:
    {
        "message_id": 123,
        "session_id": "session-123",
        "rating": 5,
        "comment": "非常满意"
    }
    
    响应格式:
    {
        "message": "反馈提交成功",
        "success": true
    }
    """
    start_time = time.time()
    trace_id = str(uuid.uuid4())
    
    try:
        # 验证用户身份
        user_id = await verify_token(credentials)
        
        # 验证请求数据
        message_id = feedback_data.get("message_id")
        session_id = feedback_data.get("session_id")
        rating = feedback_data.get("rating")
        comment = feedback_data.get("comment", "")
        
        if not message_id or not session_id or rating is None:
            raise HTTPException(status_code=400, detail="缺少必要的请求参数")
        
        if not (1 <= rating <= 5):
            raise HTTPException(status_code=400, detail="评分必须在1-5之间")
        
        # 记录反馈请求
        await logger_manager.log_chat_event(
            event_type="FEEDBACK_REQUEST",
            session_id=session_id,
            user_id=user_id,
            message_content=f"Rating: {rating}, Comment: {comment[:50]}",
            duration=0,
            trace_id=trace_id
        )
        
        # 保存反馈
        success = await mysql_manager.save_feedback(
            message_id=message_id,
            session_id=session_id,
            user_id=user_id,
            rating=rating,
            comment=comment
        )
        
        if success:
            # 记录反馈成功
            duration = time.time() - start_time
            await logger_manager.log_chat_event(
                event_type="FEEDBACK_SUBMITTED",
                session_id=session_id,
                user_id=user_id,
                message_content=f"Rating: {rating}, Comment: {comment[:50]}",
                duration=duration,
                trace_id=trace_id
            )
            
            return {
                "message": "反馈提交成功",
                "success": True
            }
        else:
            raise HTTPException(status_code=500, detail="保存反馈失败")
            
    except HTTPException:
        # 记录反馈失败
        duration = time.time() - start_time
        await logger_manager.log_error(
            error_type="feedback_error",
            error_message="HTTP异常",
            context={
                "user_id": user_id,
                "session_id": session_id,
                "message_id": message_id,
                "duration": duration
            },
            trace_id=trace_id
        )
        raise
    except Exception as e:
        # 记录反馈异常
        duration = time.time() - start_time
        await logger_manager.log_error(
            error_type="feedback_exception",
            error_message=str(e),
            context={
                "user_id": user_id,
                "session_id": session_id,
                "message_id": message_id,
                "duration": duration
            },
            trace_id=trace_id
        )
        raise HTTPException(status_code=500, detail=f"处理反馈失败: {str(e)}")
