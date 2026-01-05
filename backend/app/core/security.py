import os
import jwt
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from app.managers.redis_manager import redis_manager

load_dotenv()

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-for-development")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": str(uuid.uuid4())  # JWT ID，用于黑名单
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    """创建JWT刷新令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4())
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def add_to_blacklist(token_jti: str, expires_delta: timedelta):
    """将令牌添加到黑名单（异步版本）"""
    try:
        await redis_manager.setex_async(
            f"blacklist:{token_jti}", 
            int(expires_delta.total_seconds()), 
            "revoked"
        )
    except Exception as e:
        print(f"添加黑名单失败: {e}")

async def is_token_blacklisted(token_jti: str) -> bool:
    """检查令牌是否在黑名单中（异步版本）"""
    try:
        result = await redis_manager.get_async(f"blacklist:{token_jti}")
        return result == "revoked"
    except Exception as e:
        print(f"检查黑名单失败: {e}")
        return False

def is_token_blacklisted_sync(token_jti: str) -> bool:
    """检查令牌是否在黑名单中（同步版本）"""
    try:
        result = redis_manager.get(f"blacklist:{token_jti}")
        return result == "revoked"
    except Exception as e:
        print(f"检查黑名单失败: {e}")
        return False

async def verify_token(credentials: HTTPAuthorizationCredentials):
    """验证JWT令牌（异步版本）"""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        token_jti = payload.get("jti")
        
        # 检查令牌类型
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌类型",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 检查黑名单
        if token_jti and await is_token_blacklisted(token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌已被撤销",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_refresh_token(refresh_token: str) -> dict:
    """验证刷新令牌"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        token_type = payload.get("type")
        
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
            )
        
        # 检查黑名单
        token_jti = payload.get("jti")
        if token_jti and is_token_blacklisted(token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="刷新令牌已被撤销",
            )
        
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
        )

async def revoke_token(token: str):
    """撤销令牌（添加到黑名单，异步版本）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        token_jti = payload.get("jti")
        exp_timestamp = payload.get("exp")
        
        if token_jti and exp_timestamp:
            # 计算令牌剩余的有效时间
            current_timestamp = datetime.utcnow().timestamp()
            remaining_seconds = max(0, exp_timestamp - current_timestamp)
            
            if remaining_seconds > 0:
                await add_to_blacklist(token_jti, timedelta(seconds=remaining_seconds))
                return True
    except jwt.PyJWTError:
        pass
    return False