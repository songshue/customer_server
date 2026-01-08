export interface Reference {
  source: string
  content_preview: string
}

export interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  hasReferences?: boolean
  references?: Reference[]
  isStreaming?: boolean
  streamId?: string
  feedbackSubmitted?: boolean
}

export interface ChatRequest {
  message: string
}

export interface ChatResponse {
  message: string
  code: number
}