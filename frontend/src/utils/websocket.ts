

export interface Reference {
  source: string
  content_preview: string
}

export interface WebSocketMessage {
  type: string
  content?: string
  message?: string
  sender?: string
  timestamp: string
  has_references?: boolean
  references?: Reference[]
  is_stream?: boolean
  stream_id?: string
  chunk_index?: number
  total_chunks?: number
  is_final?: boolean
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error'

export class WebSocketManager {
  private ws: WebSocket | null = null
  private url: string = ''
  private token: string = ''
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 5
  private reconnectInterval: number = 3000
  private reconnectTimer: NodeJS.Timeout | null = null
  private heartbeatTimer: NodeJS.Timeout | null = null
  private heartbeatInterval: number = 30000
  
  private statusListeners: Array<(status: ConnectionStatus) => void> = []
  private messageListeners: Array<(message: WebSocketMessage) => void> = []
  private errorListeners: Array<(error: Event) => void> = []
  
  // 流式消息存储
  private streamMessages: Map<string, {
    content: string,
    chunks: number,
    totalChunks: number,
    references: Reference[],
    hasReferences: boolean,
    lastUpdate: number
  }> = new Map()
  
  // 流式消息监听器
  private streamListeners: Array<(messageId: string, content: string, isComplete: boolean) => void> = []

  constructor() {}

  /**
   * 添加连接状态监听器
   */
  onStatusChange(callback: (status: ConnectionStatus) => void) {
    this.statusListeners.push(callback)
  }

  /**
   * 添加消息监听器
   */
  onMessage(callback: (message: WebSocketMessage) => void) {
    this.messageListeners.push(callback)
  }

  /**
   * 添加错误监听器
   */
  onError(callback: (error: Event) => void) {
    this.errorListeners.push(callback)
  }

  /**
   * 添加流式消息监听器
   */
  onStreamMessage(callback: (messageId: string, content: string, isComplete: boolean) => void) {
    this.streamListeners.push(callback)
  }

  /**
   * 移除监听器
   */
  removeListeners() {
    this.statusListeners = []
    this.messageListeners = []
    this.errorListeners = []
    this.streamListeners = []
    this.streamMessages.clear()
  }

  /**
   * 获取当前连接状态
   */
  getConnectionStatus(): ConnectionStatus {
    if (!this.ws) return 'disconnected'
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting'
      case WebSocket.OPEN:
        return 'connected'
      case WebSocket.CLOSING:
        return 'reconnecting'
      case WebSocket.CLOSED:
        return 'disconnected'
      default:
        return 'disconnected'
    }
  }

  /**
   * 建立WebSocket连接
   */
  connect(token: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        resolve()
        return
      }

      this.token = token
      this.url = `ws://localhost:8000/api/v1/ws?token=${encodeURIComponent(token)}`

      this.updateStatus('connecting')

      try {
        this.ws = new WebSocket(this.url)

        this.ws.onopen = () => {
          console.log('WebSocket连接已建立')
          this.reconnectAttempts = 0
          this.updateStatus('connected')
          this.startHeartbeat()
          resolve()
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data)
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket连接已关闭:', event.code, event.reason)
          this.updateStatus('disconnected')
          this.stopHeartbeat()
          
          if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect()
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket错误:', error)
          this.updateStatus('error')
          this.errorListeners.forEach(callback => callback(error))
          
          if (this.reconnectAttempts === 0) {
            reject(new Error('WebSocket连接失败'))
          }
        }

      } catch (error) {
        console.error('创建WebSocket连接失败:', error)
        this.updateStatus('error')
        reject(error)
      }
    })
  }

  /**
   * 发送消息
   */
  sendMessage(content: string): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket未连接，无法发送消息')
      return false
    }

    try {
      const message = {
        type: 'message',
        content: content,
        timestamp: new Date().toISOString(),
        enable_multi_agent: true  // 总是启用多Agent模式以支持流式输出
      }
      
      this.ws.send(JSON.stringify(message))
      return true
    } catch (error) {
      console.error('发送消息失败:', error)
      return false
    }
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopReconnect()
    this.stopHeartbeat()
    
    if (this.ws) {
      this.ws.close(1000, '主动断开连接')
      this.ws = null
    }
    
    this.updateStatus('disconnected')
  }

  /**
   * 手动重连
   */
  reconnect(): Promise<void> {
    this.stopReconnect()
    this.disconnect()
    
    if (this.token) {
      return this.connect(this.token)
    }
    
    return Promise.reject(new Error('没有有效的token'))
  }

  /**
   * 处理接收到的消息
   */
  private handleMessage(data: string) {
    try {
      const message: WebSocketMessage = JSON.parse(data)
      console.log('收到WebSocket消息:', message)
      
      // 检查是否是流式消息 - 支持多种格式
      if (message.stream_id && (
        message.is_stream || 
        message.type === 'stream_start' || 
        message.type === 'stream_message' || 
        message.type === 'stream_end'
      )) {
        this.handleStreamMessage(message)
        return
      }
      
      this.messageListeners.forEach(callback => callback(message))
      
      // 处理连接状态消息
      if (message.type === 'connected') {
        console.log('已连接到客服系统')
      } else if (message.type === 'error') {
        console.error(message.message || '发生错误')
      }
    } catch (error) {
      console.error('解析WebSocket消息失败:', error)
    }
  }
  
  /**
   * 处理流式消息
   */
  private handleStreamMessage(message: WebSocketMessage) {
    const { type, stream_id, content, chunk_index, total_chunks, has_references, references } = message
    
    if (!stream_id) return
    
    console.log(`处理流式消息: ${type}, stream_id: ${stream_id}, content: ${content}`)
    
    // 获取或创建流式消息记录
    let streamMessage = this.streamMessages.get(stream_id)
    
    if (type === 'stream_start') {
      // 流式消息开始，创建新的记录
      streamMessage = {
        content: '',
        chunks: 0,
        totalChunks: total_chunks || 1,
        references: references || [],
        hasReferences: has_references || false,
        lastUpdate: Date.now()
      }
      this.streamMessages.set(stream_id, streamMessage)
      
      // 通知监听器开始流式响应
      this.streamListeners.forEach(callback => {
        callback(stream_id, '', false) // 通知开始，但还没有内容
      })
      
    } else if (type === 'stream_message') {
      // 流式消息块，更新内容
      if (!streamMessage) {
        // 如果没有找到开始消息，创建一个
        streamMessage = {
          content: content || '',
          chunks: chunk_index || 0,
          totalChunks: total_chunks || 1,
          references: references || [],
          hasReferences: has_references || false,
          lastUpdate: Date.now()
        }
        this.streamMessages.set(stream_id, streamMessage)
      } else {
        // 更新现有消息
        streamMessage.content += content || ''
        streamMessage.chunks = chunk_index || streamMessage.chunks
        streamMessage.lastUpdate = Date.now()
        
        // 如果有引用信息，更新引用
        if (has_references && references) {
          streamMessage.references = references
          streamMessage.hasReferences = true
        }
      }
      
      // 通知监听器有新的内容
      this.streamListeners.forEach(callback => {
        callback(stream_id, streamMessage?.content || '', false) // 还没完成
      })
      
    } else if (type === 'stream_end') {
      // 流式消息结束
      if (streamMessage) {
        streamMessage.content = content || streamMessage.content
        streamMessage.chunks = chunk_index || streamMessage.chunks
        streamMessage.lastUpdate = Date.now()
        
        // 如果有引用信息，更新引用
        if (has_references && references) {
          streamMessage.references = references
          streamMessage.hasReferences = true
        }
        
        // 通知监听器流式响应完成
        this.streamListeners.forEach(callback => {
          callback(stream_id, streamMessage?.content || content || '', true) // 完成
        })
        
        // 延迟清除流式消息记录
        setTimeout(() => {
          this.streamMessages.delete(stream_id)
        }, 5000)
      } else {
        // 如果没有找到之前的记录，直接处理结束消息
        this.streamListeners.forEach(callback => {
          callback(stream_id, content || '', true)
        })
      }
    }
  }

  /**
   * 更新连接状态
   */
  private updateStatus(status: ConnectionStatus) {
    this.statusListeners.forEach(callback => callback(status))
  }

  /**
   * 安排重连
   */
  private scheduleReconnect() {
    this.reconnectAttempts++
    this.updateStatus('reconnecting')
    
    console.log(`安排重连，第${this.reconnectAttempts}次尝试`)
    
    this.reconnectTimer = setTimeout(() => {
      if (this.token && this.reconnectAttempts <= this.maxReconnectAttempts) {
        this.connect(this.token).catch(error => {
          console.error('重连失败:', error)
        })
      }
    }, this.reconnectInterval * this.reconnectAttempts)
  }

  /**
   * 停止重连
   */
  private stopReconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.reconnectAttempts = 0
  }

  /**
   * 开始心跳
   */
  private startHeartbeat() {
    this.stopHeartbeat()
    
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // 发送心跳消息（可选）
        // this.ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }))
      }
    }, this.heartbeatInterval)
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  /**
   * 检查连接是否活跃
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  /**
   * 获取重连尝试次数
   */
  getReconnectAttempts(): number {
    return this.reconnectAttempts
  }
}

// 创建单例实例
export const websocketManager = new WebSocketManager()