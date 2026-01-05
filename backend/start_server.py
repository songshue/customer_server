#!/usr/bin/env python3
"""
服务器启动脚本 - 自动处理Python路径问题
"""
import os
import sys

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 启动FastAPI应用
if __name__ == "__main__":
    import uvicorn
    print("🚀 启动客服系统服务器...")
    print(f"工作目录: {current_dir}")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )