<template>
  <div class="login-container">
    <n-card class="login-card">
      <div class="login-header">
        <div class="header-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h2>用户登录</h2>
      </div>

      <div class="login-form">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <n-input
            v-model:value="loginForm.username"
            placeholder="请输入用户名"
            size="large"
            @keyup.enter="handleLogin"
            class="username-input"
          />
        </div>

        <div class="form-item">
          <n-button
            type="primary"
            size="large"
            :loading="isLoading"
            @click="handleLogin"
            block
          >
            {{ isLoading ? '登录中...' : '登录' }}
          </n-button>
        </div>
      </div>

      <div class="login-footer">
        <div class="demo-info">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="info-icon">
            <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
            <line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="12" y1="8" x2="12.01" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          这是一个演示系统，请输入任意用户名即可登录
        </div>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NInput, NButton } from 'naive-ui'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// 响应式数据
const isLoading = ref(false)

const loginForm = reactive({
  username: ''
})

// 简单的表单验证
const validateForm = () => {
  if (!loginForm.username.trim()) {
    alert('请输入用户名')
    return false
  }
  
  if (loginForm.username.trim().length < 2 || loginForm.username.trim().length > 20) {
    alert('用户名长度应在2-20个字符之间')
    return false
  }
  
  return true
}

// 登录处理函数
const handleLogin = async () => {
  if (!validateForm()) return
  
  isLoading.value = true

  try {
    // 调用登录接口
    const response = await axios.post('/api/login', {
      username: loginForm.username.trim()
    })

    const { access_token, username } = response.data

    // 使用authStore来管理认证状态
    authStore.login(access_token, username)

    alert(`欢迎，${username}!`)

    // 跳转到聊天页面
    router.push('/chat')

  } catch (error: any) {
    console.error('登录失败:', error)
    
    if (error.response?.data?.detail) {
      alert(error.response.data.detail)
    } else {
      alert('登录失败，请稍后重试')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
  border-radius: 10px;
}

.login-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  margin-bottom: 30px;
}

.header-icon {
  color: #409eff;
}

.login-header h2 {
  margin: 0;
  color: #303133;
  font-weight: 600;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.username-input {
  border-radius: 8px;
}

.username-input :deep(.n-input__input) {
  border-radius: 8px;
}

.username-input :deep(.n-input__textarea) {
  border-radius: 8px;
  border: 2px solid #E4E7ED;
  padding: 12px 16px;
  font-size: 14px;
}

.username-input :deep(.n-input__textarea:focus) {
  border-color: #409EFF;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

.login-footer {
  margin-top: 20px;
  text-align: center;
}

.demo-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.info-icon {
  color: #e6a23c;
}
</style>