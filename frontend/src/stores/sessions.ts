import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from './auth'

export interface Session {
  session_id: string
  start_time: string
  end_time: string
  message_count: number
  last_message?: string
  status: 'active' | 'ended'
}

export const useSessionsStore = defineStore('sessions', () => {
  const authStore = useAuthStore()
  
  // 状态
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string | null>(null)
  const isLoading = ref(false)
  const isLoadingMore = ref(false)
  const hasMore = ref(true)
  const currentPage = ref(1)
  
  // 计算属性
  const sortedSessions = computed(() => {
    return [...sessions.value].sort((a, b) => 
      new Date(b.start_time).getTime() - new Date(a.start_time).getTime()
    )
  })
  
  const currentSession = computed(() => {
    return sessions.value.find(session => session.session_id === currentSessionId.value)
  })
  
  // 获取会话列表
  const fetchSessions = async (page = 1, limit = 20) => {
    const token = authStore.getToken()
    if (!token) return
    
    try {
      if (page === 1) {
        isLoading.value = true
      } else {
        isLoadingMore.value = true
      }
      
      const response = await axios.get('/api/v1/sessions', {
        headers: {
          'Authorization': `Bearer ${token}`
        },
        params: {
          page,
          limit
        }
      })
      
      const data = response.data
      
      if (page === 1) {
        sessions.value = data.sessions || []
      } else {
        sessions.value.push(...(data.sessions || []))
      }
      
      hasMore.value = data.has_more || false
      currentPage.value = page
      
      return data.sessions || []
    } catch (error) {
      console.error('获取会话列表失败:', error)
      return []
    } finally {
      isLoading.value = false
      isLoadingMore.value = false
    }
  }
  
  // 创建新会话
  const createSession = async (title?: string) => {
    const token = authStore.getToken()
    if (!token) return null
    
    try {
      // 调用API创建新会话
      const response = await axios.post('/api/v1/sessions', 
        title ? { title } : {}, 
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        }
      )
      
      const newSession: Session = {
        session_id: response.data.session_id,
        start_time: response.data.start_time || new Date().toISOString(),
        end_time: response.data.end_time || new Date().toISOString(),
        message_count: 0,
        status: 'active',
        last_message: title || '新会话'
      }
      
      sessions.value.unshift(newSession)
      currentSessionId.value = newSession.session_id
      
      return newSession
    } catch (error) {
      console.error('创建会话失败:', error)
      
      // 如果API调用失败，创建临时会话
      const tempSession: Session = {
        session_id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        message_count: 0,
        status: 'active',
        last_message: title || '新会话'
      }
      
      sessions.value.unshift(tempSession)
      currentSessionId.value = tempSession.session_id
      
      return tempSession
    }
  }
  
  // 选择会话
  const selectSession = (sessionId: string) => {
    currentSessionId.value = sessionId
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session) {
      session.status = 'active'
    }
  }
  
  // 结束会话
  const endSession = (sessionId: string) => {
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session) {
      session.status = 'ended'
      session.end_time = new Date().toISOString()
    }
  }
  
  // 更新会话的最后消息
  const updateSessionLastMessage = (sessionId: string, message: string) => {
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session) {
      session.last_message = message.length > 50 ? message.substring(0, 50) + '...' : message
      session.message_count += 1
    }
  }
  
  // 刷新会话列表
  const refreshSessions = async () => {
    await fetchSessions(1)
  }
  
  // 加载更多会话
  const loadMoreSessions = async () => {
    if (!hasMore.value || isLoadingMore.value) return
    await fetchSessions(currentPage.value + 1)
  }
  
  // 清空会话
  const clearSessions = () => {
    sessions.value = []
    currentSessionId.value = null
    currentPage.value = 1
    hasMore.value = true
  }
  
  // 加载会话（初始化时从持久化存储加载）
  const loadSessions = () => {
    // 在组件挂载时调用，用于从持久化存储恢复状态
    // 实际的数据加载逻辑在 fetchSessions 中
    console.log('从持久化存储加载会话数据')
  }
  
  // 重命名会话
  const renameSession = (sessionId: string, newName: string) => {
    const session = sessions.value.find(s => s.session_id === sessionId)
    if (session) {
      // 临时实现 - 更新last_message作为会话名称
      session.last_message = newName
      // 在实际应用中，这里应该调用API更新会话名称
      console.log(`重命名会话 ${sessionId} 为: ${newName}`)
    }
  }
  
  // 删除会话
  const deleteSession = (sessionId: string) => {
    const index = sessions.value.findIndex(s => s.session_id === sessionId)
    if (index !== -1) {
      sessions.value.splice(index, 1)
      // 如果删除的是当前会话，清除当前会话ID
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = sessions.value.length > 0 ? sessions.value[0].session_id : null
      }
      // 在实际应用中，这里应该调用API删除会话
      console.log(`删除会话 ${sessionId}`)
    }
  }
  
  return {
    // 状态
    sessions,
    currentSessionId,
    isLoading,
    isLoadingMore,
    hasMore,
    currentPage,
    
    // 计算属性
    sortedSessions,
    currentSession,
    
    // 方法
    fetchSessions,
    createSession,
    selectSession,
    endSession,
    updateSessionLastMessage,
    refreshSessions,
    loadMoreSessions,
    clearSessions,
    loadSessions,
    renameSession,
    deleteSession
  }
}, {
  persist: true
})