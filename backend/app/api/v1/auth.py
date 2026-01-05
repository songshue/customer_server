from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import timedelta
from typing import Optional
import time
import asyncio

router = APIRouter()
security = HTTPBearer()

from app.core.security import (
    create_access_token, 
    create_refresh_token, 
    verify_refresh_token,
    revoke_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

from app.managers.logger_manager import logger_manager
from app.managers.prometheus_manager import prometheus_metrics

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: Optional[str] = None

class UserToken(BaseModel):
    """用户令牌模型"""
    access_token: str
    username: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型"""
    refresh_token: str

class LogoutRequest(BaseModel):
    """登出请求模型"""
    refresh_token: Optional[str] = None

@router.post("/login", response_model=UserToken)
async def login(user_data: UserLogin):
    """用户登录接口"""
    start_time = time.time()
    
    try:
        # 记录登录尝试
        prometheus_metrics.record_auth_event('login_attempt', status='attempted')
        await logger_manager.log_auth_event('login_attempt', username=user_data.username, success=False)
        
        # 简单的用户验证（演示模式：任何用户名都可以登录）
        if user_data.username and len(user_data.username.strip()) >= 2:
            duration = time.time() - start_time
            
            # 记录成功登录
            access_token = create_access_token(data={"sub": user_data.username})
            
            # 记录JWT令牌发放指标
            prometheus_metrics.record_auth_event('jwt_issued', token_type='access')
            
            # 记录成功登录日志
            prometheus_metrics.record_auth_event('login_attempt', status='success')
            await logger_manager.log_auth_event('login_attempt', username=user_data.username, success=True, 
                                              details={'token_type': 'access', 'duration': duration})
            
            return UserToken(
                access_token=access_token,
                username=user_data.username,
                token_type="bearer",
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
            )
        else:
            duration = time.time() - start_time
            
            # 记录失败登录
            prometheus_metrics.record_auth_event('login_attempt', status='failure')
            await logger_manager.log_auth_event('login_attempt', username=user_data.username, success=False,
                                              details={'reason': 'invalid_credentials', 'duration': duration})
            
            # 记录性能日志
            await logger_manager.log_performance('login', duration, 
                                               {'username': user_data.username, 'success': False})
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except Exception as e:
        duration = time.time() - start_time
        
        # 记录异常
        prometheus_metrics.record_auth_event('login_attempt', status='error')
        await logger_manager.log_error('login_error', str(e), 
                                     {'username': user_data.username, 'duration': duration})
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录过程中发生错误",
        )

@router.post("/refresh", response_model=UserToken)
async def refresh_token(refresh_data: RefreshTokenRequest):
    """刷新访问令牌"""
    try:
        # 验证刷新令牌
        payload = verify_refresh_token(refresh_data.refresh_token)
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )
        
        # 撤销旧的刷新令牌
        await revoke_token(refresh_data.refresh_token)
        
        # 创建新的访问令牌和刷新令牌
        new_access_token = create_access_token(data={"sub": username})
        new_refresh_token = create_refresh_token(data={"sub": username})
        
        return UserToken(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败",
        )

@router.post("/logout")
async def logout(logout_data: LogoutRequest = None, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """用户登出"""
    try:
        # 撤销访问令牌
        await revoke_token(credentials.credentials)
        
        # 如果提供了刷新令牌，也撤销它
        if logout_data and logout_data.refresh_token:
            await revoke_token(logout_data.refresh_token)
        
        return {"message": "登出成功"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败",
        )

@router.get("/verify")
async def verify_token_endpoint(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证令牌"""
    from app.core.security import verify_token
    username = await verify_token(credentials)
    return {"username": username, "valid": True}