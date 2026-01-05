import { defineStore } from 'pinia'
import { useRouter } from 'vue-router'

export interface User {
  username: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null as string | null,
    username: null as string | null,
  }),
  
  getters: {
    isAuthenticated: (state) => !!state.token,
    currentUser: (state) => {
      if (state.username) {
        return { username: state.username }
      }
      return null
    },
  },
  
  actions: {
    login(newToken: string, newUsername: string) {
      this.token = newToken
      this.username = newUsername
    },
    
    logout() {
      this.token = null
      this.username = null
      
      // 跳转到登录页
      const router = useRouter()
      router.push('/login')
    },
    
    getToken() {
      return this.token
    },
    
    getUsername() {
      return this.username
    },
    
    // 检查token是否有效（简单检查）
    isTokenValid() {
      if (!this.token) return false
      
      try {
        // JWT token的简单验证：检查格式和基本结构
        const parts = this.token.split('.')
        return parts.length === 3
      } catch {
        return false
      }
    },
  },
  
  persist: true
})