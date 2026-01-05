import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { ChatMessage, ChatRequest, ChatResponse, Reference } from '@/types/chat'

export const useChatStore = defineStore('chat', () => {
  // 状态
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const streamingMessage = ref<ChatMessage | null>(null)

  // 添加消息
  const addMessage = (message: ChatMessage) => {
    messages.value.push(message)
  }

  // 添加或更新流式消息
  const addOrUpdateStreamingMessage = (content: string, isComplete: boolean, streamId: string, references?: Reference[]) => {
    console.log(`[DEBUG] chatStore.addOrUpdateStreamingMessage: content=${content.substring(0, 50)}..., isComplete=${isComplete}, streamId=${streamId}`)
    
    if (streamingMessage.value) {
      console.log(`[DEBUG] 更新现有流式消息，current content length: ${streamingMessage.value.content.length}`)
      // 更新现有流式消息
      streamingMessage.value.content = content
      if (isComplete) {
        streamingMessage.value.isStreaming = false
        streamingMessage.value.hasReferences = references && references.length > 0
        streamingMessage.value.references = references || []
        // 完成时添加到消息列表
        messages.value.push(streamingMessage.value)
        console.log(`[DEBUG] 流式消息完成，添加到消息列表，当前消息数: ${messages.value.length}`)
        streamingMessage.value = null
      }
    } else if (!isComplete) {
      console.log(`[DEBUG] 创建新的流式消息`)
      // 创建新的流式消息
      const message: ChatMessage = {
        id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
        type: 'ai',
        content: content,
        timestamp: new Date(),
        isStreaming: true,
        streamId: streamId,
        hasReferences: false,
        references: references || []
      }
      streamingMessage.value = message
      console.log(`[DEBUG] 创建流式消息:`, message)
    }
  }

  // 清空消息
  const clearMessages = () => {
    messages.value = []
    streamingMessage.value = null
  }

  // 发送消息到后端
  const sendMessage = async (message: string): Promise<ChatResponse> => {
    isLoading.value = true
    
    try {
      const requestData: ChatRequest = { message }
      
      const response = await axios.post('/api/chat', requestData, {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 10000
      })
      
      return response.data
    } catch (error) {
      console.error('发送消息失败:', error)
      
      // 如果请求失败，返回默认回复
      return {
        message: '抱歉，我现在遇到了一些问题，请稍后重试或联系人工客服。',
        code: 500
      }
    } finally {
      isLoading.value = false
    }
  }

  return {
    // 状态
    messages,
    isLoading,
    streamingMessage,
    
    // 方法
    addMessage,
    clearMessages,
    sendMessage,
    addOrUpdateStreamingMessage
  }
}, {
  persist: true
})