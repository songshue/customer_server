<template>
  <div class="knowledge-base-container">
    <header class="page-header">
      <div class="header-top">
        <h1>📚 知识库管理</h1>
        <div class="header-actions">
          <button class="nav-btn" @click="goToChat">
            💬 客服问答
          </button>
        </div>
      </div>
      <p class="subtitle">管理文档知识库，支持上传、向量化、搜索等功能</p>
    </header>

    <div class="breadcrumb">
      <span 
        class="breadcrumb-item" 
        :class="{ active: currentLevel === 'collections' }"
        @click="goToLevel('collections')"
      >
        所有集合
      </span>
      <template v-if="currentLevel === 'files' || currentLevel === 'chunks'">
        <span class="breadcrumb-separator">›</span>
        <span 
          class="breadcrumb-item"
          :class="{ active: currentLevel === 'files' }"
          @click="goToLevel('files')"
        >
          {{ currentCollection }}
        </span>
      </template>
      <template v-if="currentLevel === 'chunks'">
        <span class="breadcrumb-separator">›</span>
        <span class="breadcrumb-item active">{{ currentFile }}</span>
      </template>
    </div>

    <div class="main-content">
      <div v-if="currentLevel === 'collections'" class="level-collections">
        <div class="card upload-section">
          <h2>📤 上传文档</h2>
          <div class="upload-area" @click="triggerFileInput" @drop.prevent="handleDrop" @dragover.prevent>
            <input 
              type="file" 
              ref="fileInput" 
              accept=".pdf,.docx,.txt,.csv,.md" 
              multiple 
              style="display: none"
              @change="handleFileSelect"
            />
            <div v-if="!uploading" class="upload-placeholder">
              <span class="upload-icon">📁</span>
              <p>点击或拖拽文件到此处上传</p>
              <p class="hint">支持 PDF、DOCX、TXT、CSV、MD 格式</p>
            </div>
            <div v-else class="uploading">
              <div class="spinner"></div>
              <p>正在处理文件...</p>
            </div>
          </div>
          
          <div v-if="selectedFiles.length > 0" class="selected-files">
            <h3>已选择文件：</h3>
            <ul>
              <li v-for="(file, index) in selectedFiles" :key="index">
                <span class="file-icon">📄</span>
                {{ file.name }}
                <button class="remove-btn" @click="removeFile(index)">×</button>
              </li>
            </ul>
            <div class="collection-input">
              <label>集合名称：</label>
              <input v-model="collectionName" placeholder="customer_policy" />
            </div>
            <button class="upload-btn" @click="uploadFiles" :disabled="uploading">
              {{ uploading ? '处理中...' : '开始向量化' }}
            </button>
          </div>
        </div>

        <div class="card collections-section">
          <div class="section-header">
            <h2>📚 知识库集合</h2>
            <button class="add-btn" @click="showAddCollection = true">+ 新建集合</button>
          </div>
          <div class="collections-grid">
            <div 
              v-for="collection in collections" 
              :key="collection.name"
              class="collection-card"
              @click="selectCollection(collection.name)"
            >
              <div class="collection-icon">📁</div>
              <div class="collection-info">
                <div class="collection-name">{{ collection.name }}</div>
                <div class="collection-count">{{ collection.vectors_count || 0 }} 条向量</div>
              </div>
              <div class="collection-actions">
                <button class="action-btn" @click.stop="editCollection(collection)" title="编辑集合名称">✏️</button>
                <button class="action-btn delete" @click.stop="deleteCollection(collection.name)" title="删除集合">🗑️</button>
              </div>
              <div class="collection-arrow">›</div>
            </div>
          </div>
          <div class="collection-operations">
            <button class="rebuild-btn" @click="rebuildCollection" :disabled="loading">
              {{ loading ? '重建中...' : '🔄 重建当前集合' }}
            </button>
            <button class="export-btn" @click="exportCollection" :disabled="!currentCollection || loading">
              📤 导出数据
            </button>
          </div>
        </div>
      </div>

      <div v-else-if="currentLevel === 'files'" class="level-files">
        <div class="card files-section">
          <div class="section-header">
            <h2>📄 {{ currentCollection }} - 文件列表</h2>
            <div class="header-actions">
              <button class="back-btn" @click="goToLevel('collections')">
                ‹ 返回集合
              </button>
              <button class="add-btn" @click="showAddFile = true">+ 添加文件</button>
            </div>
          </div>
          
          <div v-if="files.length > 0" class="files-grid">
            <div 
              v-for="file in files" 
              :key="file.name"
              class="file-card"
              @click="selectFile(file)"
            >
              <div class="file-icon-large">{{ getFileIcon(file.extension) }}</div>
              <div class="file-info">
                <div class="file-name">{{ file.name }}</div>
                <div class="file-chunks">{{ file.chunks.length }} 个分块</div>
              </div>
              <div class="file-actions">
                <button class="action-btn" @click.stop="viewFileChunks(file)" title="预览分块">👁️</button>
                <button class="action-btn" @click.stop="reuploadFile(file)" title="重新上传">🔄</button>
                <button class="action-btn delete" @click.stop="deleteFile(file.name)" title="删除文件">🗑️</button>
              </div>
              <div class="file-arrow">›</div>
            </div>
          </div>
          <div v-else class="empty-state">
            <span class="empty-icon">📂</span>
            <p>该集合暂无文件</p>
          </div>
        </div>
      </div>

      <div v-else-if="currentLevel === 'chunks'" class="level-chunks">
        <div class="card chunks-section">
          <div class="section-header">
            <div class="header-left">
              <h2>📑 {{ currentFile }} - 内容分块</h2>
              <button class="back-btn" @click="goToLevel('files')">
                ‹ 返回文件列表
              </button>
            </div>
            <div class="chunk-operations">
              <button class="action-btn" @click="addChunk" title="添加新分块">➕ 添加</button>
              <button class="action-btn delete" @click="deleteSelectedChunks" :disabled="selectedChunks.length === 0" title="删除选中分块">🗑️ 批量删除</button>
            </div>
          </div>
          
          <div class="chunk-operations-bar" v-if="currentLevel === 'chunks'">
            <label class="select-all">
              <input type="checkbox" v-model="selectAllChunks" @change="toggleSelectAll" />
              全选
            </label>
            <span class="selected-count">已选中 {{ selectedChunks.length }} 个分块</span>
          </div>
          
          <div class="chunks-grid">
            <div 
              v-for="chunk in chunks" 
              :key="chunk.id"
              class="chunk-card"
              :class="{ selected: selectedChunks.includes(chunk.id) }"
              @click="toggleChunkSelection(chunk.id)"
            >
              <div class="chunk-checkbox" @click.stop>
                <input 
                  type="checkbox" 
                  :checked="selectedChunks.includes(chunk.id)"
                  @change="toggleChunkSelection(chunk.id)"
                />
              </div>
              <div class="chunk-menu">
                <div class="menu-dots" @click.stop="toggleMenu(chunk.id)">
                  <span>•••</span>
                </div>
                <div v-if="activeMenu === chunk.id" class="menu-dropdown">
                  <button @click="showChunkDetails(chunk)">查看详情</button>
                  <button @click="editChunk(chunk)">编辑内容</button>
                  <button @click="copyContent(chunk)">复制内容</button>
                  <button @click="showChunkMetadata(chunk)">元数据</button>
                  <button class="delete" @click="deleteChunk(chunk)">删除</button>
                </div>
              </div>
              <div class="chunk-content">
                <div class="chunk-preview">{{ chunk.page_content }}</div>
              </div>
              <div class="chunk-footer">
                <span class="chunk-index">#{{ chunk.chunk_index + 1 }}</span>
                <span class="chunk-length">{{ chunk.content_length || chunk.page_content.length }} 字符</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="card search-section">
          <h2>🔍 知识搜索</h2>
          <div class="search-box">
            <input 
              v-model="searchQuery" 
              placeholder="输入搜索关键词..."
              @keyup.enter="search"
            />
            <button @click="search" :disabled="searching">
              {{ searching ? '搜索中...' : '搜索' }}
            </button>
          </div>
          
          <div v-if="searchResults.length > 0" class="search-results">
            <h3>搜索结果：</h3>
            <div 
              v-for="(result, index) in searchResults" 
              :key="index"
              class="result-item"
            >
              <div class="result-header">
                <span class="source">{{ result.source }}</span>
                <span class="score">相似度: {{ (result.score * 100).toFixed(1) }}%</span>
              </div>
              <p class="result-content">{{ result.content }}</p>
            </div>
          </div>
          <div v-else-if="searched && searchQuery" class="no-results">
            未找到相关结果
          </div>
        </div>

        <div class="card info-section">
          <h2>ℹ️ 当前信息</h2>
          <div v-if="currentLevel === 'collections'" class="info-content">
            <div class="info-item">
              <span class="label">集合总数：</span>
              <span class="value">{{ collections.length }}</span>
            </div>
            <div class="info-item">
              <span class="label">向量总数：</span>
              <span class="value">{{ totalVectors }}</span>
            </div>
          </div>
          <div v-else-if="selectedCollectionInfo" class="info-content">
            <div class="info-item">
              <span class="label">集合名称：</span>
              <span class="value">{{ selectedCollectionInfo.name }}</span>
            </div>
            <div class="info-item">
              <span class="label">向量数量：</span>
              <span class="value">{{ selectedCollectionInfo.vectors_count || 0 }}</span>
            </div>
            <div class="info-item">
              <span class="label">文件数量：</span>
              <span class="value">{{ files.length }}</span>
            </div>
            <div class="info-item">
              <span class="label">状态：</span>
              <span class="value status-badge" :class="selectedCollectionInfo.status">
                {{ selectedCollectionInfo.status || 'unknown' }}
              </span>
            </div>
          </div>
          <div v-else class="no-info">
            请选择一个集合查看信息
          </div>
        </div>
      </div>
    </div>

    <div v-if="message" class="toast" :class="messageType">
      {{ message }}
    </div>

    <div v-if="showModal" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>{{ modalMode === 'edit' ? '编辑分块' : '分块详情' }}</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <div class="detail-section">
            <h4>基本信息</h4>
            <div class="detail-row">
              <span class="detail-label">ID:</span>
              <span class="detail-value">{{ selectedChunk?.id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">分块索引:</span>
              <span class="detail-value">{{ (selectedChunk?.chunk_index ?? 0) + 1 }} / {{ selectedChunk?.total_chunks }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">源文件:</span>
              <span class="detail-value">{{ selectedChunk?.source }}</span>
            </div>
            <div class="detail-row" v-if="selectedChunk?.section">
              <span class="detail-label">章节:</span>
              <span class="detail-value">{{ selectedChunk?.section }}</span>
            </div>
          </div>
          <div class="detail-section">
            <h4>{{ modalMode === 'edit' ? '编辑内容' : '完整内容' }}</h4>
            <textarea 
              v-if="modalMode === 'edit'"
              v-model="editingContent"
              rows="10"
              class="content-editor"
            ></textarea>
            <div v-else class="full-content">{{ selectedChunk?.page_content }}</div>
          </div>
          <div class="detail-section" v-if="selectedChunk?.headers?.length">
            <h4>标题层级</h4>
            <div class="headers-list">
              <span v-for="(header, idx) in selectedChunk?.headers" :key="idx" class="header-tag">
                {{ header }}
              </span>
            </div>
          </div>
          <div class="detail-section">
            <h4>元数据</h4>
            <div class="meta-grid">
              <div class="meta-item">
                <span class="meta-label">文件类型:</span>
                <span class="meta-value">{{ selectedChunk?.file_type }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">处理时间:</span>
                <span class="meta-value">{{ formatDate(selectedChunk?.processed_at) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">内容长度:</span>
                <span class="meta-value">{{ selectedChunk?.content_length }} 字符</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="modalMode === 'edit'" class="cancel-btn" @click="closeModal">取消</button>
          <button v-if="modalMode === 'edit'" class="save-btn" @click="saveChunkEdit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showAddCollection" class="modal-overlay" @click="showAddCollection = false">
      <div class="modal-content small" @click.stop>
        <div class="modal-header">
          <h3>新建集合</h3>
          <button class="modal-close" @click="showAddCollection = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>集合名称：</label>
            <input v-model="newCollectionName" placeholder="请输入集合名称" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showAddCollection = false">取消</button>
          <button class="save-btn" @click="createCollection">创建</button>
        </div>
      </div>
    </div>

    <div v-if="showAddFile" class="modal-overlay" @click="showAddFile = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>添加文件</h3>
          <button class="modal-close" @click="showAddFile = false">×</button>
        </div>
        <div class="modal-body">
          <div class="upload-area small" @click="triggerFileInput" @drop.prevent="handleFileDrop" @dragover.prevent>
            <input 
              type="file" 
              ref="fileInput2" 
              accept=".pdf,.docx,.txt,.csv,.md" 
              style="display: none"
              @change="handleFileSelect2"
            />
            <div v-if="!singleFile" class="upload-placeholder">
              <span class="upload-icon">📁</span>
              <p>点击或拖拽文件到此处</p>
              <p class="hint">支持 PDF、DOCX、TXT、CSV、MD 格式</p>
            </div>
            <div v-else class="selected-file">
              <span class="file-icon">📄</span>
              <span class="file-name">{{ singleFile.name }}</span>
              <button class="remove-btn" @click="singleFile = null">×</button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showAddFile = false">取消</button>
          <button class="save-btn" @click="addFileToCollection" :disabled="!singleFile">添加</button>
        </div>
      </div>
    </div>

    <div v-if="showEditCollectionModal" class="modal-overlay" @click="showEditCollectionModal = false">
      <div class="modal-content small" @click.stop>
        <div class="modal-header">
          <h3>重命名集合</h3>
          <button class="modal-close" @click="showEditCollectionModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>当前名称：</label>
            <input :value="editingCollection?.name" disabled />
          </div>
          <div class="form-group">
            <label>新名称：</label>
            <input v-model="newCollectionNameForEdit" placeholder="请输入新名称" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showEditCollectionModal = false">取消</button>
          <button class="save-btn" @click="saveCollectionEdit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showAddChunkModal" class="modal-overlay" @click="showAddChunkModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>添加新分块</h3>
          <button class="modal-close" @click="showAddChunkModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>来源文件：</label>
            <input :value="currentFile || '手动添加'" disabled />
          </div>
          <div class="form-group">
            <label>分块内容：</label>
            <textarea 
              v-model="newChunkContent" 
              rows="10" 
              placeholder="请输入分块内容..."
              class="content-editor"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="cancel-btn" @click="showAddChunkModal = false">取消</button>
          <button class="save-btn" @click="saveNewChunk">添加</button>
        </div>
      </div>
    </div>

    <div v-if="showMetadataModal" class="modal-overlay" @click="closeMetadataModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>元数据详情</h3>
          <button class="modal-close" @click="closeMetadataModal">×</button>
        </div>
        <div class="modal-body">
          <div class="meta-detail">
            <div class="meta-row">
              <span class="meta-label">ID:</span>
              <span class="meta-value">{{ metadataChunk?.id }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">源文件:</span>
              <span class="meta-value">{{ metadataChunk?.source }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">分块索引:</span>
              <span class="meta-value">{{ (metadataChunk?.chunk_index ?? 0) + 1 }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">文件类型:</span>
              <span class="meta-value">{{ metadataChunk?.file_type }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">章节:</span>
              <span class="meta-value">{{ metadataChunk?.section || 'N/A' }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">处理时间:</span>
              <span class="meta-value">{{ formatDate(metadataChunk?.processed_at) }}</span>
            </div>
            <div class="meta-row">
              <span class="meta-label">内容长度:</span>
              <span class="meta-value">{{ metadataChunk?.content_length }} 字符</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

interface SearchResult {
  content: string
  source: string
  score: number
}

interface CollectionInfo {
  name: string
  vectors_count: number
  status: string
}

interface ChunkData {
  id: string
  page_content: string
  source: string
  file_type?: string
  section?: string
  headers?: string[]
  chunk_index: number
  total_chunks?: number
  processed_at?: string
  content_length?: number
}

interface FileData {
  name: string
  extension: string
  chunks: ChunkData[]
}

type Level = 'collections' | 'files' | 'chunks'

const router = useRouter()

const fileInput = ref<HTMLInputElement | null>(null)
const fileInput2 = ref<HTMLInputElement | null>(null)
const selectedFiles = ref<File[]>([])
const singleFile = ref<File | null>(null)
const uploading = ref(false)
const loading = ref(false)
const searching = ref(false)
const searched = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error' | 'info'>('info')

const collectionName = ref('customer_policy')
const newCollectionName = ref('')
const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
const collections = ref<CollectionInfo[]>([])
const selectedCollectionInfo = ref<CollectionInfo | null>(null)
const files = ref<FileData[]>([])
const chunks = ref<ChunkData[]>([])

const currentLevel = ref<Level>('collections')
const currentCollection = ref('')
const currentFile = ref('')
const activeMenu = ref<string | null>(null)
const showModal = ref(false)
const showAddCollection = ref(false)
const showAddFile = ref(false)
const showMetadataModal = ref(false)
const showEditCollectionModal = ref(false)
const showAddChunkModal = ref(false)
const modalMode = ref<'view' | 'edit'>('view')
const selectedChunk = ref<ChunkData | null>(null)
const metadataChunk = ref<ChunkData | null>(null)
const editingContent = ref('')
const selectedChunks = ref<string[]>([])
const selectAllChunks = ref(false)
const editingCollection = ref<CollectionInfo | null>(null)
const newCollectionNameForEdit = ref('')
const newChunkContent = ref('')

const totalVectors = computed(() => {
  return collections.value.reduce((sum, c) => sum + (c.vectors_count || 0), 0)
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    selectedFiles.value = Array.from(target.files)
  }
}

const handleFileSelect2 = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    singleFile.value = target.files[0]
  }
}

const handleFileDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
    singleFile.value = event.dataTransfer.files[0]
  }
}

const handleDrop = (event: DragEvent) => {
  if (event.dataTransfer?.files) {
    selectedFiles.value = Array.from(event.dataTransfer.files)
  }
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}

const showMessage = (msg: string, type: 'success' | 'error' | 'info' = 'info') => {
  message.value = msg
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}

const goToChat = () => {
  router.push('/')
}

const uploadFiles = async () => {
  if (selectedFiles.value.length === 0) {
    showMessage('请选择文件', 'error')
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('file', file)
    })
    formData.append('knowledge_dir', 'knowledge')
    formData.append('collection_name', collectionName.value)

    const response = await fetch(`/api/v1/knowledge/upload/${collectionName.value}`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(await response.text())
    }

    const result = await response.json()
    showMessage(`成功处理 ${result.chunks_processed} 个文档块`, 'success')
    selectedFiles.value = []
    
    if (fileInput.value) {
      fileInput.value.value = ''
    }

    await loadCollections()

  } catch (error) {
    console.error('上传失败:', error)
    showMessage('文件处理失败', 'error')
  } finally {
    uploading.value = false
  }
}

const addFileToCollection = async () => {
  if (!singleFile.value) {
    showMessage('请选择文件', 'error')
    return
  }

  uploading.value = true

  try {
    const formData = new FormData()
    formData.append('file', singleFile.value)
    formData.append('knowledge_dir', 'knowledge')
    formData.append('collection_name', currentCollection.value)

    const response = await fetch(`/api/v1/knowledge/upload/${currentCollection.value}`, {
      method: 'POST',
      body: formData
    })

    if (!response.ok) {
      throw new Error(await response.text())
    }

    const result = await response.json()
    showMessage(`成功添加文件`, 'success')
    singleFile.value = null
    showAddFile.value = false
    
    await loadCollectionInfo(currentCollection.value)
    await loadFilesByCollection(currentCollection.value)

  } catch (error) {
    console.error('添加文件失败:', error)
    showMessage('文件处理失败', 'error')
  } finally {
    uploading.value = false
  }
}

const search = async () => {
  if (!searchQuery.value.trim()) {
    showMessage('请输入搜索关键词', 'error')
    return
  }

  searching.value = true
  searched.value = true

  try {
    const response = await fetch('/api/v1/knowledge/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        query: searchQuery.value,
        collection_name: currentCollection.value || collectionName.value,
        limit: 5
      })
    })

    if (!response.ok) {
      throw new Error('搜索请求失败')
    }

    const data = await response.json()
    searchResults.value = data.results || []

    if (searchResults.value.length === 0) {
      showMessage('未找到相关结果', 'info')
    }

  } catch (error) {
    console.error('搜索失败:', error)
    showMessage('搜索失败', 'error')
  } finally {
    searching.value = false
  }
}

const selectCollection = async (name: string) => {
  currentCollection.value = name
  collectionName.value = name
  searchResults.value = []
  searched.value = false
  currentLevel.value = 'files'
  
  await loadCollectionInfo(name)
  await loadFilesByCollection(name)
}

const selectFile = (file: FileData) => {
  currentFile.value = file.name
  chunks.value = file.chunks
  currentLevel.value = 'chunks'
}

const goToLevel = async (level: Level) => {
  if (level === 'collections') {
    currentLevel.value = 'collections'
    currentCollection.value = ''
    currentFile.value = ''
    files.value = []
    chunks.value = []
  } else if (level === 'files') {
    currentLevel.value = 'files'
    currentFile.value = ''
    chunks.value = []
  }
}

const loadCollections = async () => {
  try {
    const response = await fetch('/api/v1/knowledge/collections')
    const result = await response.json()
    
    if (result.success) {
      collections.value = result.collections || []
    }
  } catch (error) {
    console.error('加载集合列表失败:', error)
  }
}

const loadCollectionInfo = async (name: string) => {
  try {
    const response = await fetch(`/api/v1/knowledge/collection/${name}/info`)
    const result = await response.json()
    
    if (result.success) {
      selectedCollectionInfo.value = result.info
    }
  } catch (error) {
    console.error('加载集合信息失败:', error)
  }
}

const loadFilesByCollection = async (collectionName: string) => {
  try {
    const response = await fetch(`/api/v1/knowledge/collection/${collectionName}/points`)
    const result = await response.json()
    
    if (result.success && result.points) {
      const fileMap = new Map<string, FileData>()
      
      for (const point of result.points) {
        const source = point.payload?.source || 'unknown'
        const extension = source.split('.').pop()?.toLowerCase() || 'txt'
        
        if (!fileMap.has(source)) {
          fileMap.set(source, {
            name: source,
            extension: extension,
            chunks: []
          })
        }
        
        fileMap.get(source)!.chunks.push({
          id: point.id,
          page_content: point.payload?.page_content || point.payload?.content || '',
          source: source,
          file_type: point.payload?.file_type,
          section: point.payload?.section,
          headers: point.payload?.headers || [],
          chunk_index: point.payload?.chunk_index || 0,
          total_chunks: point.payload?.total_chunks,
          processed_at: point.payload?.processed_at,
          content_length: point.payload?.content_length
        })
      }
      
      files.value = Array.from(fileMap.values()).map(file => ({
        ...file,
        chunks: file.chunks.sort((a, b) => a.chunk_index - b.chunk_index)
      }))
    }
  } catch (error) {
    console.error('加载文件列表失败:', error)
  }
}

const rebuildCollection = async () => {
  if (!currentCollection.value) {
    showMessage('请先选择集合', 'error')
    return
  }

  loading.value = true

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/rebuild`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ clear_existing: true })
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage(`成功处理 ${result.documents_processed} 个文档`, 'success')
      await loadCollectionInfo(currentCollection.value)
      if (currentLevel.value === 'files') {
        await loadFilesByCollection(currentCollection.value)
      }
    } else {
      showMessage('重建失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('重建集合失败:', error)
    showMessage('重建集合失败', 'error')
  } finally {
    loading.value = false
  }
}

const createCollection = async () => {
  if (!newCollectionName.value.trim()) {
    showMessage('请输入集合名称', 'error')
    return
  }

  try {
    const response = await fetch('/api/v1/knowledge/collection/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        collection_name: newCollectionName.value
      })
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('集合创建成功', 'success')
      showAddCollection.value = false
      newCollectionName.value = ''
      await loadCollections()
    } else {
      showMessage('创建失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('创建集合失败:', error)
    showMessage('创建集合失败', 'error')
  }
}

const deleteCollection = async (name: string) => {
  if (!confirm(`确定要删除集合 "${name}" 吗？此操作不可恢复。`)) {
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${name}`, {
      method: 'DELETE'
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('集合删除成功', 'success')
      await loadCollections()
      if (currentCollection.value === name) {
        goToLevel('collections')
      }
    } else {
      showMessage('删除失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('删除集合失败:', error)
    showMessage('删除集合失败', 'error')
  }
}

const deleteFile = async (fileName: string) => {
  if (!confirm(`确定要删除文件 "${fileName}" 吗？`)) {
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/source/${fileName}`, {
      method: 'DELETE'
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('文件删除成功', 'success')
      await loadCollectionInfo(currentCollection.value)
      await loadFilesByCollection(currentCollection.value)
    } else {
      showMessage('删除失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('删除文件失败:', error)
    showMessage('删除文件失败', 'error')
  }
}

const viewFileChunks = (file: FileData) => {
  selectFile(file)
}

const reuploadFile = async (file: FileData) => {
  if (!confirm(`确定要重新上传 "${file.name}" 吗？这将删除现有分块并重新处理。`)) {
    return
  }

  loading.value = true

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/file/${file.name}`, {
      method: 'DELETE'
    })

    if (!response.ok) {
      throw new Error('删除失败')
    }

    showMessage('请选择新文件进行上传', 'info')
    showAddFile.value = true

  } catch (error) {
    console.error('重新上传失败:', error)
    showMessage('重新上传失败', 'error')
  } finally {
    loading.value = false
  }
}

const editCollection = (collection: CollectionInfo) => {
  editingCollection.value = collection
  newCollectionNameForEdit.value = collection.name
  showEditCollectionModal.value = true
}

const saveCollectionEdit = async () => {
  if (!editingCollection.value || !newCollectionNameForEdit.value.trim()) {
    showMessage('集合名称不能为空', 'error')
    return
  }

  if (newCollectionNameForEdit.value === editingCollection.value.name) {
    showEditCollectionModal.value = false
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${editingCollection.value.name}/rename`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        new_name: newCollectionNameForEdit.value
      })
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('集合重命名成功', 'success')
      showEditCollectionModal.value = false
      
      if (currentCollection.value === editingCollection.value.name) {
        currentCollection.value = newCollectionNameForEdit.value
        collectionName.value = newCollectionNameForEdit.value
      }
      
      await loadCollections()
    } else {
      showMessage('重命名失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('重命名集合失败:', error)
    showMessage('重命名集合失败', 'error')
  }
}

const exportCollection = async () => {
  if (!currentCollection.value) {
    showMessage('请先选择集合', 'error')
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/points`)
    const result = await response.json()
    
    if (result.success && result.points) {
      const exportData = {
        collection: currentCollection.value,
        exported_at: new Date().toISOString(),
        total_points: result.total,
        points: result.points.map((point: any) => ({
          content: point.payload?.page_content || point.payload?.content || '',
          source: point.payload?.source || '',
          section: point.payload?.section || '',
          chunk_index: point.payload?.chunk_index || 0,
          metadata: {
            file_type: point.payload?.file_type || '',
            processed_at: point.payload?.processed_at || '',
            content_length: point.payload?.content_length || 0
          }
        }))
      }

      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${currentCollection.value}_export.json`
      a.click()
      URL.revokeObjectURL(url)
      
      showMessage('数据导出成功', 'success')
    }

  } catch (error) {
    console.error('导出失败:', error)
    showMessage('导出失败', 'error')
  }
}

const toggleChunkSelection = (chunkId: string) => {
  const index = selectedChunks.value.indexOf(chunkId)
  if (index > -1) {
    selectedChunks.value.splice(index, 1)
  } else {
    selectedChunks.value.push(chunkId)
  }
  selectAllChunks.value = selectedChunks.value.length === chunks.value.length && chunks.value.length > 0
}

const toggleSelectAll = () => {
  if (selectAllChunks.value) {
    selectedChunks.value = chunks.value.map(chunk => chunk.id)
  } else {
    selectedChunks.value = []
  }
}

const deleteSelectedChunks = async () => {
  if (selectedChunks.value.length === 0) return
  
  if (!confirm(`确定要删除选中的 ${selectedChunks.value.length} 个分块吗？`)) {
    return
  }

  loading.value = true

  try {
    const deletePromises = selectedChunks.value.map(chunkId => 
      fetch(`/api/v1/knowledge/collection/${currentCollection.value}/chunk/${chunkId}`, {
        method: 'DELETE'
      })
    )

    await Promise.all(deletePromises)
    
    showMessage(`成功删除 ${selectedChunks.value.length} 个分块`, 'success')
    selectedChunks.value = []
    selectAllChunks.value = false
    
    await loadCollectionInfo(currentCollection.value)
    await loadFilesByCollection(currentCollection.value)
    
    const updatedFile = files.value.find(f => f.name === currentFile.value)
    if (updatedFile) {
      chunks.value = updatedFile.chunks
    }

  } catch (error) {
    console.error('批量删除失败:', error)
    showMessage('批量删除失败', 'error')
  } finally {
    loading.value = false
  }
}

const addChunk = () => {
  newChunkContent.value = ''
  selectedChunk.value = null
  showAddChunkModal.value = true
}

const saveNewChunk = async () => {
  if (!newChunkContent.value.trim()) {
    showMessage('内容不能为空', 'error')
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/chunk/add`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content: newChunkContent.value,
        source: currentFile.value || 'manual_addition',
        chunk_index: chunks.value.length
      })
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('分块添加成功', 'success')
      showAddChunkModal.value = false
      
      await loadCollectionInfo(currentCollection.value)
      await loadFilesByCollection(currentCollection.value)
      
      if (currentFile.value) {
        const updatedFile = files.value.find(f => f.name === currentFile.value)
        if (updatedFile) {
          chunks.value = updatedFile.chunks
        }
      }
    } else {
      showMessage('添加失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('添加分块失败:', error)
    showMessage('添加分块失败', 'error')
  }
}

const deleteChunk = async (chunk: ChunkData) => {
  if (!confirm('确定要删除这个分块吗？')) {
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/chunk/${chunk.id}`, {
      method: 'DELETE'
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('分块删除成功', 'success')
      await loadCollectionInfo(currentCollection.value)
      await loadFilesByCollection(currentCollection.value)
      if (currentLevel.value === 'chunks') {
        const updatedFile = files.value.find(f => f.name === currentFile.value)
        if (updatedFile) {
          chunks.value = updatedFile.chunks
        }
      }
    } else {
      showMessage('删除失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('删除分块失败:', error)
    showMessage('删除分块失败', 'error')
  }

  activeMenu.value = null
}

const editChunk = (chunk: ChunkData) => {
  selectedChunk.value = chunk
  editingContent.value = chunk.page_content
  modalMode.value = 'edit'
  showModal.value = true
  activeMenu.value = null
}

const saveChunkEdit = async () => {
  if (!selectedChunk.value || !editingContent.value.trim()) {
    showMessage('内容不能为空', 'error')
    return
  }

  try {
    const response = await fetch(`/api/v1/knowledge/collection/${currentCollection.value}/chunk/${selectedChunk.value.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        content: editingContent.value
      })
    })

    const result = await response.json()
    
    if (result.success) {
      showMessage('内容更新成功', 'success')
      showModal.value = false
      await loadFilesByCollection(currentCollection.value)
      const updatedFile = files.value.find(f => f.name === currentFile.value)
      if (updatedFile) {
        chunks.value = updatedFile.chunks
      }
    } else {
      showMessage('更新失败: ' + result.message, 'error')
    }

  } catch (error) {
    console.error('更新分块失败:', error)
    showMessage('更新分块失败', 'error')
  }
}

const getFileIcon = (ext: string) => {
  const icons: Record<string, string> = {
    'pdf': '📕',
    'docx': '📘',
    'txt': '📝',
    'csv': '📊',
    'md': '📄',
    'xlsx': '📗',
    'xls': '📗'
  }
  return icons[ext] || '📄'
}

const toggleMenu = (chunkId: string) => {
  activeMenu.value = activeMenu.value === chunkId ? null : chunkId
}

const showChunkDetails = (chunk: ChunkData) => {
  selectedChunk.value = chunk
  modalMode.value = 'view'
  showModal.value = true
  activeMenu.value = null
}

const showChunkMetadata = (chunk: ChunkData) => {
  metadataChunk.value = chunk
  showMetadataModal.value = true
  activeMenu.value = null
}

const closeMetadataModal = () => {
  showMetadataModal.value = false
  metadataChunk.value = null
}

const copyContent = (chunk: ChunkData) => {
  navigator.clipboard.writeText(chunk.page_content)
  showMessage('内容已复制到剪贴板', 'success')
  activeMenu.value = null
}

const closeModal = () => {
  showModal.value = false
  selectedChunk.value = null
  editingContent.value = ''
  modalMode.value = 'view'
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('.chunk-menu')) {
    activeMenu.value = null
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  await loadCollections()
  if (collections.value.length > 0) {
    collectionName.value = collections.value[0].name
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.knowledge-base-container {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.nav-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.page-header {
  margin-bottom: 16px;
}

.page-header h1 {
  font-size: 28px;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
}

.breadcrumb {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 20px;
}

.breadcrumb-item {
  color: #666;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}

.breadcrumb-item:hover {
  background: #e0e0e0;
}

.breadcrumb-item.active {
  color: #667eea;
  font-weight: 600;
}

.breadcrumb-separator {
  margin: 0 8px;
  color: #999;
}

.main-content {
  display: flex;
  gap: 20px;
}

.level-collections,
.level-files,
.level-chunks {
  flex: 1;
  min-width: 0;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 20px;
}

.card h2 {
  font-size: 18px;
  color: #1a1a1a;
  margin-bottom: 16px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h2 {
  margin-bottom: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.file-meta {
  display: flex;
  gap: 12px;
}

.meta-tag {
  background: #f0f0f0;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
  color: #666;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #667eea;
  background: #f8f8ff;
}

.upload-area.small {
  padding: 20px;
}

.upload-placeholder .upload-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.upload-placeholder p {
  color: #666;
  margin: 8px 0;
}

.upload-placeholder .hint {
  font-size: 12px;
  color: #999;
}

.uploading {
  padding: 40px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.selected-files {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.selected-files ul {
  list-style: none;
  padding: 0;
}

.selected-files li {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #f8f8ff;
  border-radius: 8px;
  margin-bottom: 8px;
}

.file-icon {
  margin-right: 8px;
}

.remove-btn {
  margin-left: auto;
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 18px;
}

.remove-btn:hover {
  color: #f56c6c;
}

.collection-input {
  margin: 16px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.collection-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.upload-btn,
.add-btn,
.back-btn,
.rebuild-btn {
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  border: none;
}

.upload-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.upload-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.upload-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.add-btn {
  background: #52c41a;
  color: white;
}

.add-btn:hover {
  background: #73d13d;
}

.back-btn {
  background: #f0f0f0;
  color: #666;
}

.back-btn:hover {
  background: #e0e0e0;
}

.rebuild-btn {
  background: #faad14;
  color: white;
  margin-top: 16px;
}

.rebuild-btn:hover:not(:disabled) {
  background: #ffc53d;
}

.rebuild-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.collections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.collections-section {
  min-height: 300px;
}

.collection-card {
  display: flex;
  align-items: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  position: relative;
}

.collection-card:hover {
  background: #f0f0ff;
  border-color: #667eea;
  transform: translateY(-2px);
}

.collection-icon {
  font-size: 32px;
  margin-right: 12px;
}

.collection-info {
  flex: 1;
}

.collection-name {
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 4px;
}

.collection-count {
  font-size: 12px;
  color: #999;
}

.collection-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.action-btn:hover {
  opacity: 1;
}

.action-btn.delete:hover {
  color: #f56c6c;
}

.collection-arrow {
  font-size: 20px;
  color: #999;
  margin-left: 8px;
}

.collection-operations {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.files-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.file-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: #fafafa;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  position: relative;
}

.file-card:hover {
  background: #f0f0ff;
  border-color: #667eea;
  transform: translateY(-2px);
}

.file-icon-large {
  font-size: 48px;
  margin-bottom: 12px;
}

.file-info {
  text-align: center;
}

.file-name {
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 4px;
  word-break: break-all;
}

.file-chunks {
  font-size: 12px;
  color: #999;
}

.file-actions {
  position: absolute;
  top: 8px;
  right: 8px;
}

.file-arrow {
  font-size: 20px;
  color: #999;
  margin-top: 12px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 16px;
}

.chunks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  max-height: 600px;
  overflow-y: auto;
  padding: 4px;
}

.chunk-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 16px;
  position: relative;
  transition: all 0.3s;
  border: 1px solid #eee;
  min-height: 150px;
}

.chunk-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.chunk-menu {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

.menu-dots {
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.menu-dots:hover {
  background: #e0e0e0;
}

.menu-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 120px;
  overflow: hidden;
}

.menu-dropdown button {
  display: block;
  width: 100%;
  padding: 10px 16px;
  text-align: left;
  border: none;
  background: none;
  cursor: pointer;
  transition: background 0.2s;
}

.menu-dropdown button:hover {
  background: #f5f5f5;
}

.menu-dropdown button.delete {
  color: #f56c6c;
}

.chunk-content {
  margin-top: 24px;
}

.chunk-preview {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
  max-height: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chunk-footer {
  margin-top: 12px;
  text-align: right;
}

.chunk-index {
  font-size: 12px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 10px;
}

.right-panel {
  width: 350px;
  flex-shrink: 0;
}

.search-section {
  margin-bottom: 20px;
}

.search-box {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.search-box input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.search-box button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s;
}

.search-box button:hover:not(:disabled) {
  transform: translateY(-2px);
}

.search-box button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-results h3 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.result-item {
  background: #f8f8ff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.result-header .source {
  font-weight: 500;
  color: #667eea;
}

.result-header .score {
  font-size: 12px;
  color: #52c41a;
}

.result-content {
  font-size: 13px;
  color: #666;
  line-height: 1.6;
}

.no-results {
  text-align: center;
  color: #999;
  padding: 20px;
}

.info-content {
  font-size: 14px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-item .label {
  color: #666;
}

.info-item .value {
  font-weight: 500;
  color: #1a1a1a;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.status-badge.green {
  background: #f6ffed;
  color: #52c41a;
}

.status-badge.yellow {
  background: #fffbe6;
  color: #faad14;
}

.status-badge.gray {
  background: #f5f5f5;
  color: #999;
}

.no-info {
  color: #999;
  text-align: center;
  padding: 20px;
}

.toast {
  position: fixed;
  bottom: 30px;
  right: 30px;
  padding: 16px 24px;
  border-radius: 8px;
  color: white;
  font-size: 14px;
  z-index: 1000;
  animation: slideIn 0.3s ease;
}

.toast.success {
  background: #52c41a;
}

.toast.error {
  background: #f56c6c;
}

.toast.info {
  background: #667eea;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: modalIn 0.3s ease;
}

.modal-content.small {
  max-width: 400px;
}

@keyframes modalIn {
  from {
    transform: scale(0.9);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.modal-header h3 {
  font-size: 18px;
  color: #1a1a1a;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
}

.modal-close:hover {
  color: #666;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn {
  padding: 10px 20px;
  background: #f0f0f0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: #666;
}

.save-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: white;
}

.detail-section {
  margin-bottom: 20px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-section h4 {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.detail-row {
  display: flex;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.detail-label {
  width: 100px;
  color: #999;
  flex-shrink: 0;
}

.detail-value {
  color: #1a1a1a;
}

.full-content {
  background: #f8f8ff;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

.content-editor {
  width: 100%;
  padding: 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  resize: vertical;
}

.headers-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.header-tag {
  background: #e8f4fd;
  color: #1677ff;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 12px;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.meta-item {
  background: #f8f8ff;
  padding: 12px;
  border-radius: 8px;
}

.meta-label {
  display: block;
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.meta-value {
  font-size: 14px;
  color: #1a1a1a;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #666;
}

.form-group input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f8f8ff;
  border-radius: 8px;
}

.meta-detail {
  padding: 16px;
  background: #f8f8ff;
  border-radius: 8px;
}

.meta-row {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}

.meta-row:last-child {
  border-bottom: none;
}

.meta-row .meta-label {
  width: 120px;
  flex-shrink: 0;
}

.meta-row .meta-value {
  flex: 1;
}
</style>
