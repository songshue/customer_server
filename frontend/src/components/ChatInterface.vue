<template>
  <div class="chat-interface">

    <!-- 智能助手导航栏 - 顶层 -->
    <div class="top-navbar">
      <div class="navbar-glass">
        <div class="navbar-content">
          <div class="navbar-left">
            <div class="ai-avatar">
              <div class="avatar-inner">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="aiGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style="stop-color:#667eea"/>
                      <stop offset="100%" style="stop-color:#764ba2"/>
                    </linearGradient>
                  </defs>
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#aiGradient)"/>
                  <path d="M2 17L12 22L22 17" stroke="url(#aiGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 12L12 17L22 12" stroke="url(#aiGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
            <div class="header-text">
              <h2 class="ai-title">智能助手</h2>
              <p class="ai-subtitle">{{ connectionStatusText }}</p>
            </div>
          </div>
          <div class="navbar-right">
            <div class="status-indicator" :class="connectionStatusClass">
              <div class="status-dot"></div>
              <span class="status-text">{{ connectionStatusText }}</span>
            </div>
            <n-button type="info" size="tiny" @click="goToKnowledge" class="knowledge-btn">
              知识库管理
            </n-button>
            <n-button type="error" size="tiny" @click="handleLogout" class="logout-btn">
              退出
            </n-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 主内容区域 - 两列布局 -->
    <div class="main-content">
      <!-- 左侧会话历史 -->
      <div class="sidebar-section">
        <SessionSidebar 
          @newSession="handleNewSession"
          @sessionClick="handleSessionClick"
          @updateCollapsed="handleSidebarCollapsed"
        />
      </div>

      <!-- 右侧聊天区域 -->
      <div class="chat-section">
        <!-- 连接状态提示 -->
        <div v-if="!isConnected && connectionStatus !== 'connecting'" class="connection-warning">
          <div class="warning-glass">
            <div class="warning-content">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#F56C6C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 17L12 22L22 17" stroke="#F56C6C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#F56C6C" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span>{{ connectionWarningText }}</span>
              <n-button size="small" type="primary" @click="reconnect" class="reconnect-btn">
                重新连接
              </n-button>
            </div>
          </div>
        </div>

        <!-- 消息列表 -->
        <div class="chat-messages" ref="messagesContainer">
        <div v-if="allMessages && allMessages.length === 0" class="welcome-container">
          <div class="welcome-content">
            <div class="welcome-avatar">
              <svg width="80" height="80" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <linearGradient id="welcomeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#667eea"/>
                    <stop offset="100%" style="stop-color:#764ba2"/>
                  </linearGradient>
                </defs>
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#welcomeGradient)"/>
                <path d="M2 17L12 22L22 17" stroke="url(#welcomeGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="url(#welcomeGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h1 class="welcome-title">您好，我是智能助手</h1>
            <p class="welcome-subtitle">我可以帮您解答问题、提供建议，或者进行友好的对话</p>
            
            <div class="suggestion-cards">
              <div class="suggestion-card" @click="handleSuggestionClick('你好，请介绍一下自己')">
                <div class="card-icon">👋</div>
                <div class="card-text">你好，请介绍一下自己</div>
              </div>
              <div class="suggestion-card" @click="handleSuggestionClick('你能帮我做什么？')">
                <div class="card-icon">💡</div>
                <div class="card-text">你能帮我做什么？</div>
              </div>
              <div class="suggestion-card" @click="handleSuggestionClick('推荐一些学习资源')">
                <div class="card-icon">📚</div>
                <div class="card-text">推荐一些学习资源</div>
              </div>
            </div>
          </div>
        </div>

        <div v-for="message in allMessages" :key="message.id" class="message-item" :class="`message-${message.type}`">
          <div class="message-content">
            <div class="message-avatar">
              <div v-if="message.type === 'user'" class="user-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <circle cx="12" cy="7" r="4" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div v-else class="ai-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="aiMessageGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style="stop-color:#667eea"/>
                      <stop offset="100%" style="stop-color:#764ba2"/>
                    </linearGradient>
                  </defs>
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#aiMessageGradient)"/>
                  <path d="M2 17L12 22L22 17" stroke="url(#aiMessageGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 12L12 17L22 12" stroke="url(#aiMessageGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
            <div class="message-bubble">
              <div class="message-text" v-html="formatMessageContent(message.content)"></div>
              <div v-if="message.isStreaming" class="streaming-indicator">
                <div class="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span class="typing-text">正在输入...</span>
              </div>
              <div v-if="message.hasReferences" class="references-section">
                <div class="references-header">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <span>参考文档</span>
                </div>
                <div class="references-content">
                  <div v-for="(ref, index) in message.references" :key="index" class="reference-item">
                    <span class="reference-number">{{ index + 1 }}.</span>
                    <span class="reference-source">{{ ref.source }}</span>
                    <div class="reference-preview">{{ ref.content_preview }}</div>
                  </div>
                </div>
              </div>
              <div class="message-time">{{ formatTime(message.timestamp) }}</div>
            </div>
          </div>
          <!-- 反馈按钮 - 仅显示在AI消息下方 -->
          <div v-if="message.type === 'ai'" class="feedback-section">
            <div class="feedback-buttons">
              <button 
                class="feedback-btn like-btn" 
                @click="handleFeedback(message.id, 5, 'like')"
                :disabled="message.feedbackSubmitted"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                </svg>
                <span>满意</span>
              </button>
              <button 
                class="feedback-btn dislike-btn" 
                @click="handleFeedback(message.id, 1, 'dislike')"
                :disabled="message.feedbackSubmitted"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                  <path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0L12 2.69z"/>
                </svg>
                <span>不满意</span>
              </button>
            </div>
            <div v-if="message.feedbackSubmitted" class="feedback-thankyou">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
              </svg>
              <span>感谢您的反馈</span>
            </div>
          </div>
        </div>



        <!-- 正在输入指示器 -->
        <div v-if="isTyping" class="message-item message-ai">
          <div class="message-content">
            <div class="message-avatar">
              <div class="ai-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="aiTypingGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style="stop-color:#667eea"/>
                      <stop offset="100%" style="stop-color:#764ba2"/>
                    </linearGradient>
                  </defs>
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="url(#aiTypingGradient)"/>
                  <path d="M2 17L12 22L22 17" stroke="url(#aiTypingGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                  <path d="M2 12L12 17L22 12" stroke="url(#aiTypingGradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
            </div>
            <div class="message-bubble">
              <div class="typing-animation">
                <div class="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span class="typing-text">正在思考中...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区域 -->
      <div class="chat-input">
        <div class="input-container">
          <div class="input-wrapper">
            <n-input
              v-model:value="inputMessage"
              type="textarea"
              :rows="3"
              placeholder="请输入您的问题..."
              :disabled="isTyping"
              @keydown="handleEnterKey"
              resize="none"
              class="message-input"
            />
          </div>
          <div class="send-wrapper">
            <n-button 
              type="primary" 
              :loading="isTyping"
              :disabled="!inputMessage.trim() || isTyping"
              @click="sendMessage"
              class="send-button"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <line x1="22" y1="2" x2="11" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <polygon points="22,2 15,22 11,13 2,9 22,2" fill="currentColor"/>
              </svg>
              <span class="send-text">发送</span>
            </n-button>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, useMessage } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useSessionsStore, type Session } from '@/stores/sessions'
import { useChatStore } from '@/stores/chat'
import { websocketManager, type ConnectionStatus, type WebSocketMessage } from '@/utils/websocket'
import type { ChatMessage } from '@/types/chat'
import type { Reference } from '@/types/chat'
import SessionSidebar from './SessionSidebar.vue'

// 获取 Naive UI 消息实例
const message = useMessage()

const router = useRouter()
const authStore = useAuthStore()
const sessionsStore = useSessionsStore()
const chatStore = useChatStore()

// 响应式数据
const inputMessage = ref('')
const isTyping = ref(false)
const messagesContainer = ref<HTMLElement>()
const connectionStatus = ref<ConnectionStatus>('disconnected')
const isSending = ref(false)
const sidebarCollapsed = ref(false)
const streamingMessageId = ref<string | null>(null)
const currentStreamContent = ref('')
const isStreamComplete = ref(false)

// 计算属性
const isConnected = computed(() => connectionStatus.value === 'connected')
const allMessages = computed(() => {
  // 如果有流式消息，需要显示它
  const baseMessages = chatStore.messages
  const streamingMessage = chatStore.streamingMessage
  
  if (streamingMessage) {
    return [...baseMessages, streamingMessage]
  }
  
  return baseMessages
})
const connectionStatusClass = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return 'status-connected'
    case 'connecting': return 'status-connecting'
    case 'reconnecting': return 'status-reconnecting'
    case 'error': return 'status-error'
    default: return 'status-disconnected'
  }
})

const connectionStatusText = computed(() => {
  switch (connectionStatus.value) {
    case 'connected': return '已连接'
    case 'connecting': return '连接中...'
    case 'reconnecting': return '重连中...'
    case 'error': return '连接错误'
    default: return '已断开'
  }
})

const connectionWarningText = computed(() => {
  switch (connectionStatus.value) {
    case 'error': return '连接出现错误，请检查网络后重试'
    case 'disconnected': return '连接已断开，请重新连接'
    default: return '连接异常，请重试'
  }
})

// 格式化时间
const formatTime = (timestamp: Date | string) => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  }).format(date)
}

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick()
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 格式化消息内容（处理换行和引用）
const formatMessageContent = (content: string) => {
  return content.replace(/\n/g, '<br>')
}

// 处理流式消息更新
const handleStreamMessage = (messageId: string, content: string, isComplete: boolean) => {
  console.log(`[DEBUG] 收到流式消息: messageId=${messageId}, content=${content.substring(0, 50)}..., isComplete=${isComplete}`)
  
  streamingMessageId.value = messageId
  currentStreamContent.value = content
  isStreamComplete.value = isComplete
  
  // 检查是否已存在引用信息
  const hasReferences = checkHasReferences(content)
  const references = hasReferences ? extractReferences(content) : []
  
  console.log(`[DEBUG] 更新流式消息到 chatStore: content.length=${content.length}, hasReferences=${hasReferences}`)
  
  // 使用 chatStore 管理流式消息
  chatStore.addOrUpdateStreamingMessage(content, isComplete, messageId, references)
  
  console.log(`[DEBUG] chatStore.streamingMessage:`, chatStore.streamingMessage)
  
  // 如果流式消息完成，重置打字机状态
  if (isComplete) {
    isTyping.value = false
    streamingMessageId.value = null
    currentStreamContent.value = ''
    isStreamComplete.value = false
    console.log(`[DEBUG] 流式消息完成，重置状态`)
  }
}

// 检查内容是否包含引用
const checkHasReferences = (content: string): boolean => {
  return content.includes('**参考文档:**')
}

// 提取引用信息
const extractReferences = (content: string): Reference[] => {
  const references: Reference[] = []
  const lines = content.split('\n')
  let inReferenceSection = false
  
  for (const line of lines) {
    if (line.includes('**参考文档:**')) {
      inReferenceSection = true
      continue
    }
    
    if (inReferenceSection) {
      // 解析引用行格式：数字. 源文件名\n   内容预览
      const refMatch = line.match(/^(\d+)\.\s+(.+)\s*\n\s+(.+)/)
      if (refMatch) {
        references.push({
          source: refMatch[2],
          content_preview: refMatch[3]
        })
      }
    }
  }
  
  return references
}

// 解析引用信息
const parseReferences = (content: string): { text: string; references: Reference[] } => {
  const lines = content.split('\n')
  const textLines: string[] = []
  const references: Reference[] = []
  
  let inReferenceSection = false
  
  for (const line of lines) {
    if (line.includes('**参考文档:**')) {
      inReferenceSection = true
      continue
    }
    
    if (inReferenceSection) {
      // 解析引用行格式：数字. 源文件名\n   内容预览
      const refMatch = line.match(/^(\d+)\.\s+(.+)\s*\n\s+(.+)/)
      if (refMatch) {
        references.push({
          source: refMatch[2],
          content_preview: refMatch[3]
        })
      }
    } else {
      textLines.push(line)
    }
  }
  
  return {
    text: textLines.join('\n'),
    references: references
  }
}

// 添加消息到列表
const addMessage = (content: string, type: 'user' | 'ai', timestamp?: string, hasReferences?: boolean, references?: Reference[]) => {
  const message: ChatMessage = {
    id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    type,
    content,
    timestamp: timestamp ? new Date(timestamp) : new Date(),
    hasReferences,
    references
  }
  chatStore.addMessage(message)
  scrollToBottom()
}

// 发送消息
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || isSending.value || !isConnected.value) return

  // 清空输入框
  inputMessage.value = ''
  isSending.value = true
  isTyping.value = true

  try {
    // 添加用户消息
    addMessage(message, 'user')

    // 通过WebSocket发送消息
    const success = websocketManager.sendMessage(message)
    if (!success) {
      // message.error('发送失败，请检查连接状态')
      isTyping.value = false
    }

  } catch (error) {
    // message.error('发送失败，请稍后重试')
    console.error('发送消息失败:', error)
  } finally {
    // isSending和isTyping的状态由WebSocket消息处理控制
  }
}

// 处理Enter键发送
const handleEnterKey = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

// 重新连接
const reconnect = async () => {
  try {
    await websocketManager.reconnect()
    message.success('重新连接成功')
  } catch (error) {
    message.error('重新连接失败')
    console.error('重连失败:', error)
  }
}

// 退出登录
const handleLogout = () => {
  websocketManager.disconnect()
  sessionsStore.clearSessions()
  authStore.logout()
}

const goToKnowledge = () => {
  router.push('/knowledge')
}

// 处理新建会话
const handleNewSession = async () => {
  await sessionsStore.createSession()
  chatStore.clearMessages()
  
  // 重置WebSocket连接
  websocketManager.disconnect()
  
  message.success('已创建新会话')
}

// 处理会话点击
const handleSessionClick = (session: Session) => {
  sessionsStore.selectSession(session.session_id)
  
  // 加载会话历史
  loadSessionHistory(session.session_id)
  
  message.info(`已切换到会话: ${formatSessionTime(session.start_time)}`)
}

// 加载会话历史
const loadSessionHistory = async (_sessionId: string) => {
  try {
    // 这里应该调用API获取会话历史
    // const history = await sessionsStore.getSessionHistory(_sessionId)
    
    // 临时清空消息
    chatStore.clearMessages()
    
    // 添加欢迎消息
    addMessage('您好！我是智能客服助手，很高兴为您服务。请输入您的问题，我将尽力帮助您。', 'ai')
  } catch (error) {
    console.error('加载会话历史失败:', error)
    message.error('加载会话历史失败')
  }
}

// 处理侧边栏收起状态变化
const handleSidebarCollapsed = (collapsed: boolean) => {
  sidebarCollapsed.value = collapsed
}

// 处理建议卡片点击
const handleSuggestionClick = (suggestion: string) => {
  inputMessage.value = suggestion
  sendMessage()
}

// 格式化会话时间
const formatSessionTime = (timeString: string) => {
  const date = new Date(timeString)
  const now = new Date()
  const diffTime = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) {
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else if (diffDays === 1) {
    return `昨天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  } else {
    return date.toLocaleDateString('zh-CN', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

// 处理用户反馈
const handleFeedback = async (messageId: string, rating: number, type: string) => {
  try {
    // 获取认证token
    const token = authStore.getToken()
    if (!token) {
      message.error('请先登录')
      return
    }
    
    // 调用反馈API
    const response = await fetch('/api/v1/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        message_id: parseInt(messageId),
        session_id: sessionsStore.currentSessionId || '',
        rating: rating,
        comment: type
      })
    })
    
    if (response.ok) {
      // 更新消息状态，标记为已提交反馈
      const messageIndex = chatStore.messages.findIndex(msg => msg.id === messageId)
      if (messageIndex !== -1) {
        chatStore.messages[messageIndex].feedbackSubmitted = true
      }
      
      message.success('感谢您的反馈')
    } else {
      const errorData = await response.json()
      message.error(`提交反馈失败: ${errorData.detail || '未知错误'}`)
    }
  } catch (error) {
    console.error('提交反馈失败:', error)
    message.error('提交反馈失败，请稍后重试')
  }
}

// 处理WebSocket消息
const handleWebSocketMessage = (message: WebSocketMessage) => {
  switch (message.type) {
    case 'connected':
      // 连接成功，如果没有当前会话，创建或选择一个会话
      if (!sessionsStore.currentSessionId) {
        if (sessionsStore.sessions.length > 0) {
          sessionsStore.selectSession(sessionsStore.sessions[0].session_id)
        } else {
          // 如果没有会话，创建一个新会话
          sessionsStore.createSession()
        }
      }
      // 显示欢迎消息
      addMessage('您好！我是智能客服助手，很高兴为您服务。请输入您的问题，我将尽力帮助您。', 'ai', message.timestamp)
      break
    case 'message':
      // 用户消息确认
      if (message.sender === 'user') {
        // 用户消息已经在本地添加了，这里不需要重复添加
      }
      break
    case 'response':
      // AI回复消息
      const hasReferences = message.has_references || false
      if (hasReferences) {
        // 解析引用信息
        const parsed = parseReferences(message.content || '')
        addMessage(parsed.text, 'ai', message.timestamp, hasReferences, parsed.references)
      } else {
        addMessage(message.content || '', 'ai', message.timestamp)
      }
      break
    case 'error':
      // 错误消息
      console.error('WebSocket错误:', message.message)
      break
  }
  isTyping.value = false
  isSending.value = false
}

// 处理连接状态变化
const handleConnectionStatusChange = (status: ConnectionStatus) => {
  connectionStatus.value = status
  
  switch (status) {
    case 'connected':
      isTyping.value = false
      isSending.value = false
      break
    case 'disconnected':
    case 'error':
      isTyping.value = false
      isSending.value = false
      message.warning('连接已断开')
      break
  }
}

// 组件挂载时建立WebSocket连接
onMounted(async () => {
  // 检查认证状态
  if (!authStore.isAuthenticated) {
    router.push('/login')
    return
  }

  try {
    const token = authStore.getToken()
    if (!token) {
      router.push('/login')
      return
    }

    // 添加事件监听器
    websocketManager.onMessage(handleWebSocketMessage)
    websocketManager.onStatusChange(handleConnectionStatusChange)
    websocketManager.onStreamMessage(handleStreamMessage)

    // 先加载会话列表
    const sessions = await sessionsStore.fetchSessions()
    
    // 如果没有会话，创建一个新会话
    if (!sessions || sessions.length === 0) {
      await sessionsStore.createSession()
    }

    // 建立WebSocket连接
    await websocketManager.connect(token)

  } catch (error) {
    console.error('初始化失败:', error)
    message.error('初始化失败，请检查网络后重试')
  }

  scrollToBottom()
})

// 组件卸载时清理
onUnmounted(() => {
  websocketManager.removeListeners()
  websocketManager.disconnect()
})
</script>

<style scoped>
.chat-interface {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  position: relative;
  overflow: hidden;
}

.chat-interface::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(circle at 20% 80%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 40% 40%, rgba(120, 119, 198, 0.2) 0%, transparent 50%);
  pointer-events: none;
}

/* 顶层导航栏 */
.top-navbar {
  position: relative;
  z-index: 100;
  padding: 12px 20px;
  backdrop-filter: blur(10px);
}

.navbar-glass {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  padding: 12px 20px;
}

.navbar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.navbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 主内容区域 */
.main-content {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  height: calc(100vh - 72px); /* 减去导航栏高度 */
}

.sidebar-section {
  flex-shrink: 0;
  width: 280px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

.chat-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.02);
}

/* 移除旧的聊天头部样式，使用新的导航栏样式 */

.ai-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.avatar-inner {
  color: white;
}

.header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ai-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.ai-subtitle {
  font-size: 12px;
  color: #666;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 16px;
  font-size: 12px;
}

.status-text {
  font-size: 12px;
  color: #666;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-connected .status-dot {
  background: #52c41a;
}

.status-connecting .status-dot,
.status-reconnecting .status-dot {
  background: #faad14;
  animation: pulse 1s infinite;
}

.status-error .status-dot,
.status-disconnected .status-dot {
  background: #ff4d4f;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.logout-btn {
  border-radius: 6px;
  font-size: 12px;
  padding: 6px 12px;
  height: 28px;
  line-height: 1;
}

.knowledge-btn {
  border-radius: 6px;
  font-size: 12px;
  padding: 6px 12px;
  height: 28px;
  line-height: 1;
  margin-right: 8px;
}

.connection-warning {
  padding: 0 24px 16px;
}

.warning-glass {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 184, 0, 0.3);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(255, 184, 0, 0.2);
}

.warning-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.reconnect-btn {
  border-radius: 8px;
  font-size: 12px;
  padding: 6px 12px;
}

.chat-messages {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  scroll-behavior: smooth;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  padding: 40px 20px;
}

.welcome-content {
  text-align: center;
  max-width: 600px;
  width: 100%;
}

.welcome-avatar {
  margin-bottom: 32px;
  display: flex;
  justify-content: center;
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

.welcome-title {
  font-size: 32px;
  font-weight: 600;
  color: white;
  margin: 0 0 16px 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.welcome-subtitle {
  font-size: 18px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0 0 48px 0;
  line-height: 1.6;
}

.suggestion-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 32px;
}

.suggestion-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: left;
}

.suggestion-card:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
}

.card-icon {
  font-size: 24px;
  margin-bottom: 12px;
}

.card-text {
  font-size: 14px;
  color: white;
  font-weight: 500;
  line-height: 1.4;
}

.message-item {
  display: flex;
  animation: messageSlideIn 0.3s ease-out;
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-content {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  max-width: 80%;
  width: 100%;
}

.message-user .message-content {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.ai-avatar {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.message-bubble {
  background: white;
  padding: 16px 20px;
  border-radius: 18px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  position: relative;
  max-width: 100%;
  word-wrap: break-word;
}

.message-user .message-bubble {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.message-text {
  line-height: 1.6;
  font-size: 15px;
}

.message-time {
  font-size: 12px;
  opacity: 0.6;
  margin-top: 8px;
}

.message-user .message-time {
  text-align: right;
}

/* 反馈按钮样式 */
.feedback-section {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-top: 4px;
  margin-right: 56px;
  gap: 8px;
}

.feedback-buttons {
  display: flex;
  gap: 12px;
}

.feedback-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  color: white;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.feedback-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.feedback-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.feedback-btn.like-btn:hover:not(:disabled) {
  background: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.3);
}

.feedback-btn.dislike-btn:hover:not(:disabled) {
  background: rgba(244, 67, 54, 0.2);
  border-color: rgba(244, 67, 54, 0.3);
}

.feedback-thankyou {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}

.typing-animation {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background: #999;
  border-radius: 50%;
  animation: typingBounce 1.4s infinite ease-in-out;
}

.message-user .typing-dots span {
  background: rgba(255, 255, 255, 0.7);
}

.typing-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typingBounce {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  font-size: 14px;
  color: #666;
  font-style: italic;
}

.message-user .typing-text {
  color: rgba(255, 255, 255, 0.8);
}

/* 打字机效果样式 */
.typewriter {
  position: relative;
  display: inline-block;
}

.cursor {
  display: inline-block;
  width: 2px;
  height: 1.2em;
  background-color: #667eea;
  margin-left: 2px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

.chat-input {
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.2);
}

.input-container {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  max-width: 1000px;
  margin: 0 auto;
}

.input-wrapper {
  flex: 1;
}

.message-input {
  width: 100%;
}

.message-input :deep(.n-input) {
  border-radius: 16px;
  border: 2px solid rgba(102, 126, 234, 0.2);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  transition: all 0.3s ease;
}

.message-input :deep(.n-input__textarea) {
  border-radius: 16px;
  padding: 16px 20px;
  font-size: 15px;
  line-height: 1.6;
  min-height: 60px;
  resize: none;
}

.message-input :deep(.n-input__textarea:focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  background: rgba(255, 255, 255, 0.95);
}

.send-wrapper {
  flex-shrink: 0;
}

.send-button {
  height: 60px;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 600;
  padding: 0 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.send-button:disabled {
  opacity: 0.6;
  transform: none;
}

.send-text {
  font-weight: 600;
}

.references-section {
  margin-top: 16px;
  padding: 16px;
  background: rgba(240, 240, 240, 0.5);
  border-radius: 12px;
  border-left: 4px solid #667eea;
}

.references-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 12px;
}

.references-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reference-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.reference-number {
  font-size: 12px;
  font-weight: 600;
  color: #666;
}

.reference-source {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.reference-preview {
  font-size: 12px;
  color: #666;
  line-height: 1.5;
  padding-left: 12px;
  border-left: 2px solid #ddd;
  margin-top: 4px;
}

.message-user .references-section {
  background: rgba(255, 255, 255, 0.1);
  border-left-color: rgba(255, 255, 255, 0.5);
}

.message-user .references-header {
  color: rgba(255, 255, 255, 0.9);
}

.message-user .reference-number,
.message-user .reference-source,
.message-user .reference-preview {
  color: rgba(255, 255, 255, 0.8);
}

.header-card {
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-icon {
  color: #409EFF;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-connected {
  background: #67C23A;
}

.status-connecting,
.status-reconnecting {
  background: #E6A23C;
  animation: pulse 1s infinite;
}

.status-error,
.status-disconnected {
  background: #F56C6C;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

.status-text {
  font-size: 14px;
  color: #606266;
}

.connection-warning {
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.9);
}

.connection-actions {
  margin-top: 8px;
}

.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.message-item {
  margin-bottom: 20px;
}

.message-content {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message-content.user {
  flex-direction: row-reverse;
}

.message-avatar .n-avatar {
  background: #409EFF;
}

.message-avatar .n-avatar.ai {
  background: #67C23A;
}

.message-bubble {
  max-width: 70%;
  background: white;
  padding: 16px 20px;
  border-radius: 18px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: relative;
}

.message-content.user .message-bubble {
  background: #409EFF;
  color: white;
}

.message-text {
  line-height: 1.6;
  word-wrap: break-word;
}

.message-time {
  font-size: 12px;
  opacity: 0.7;
  margin-top: 8px;
}

.message-content.user .message-time {
  text-align: right;
}

.welcome-message {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.welcome-card {
  text-align: center;
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.welcome-content {
  padding: 40px;
}

.welcome-content h3 {
  margin: 20px 0 10px 0;
  color: #303133;
}

.welcome-content p {
  color: #606266;
  line-height: 1.6;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #909399;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.chat-input {
  padding: 20px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
}

.input-card {
  border: none;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.input-container {
  display: flex;
  gap: 16px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
}

.message-input :deep(.n-input) {
  border-radius: 12px;
}

.message-input :deep(.n-input__textarea) {
  border-radius: 12px;
  border: 2px solid #E4E7ED;
  padding: 12px 16px;
  font-size: 14px;
  line-height: 1.6;
}

.message-input :deep(.n-input__textarea:focus) {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.input-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.send-button {
  height: 120px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  background: #409EFF;
  border-color: #409EFF;
}

.send-button:hover {
  background: #66B1FF;
  border-color: #66B1FF;
}

/* 引用信息样式 */
.references-section {
  margin-top: 12px;
  padding: 12px;
  background: rgba(240, 240, 240, 0.6);
  border-radius: 8px;
  border-left: 3px solid #409EFF;
}

.references-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: #409EFF;
  margin-bottom: 8px;
}

.references-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reference-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.reference-number {
  font-size: 11px;
  font-weight: 600;
  color: #606266;
}

.reference-source {
  font-size: 12px;
  font-weight: 500;
  color: #303133;
}

.reference-preview {
  font-size: 11px;
  color: #606266;
  line-height: 1.4;
  padding-left: 12px;
  border-left: 2px solid #E4E7ED;
  margin-top: 4px;
}

.message-content.user .references-section {
  background: rgba(64, 158, 255, 0.1);
  border-left-color: rgba(255, 255, 255, 0.3);
}

.message-content.user .references-title {
  color: rgba(255, 255, 255, 0.9);
}

.message-content.user .reference-number,
.message-content.user .reference-source,
.message-content.user .reference-preview {
  color: rgba(255, 255, 255, 0.8);
}

</style>