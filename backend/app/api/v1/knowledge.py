#!/usr/bin/env python3
"""
知识库管理API
功能：文件上传、向量化、搜索等接口
"""
import os
import sys
import json
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.knowledge_base import (
    KnowledgeBasePipeline,
    DocumentProcessor,
    QdrantVectorStore
)

from app.models import SearchRequest, SearchResponse, UploadResponse, CollectionInfoResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

knowledge_pipelines: Dict[str, KnowledgeBasePipeline] = {}

def get_pipeline(collection_name: str, knowledge_dir: str = "knowledge") -> KnowledgeBasePipeline:
    """获取或创建知识库处理流水线"""
    if collection_name not in knowledge_pipelines:
        knowledge_pipelines[collection_name] = KnowledgeBasePipeline(
            knowledge_dir=knowledge_dir,
            collection_name=collection_name
        )
    return knowledge_pipelines[collection_name]

@router.post("/upload/{collection_name}")
async def upload_file(
    collection_name: str,
    file: UploadFile = File(...),
    knowledge_dir: str = Form("knowledge")
):
    """
    上传文件并向量化到指定集合
    
    Args:
        collection_name: 集合名称
        file: 上传的文件
        knowledge_dir: 知识库目录
        
    Returns:
        上传结果
    """
    try:
        allowed_extensions = {'.pdf', '.docx', '.txt', '.csv', '.md'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {file_ext}。支持格式: {', '.join(allowed_extensions)}"
            )
        
        save_dir = Path(knowledge_dir)
        if not save_dir.exists():
            save_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = save_dir / file.filename
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        pipeline = get_pipeline(collection_name, knowledge_dir)
        
        pipeline.add_single_document(str(file_path))
        
        return UploadResponse(
            success=True,
            message="文件上传并向量化成功",
            filename=file.filename,
            collection_name=collection_name,
            chunks_processed=1
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

@router.post("/search")
async def search_knowledge(request: SearchRequest):
    """
    搜索知识库
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果
    """
    try:
        pipeline = get_pipeline(request.collection_name)
        
        results = pipeline.search_knowledge(
            query=request.query,
            limit=request.limit,
            filter_source=request.filter_source
        )
        
        return SearchResponse(
            success=True,
            results=results,
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

@router.get("/collection/{collection_name}/info")
async def get_collection_info(collection_name: str):
    """
    获取集合信息
    
    Args:
        collection_name: 集合名称
        
    Returns:
        集合信息
    """
    try:
        pipeline = get_pipeline(collection_name)
        info = pipeline.vector_store.get_collection_info()
        
        return CollectionInfoResponse(
            success=True,
            info=info
        )
        
    except Exception as e:
        logger.error(f"获取集合信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")

@router.post("/collection/{collection_name}/rebuild")
async def rebuild_collection(collection_name: str, clear_existing: bool = True):
    """
    重建整个集合
    
    Args:
        collection_name: 集合名称
        clear_existing: 是否清除已有数据
        
    Returns:
        重建结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        result = pipeline.run(clear_existing=clear_existing)
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"重建集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"重建失败: {str(e)}")

@router.delete("/collection/{collection_name}/source/{filename}")
async def delete_by_source(collection_name: str, filename: str):
    """
    删除指定源的所有文档
    
    Args:
        collection_name: 集合名称
        filename: 源文件名
        
    Returns:
        删除结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        pipeline.vector_store.delete_by_source(filename)
        
        file_path = Path("knowledge") / filename
        if file_path.exists():
            file_path.unlink()
        
        return JSONResponse(content={
            "success": True,
            "message": f"已删除 {filename} 的文档和源文件"
        })
        
    except Exception as e:
        logger.error(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.get("/collections")
async def list_collections():
    """
    列出所有集合
    
    Returns:
        集合列表
    """
    try:
        from app.services.knowledge_base import QdrantVectorStore
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        all_collections = client.get_collections()
        
        info_list = []
        for collection in all_collections.collections:
            collection_name = collection.name
            try:
                collection_info = client.get_collection(collection_name)
                vectors_count = getattr(collection_info, 'vectors_count', 
                               getattr(collection_info, 'points_count', 0))
                status = getattr(collection_info, 'status', 'unknown')
                info_list.append({
                    "name": collection_name,
                    "vectors_count": vectors_count,
                    "status": status
                })
            except Exception as e:
                logger.warning(f"获取集合 {collection_name} 信息失败: {e}")
                info_list.append({
                    "name": collection_name,
                    "vectors_count": 0,
                    "status": "unknown"
                })
        
        return JSONResponse(content={
            "success": True,
            "collections": info_list
        })
        
    except Exception as e:
        logger.error(f"列出集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"列出失败: {str(e)}")

@router.get("/collection/{collection_name}/points")
async def get_collection_points(collection_name: str, limit: int = 1000):
    """
    获取集合中的所有数据点（用于展示文件列表）
    
    Args:
        collection_name: 集合名称
        limit: 返回数量限制
        
    Returns:
        数据点列表
    """
    try:
        pipeline = get_pipeline(collection_name)
        
        scroll_result = pipeline.vector_store.client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        if hasattr(scroll_result, 'points'):
            points = scroll_result.points
        else:
            points = scroll_result[0] if isinstance(scroll_result, tuple) else scroll_result
        
        return JSONResponse(content={
            "success": True,
            "points": [
                {
                    "id": point.id,
                    "payload": point.payload
                }
                for point in points
            ],
            "total": len(points)
        })
        
    except Exception as e:
        logger.error(f"获取集合数据点失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")

@router.delete("/collection/{collection_name}")
async def delete_collection(collection_name: str):
    """
    删除整个集合
    
    Args:
        collection_name: 集合名称
        
    Returns:
        删除结果
    """
    try:
        from app.services.knowledge_base import QdrantVectorStore
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        
        try:
            client.get_collection(collection_name)
        except Exception:
            return JSONResponse(content={
                "success": True,
                "message": f"集合不存在: {collection_name}"
            })
        
        client.delete_collection(collection_name)
        
        if collection_name in knowledge_pipelines:
            del knowledge_pipelines[collection_name]
        
        return JSONResponse(content={
            "success": True,
            "message": f"已删除集合: {collection_name}"
        })
        
    except Exception as e:
        logger.error(f"删除集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.put("/collection/{collection_name}/rename")
async def rename_collection(collection_name: str, new_name: str):
    """
    重命名集合
    
    Args:
        collection_name: 集合名称
        new_name: 新名称
        
    Returns:
        重命名结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        success = pipeline.vector_store.rename_collection(new_name)
        
        if success and collection_name in knowledge_pipelines:
            knowledge_pipelines[new_name] = knowledge_pipelines.pop(collection_name)
        
        return JSONResponse(content={
            "success": True,
            "message": f"已将集合 {collection_name} 重命名为 {new_name}"
        })
        
    except Exception as e:
        logger.error(f"重命名集合失败: {e}")
        raise HTTPException(status_code=500, detail=f"重命名失败: {str(e)}")

@router.delete("/collection/{collection_name}/chunk/{point_id}")
async def delete_chunk(collection_name: str, point_id: str):
    """
    删除单个chunk
    
    Args:
        collection_name: 集合名称
        point_id: chunk ID
        
    Returns:
        删除结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        success = pipeline.vector_store.delete_chunk(point_id)
        
        return JSONResponse(content={
            "success": True,
            "message": f"已删除 chunk: {point_id}"
        })
        
    except Exception as e:
        logger.error(f"删除 chunk 失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

@router.put("/collection/{collection_name}/chunk/{point_id}")
async def update_chunk(
    collection_name: str,
    point_id: str,
    new_content: str,
    new_metadata: Dict[str, Any] = None
):
    """
    更新单个chunk
    
    Args:
        collection_name: 集合名称
        point_id: chunk ID
        new_content: 新的内容
        new_metadata: 新的元数据
        
    Returns:
        更新结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        
        success = pipeline.vector_store.update_chunk(
            point_id=point_id,
            new_content=new_content,
            new_metadata=new_metadata
        )
        
        return JSONResponse(content={
            "success": True,
            "message": f"已更新 chunk: {point_id}"
        })
        
    except Exception as e:
        logger.error(f"更新 chunk 失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@router.post("/collection/{collection_name}/chunk")
async def add_chunk(
    collection_name: str,
    content: str,
    metadata: Dict[str, Any]
):
    """
    添加单个chunk
    
    Args:
        collection_name: 集合名称
        content: 内容
        metadata: 元数据
        
    Returns:
        添加结果
    """
    try:
        pipeline = get_pipeline(collection_name)
        
        point_id = pipeline.vector_store.add_chunk(
            content=content,
            metadata=metadata,
            embeddings=pipeline.processor.embeddings
        )
        
        if point_id:
            return JSONResponse(content={
                "success": True,
                "message": "chunk 添加成功",
                "point_id": point_id
            })
        else:
            raise HTTPException(status_code=500, detail="添加 chunk 失败")
        
    except Exception as e:
        logger.error(f"添加 chunk 失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")

@router.get("/collection/{collection_name}/chunk/{point_id}")
async def get_chunk(collection_name: str, point_id: str):
    """
    获取单个chunk
    
    Args:
        collection_name: 集合名称
        point_id: chunk ID
        
    Returns:
        chunk信息
    """
    try:
        pipeline = get_pipeline(collection_name)
        chunk = pipeline.vector_store.get_chunk(point_id)
        
        if chunk:
            return JSONResponse(content={
                "success": True,
                "chunk": chunk
            })
        else:
            raise HTTPException(status_code=404, detail="chunk 不存在")
        
    except Exception as e:
        logger.error(f"获取 chunk 失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")
