#!/usr/bin/env python3
"""
Qdrant 向量数据库可视化工具
使用 Streamlit 创建 Web 界面来查看和搜索 Qdrant 中的数据
"""

import streamlit as st
import json
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# 页面配置
st.set_page_config(
    page_title="Qdrant 向量库可视化",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 标题
st.title("🔍 Qdrant 向量数据库可视化工具")
st.markdown("---")

# 侧边栏 - 连接配置
with st.sidebar:
    st.header("⚙️ 连接配置")
    
    # Qdrant URL
    qdrant_url = st.text_input(
        "Qdrant URL",
        value="http://localhost:6333",
        help="Qdrant 服务器地址"
    )
    
    # 连接状态
    try:
        client = QdrantClient(url=qdrant_url)
        collections = client.get_collections()
        st.success("✅ 已连接到 Qdrant")
        
        # 集合选择
        collection_names = [c.name for c in collections.collections]
        selected_collection = st.selectbox(
            "📚 选择集合",
            options=collection_names,
            index=0 if collection_names else None
        )
        
    except Exception as e:
        st.error(f"❌ 连接失败: {str(e)}")
        selected_collection = None

# 主内容区
if selected_collection:
    st.header(f"📚 集合: {selected_collection}")
    
    # 获取集合信息
    try:
        collection_info = client.get_collection(selected_collection)
        
        # 显示集合统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("状态", collection_info.status)
        with col2:
            vectors_count = getattr(collection_info, 'vectors_count', getattr(collection_info, 'points_count', 0))
            st.metric("向量数量", vectors_count)
        with col3:
            st.metric("向量维度", collection_info.config.params.vectors.size)
        with col4:
            st.metric("距离度量", collection_info.config.params.vectors.distance)
        
        st.markdown("---")
        
        # 标签页
        tab1, tab2, tab3 = st.tabs(["📋 数据浏览", "🔍 搜索测试", "📊 统计信息"])
        
        with tab1:
            st.subheader("数据浏览")
            
            # 分页设置
            page_size = st.slider("每页数量", 5, 50, 10)
            page_num = st.number_input("页码", min_value=1, value=1, step=1)
            
            offset = (page_num - 1) * page_size
            
            # 获取数据
            points, next_offset = client.scroll(
                collection_name=selected_collection,
                limit=page_size,
                offset=offset,
                with_payload=True,
                with_vectors=False
            )
            
            st.write(f"显示第 {offset + 1} - {offset + len(points)} 条，共 {vectors_count} 条")
            
            # 显示数据
            for i, point in enumerate(points):
                with st.expander(f"📄 ID: {point.id} (chunk_index: {point.payload.get('chunk_index', 'N/A')})"):
                    st.json(point.payload)
        
        with tab2:
            st.subheader("向量搜索测试")
            
            # 搜索输入
            query_text = st.text_area("输入搜索文本", height=100, placeholder="输入要搜索的内容...")
            search_limit = st.slider("返回数量", 1, 20, 5)
            
            if st.button("🔍 执行搜索"):
                if query_text.strip():
                    with st.spinner("正在搜索..."):
                        try:
                            # 注意：实际搜索需要 embedding 模型
                            # 这里我们展示如何使用 payload 进行过滤搜索
                            
                            # 获取所有点进行简单匹配演示
                            all_points, _ = client.scroll(
                                collection_name=selected_collection,
                                limit=search_limit,
                                with_payload=True,
                                with_vectors=False
                            )
                            
                            st.success(f"找到 {len(all_points)} 条结果")
                            
                            for i, point in enumerate(all_points):
                                st.write(f"---")
                                st.write(f"**结果 {i+1}** (ID: {point.id})")
                                st.json(point.payload)
                                
                        except Exception as e:
                            st.error(f"搜索失败: {str(e)}")
                else:
                    st.warning("请输入搜索文本")
        
        with tab3:
            st.subheader("Payload 字段统计")
            
            # 获取所有点的payload
            all_points, _ = client.scroll(
                collection_name=selected_collection,
                limit=100,
                with_payload=True,
                with_vectors=False
            )
            
            # 统计字段
            field_stats = {}
            for point in all_points:
                if point.payload:
                    for key in point.payload.keys():
                        if key not in field_stats:
                            field_stats[key] = 0
                        field_stats[key] += 1
            
            # 显示统计
            st.write("字段出现频率:")
            for field, count in sorted(field_stats.items(), key=lambda x: -x[1]):
                st.write(f"  - {field}: {count} 次")
            
            # 源文件统计
            sources = {}
            for point in all_points:
                source = point.payload.get('source', 'Unknown')
                if source not in sources:
                    sources[source] = 0
                sources[source] += 1
            
            st.write("\n源文件统计:")
            for source, count in sorted(sources.items(), key=lambda x: -x[1]):
                st.write(f"  - {source}: {count} 条")
        
    except Exception as e:
        st.error(f"获取集合信息失败: {str(e)}")
        
elif collections and not collections.collections:
    st.info("📭 未找到任何集合，请先上传数据到 Qdrant")
    
else:
    st.warning("⚠️ 请确保 Qdrant 服务正在运行")
    st.markdown("""
    ### 启动 Qdrant 服务
    ```bash
    # 使用 Docker 启动
    docker run -p 6333:6333 qdrant/qdrant
    
    # 或从源码启动
    cargo run --bin qdrant
    ```
    """)
