<template>
  <div class="session-sidebar" :class="{ 'collapsed': collapsed }">
    <!-- 侧边栏头部 -->
    <div class="sidebar-header">
      <div class="header-title">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="mr-2">
          <path d="M21 11.5C21.0034 12.8199 20.6951 14.1219 20.1 15.3C19.3944 16.7118 18.3098 17.8992 16.9674 18.7293C15.6251 19.5594 14.0782 19.9994 12.5 20C11.1801 20.0035 9.87812 19.6951 8.7 19.1L3 21L4.9 15.3C4.30493 14.1219 3.99656 12.8199 4 11.5C4.00061 9.92179 4.44061 8.37488 5.27072 7.03258C6.10083 5.69028 7.28825 4.6056 8.7 3.90003C9.87812 3.30496 11.1801 2.99659 12.5 3.00003H13C15.0843 3.11502 17.053 3.99479 18.5291 5.47089C20.0052 6.94699 20.885 8.91568 21 11V11.5Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span v-if="!collapsed">会话历史</span>
      </div>
      <n-button 
        quaternary 
        circle 
        size="small" 
        @click="toggleCollapse"
        class="collapse-button"
      >
        <template #icon>
          <svg v-if="collapsed" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polyline points="15 18 9 12 15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <polyline points="9 18 15 12 9 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </template>
      </n-button>
    </div>

    <!-- 新建会话按钮 -->
    <div class="new-session-container">
      <n-button 
        type="primary" 
        block 
        @click="createNewSession"
        class="new-session-button"
      >
        <template #icon>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="12" y1="5" x2="12" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="5" y1="12" x2="19" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </template>
        <span v-if="!collapsed">新建会话</span>
      </n-button>
    </div>

    <!-- 会话列表 -->
    <div class="sessions-list">
      <div v-if="sessions && sessions.length > 0" class="sessions-container">
        <div 
          v-for="session in sessions" 
          :key="session.session_id" 
          class="session-item" 
          :class="{ 'active': selectedSessionId === session.session_id }"
          @click="selectSession(session)"
        >
          <div class="session-info">
            <div class="session-time">
              {{ formatSessionTime(session.start_time) }}
            </div>
            <div v-if="!collapsed" class="session-preview">
              {{ getSessionPreview(session) }}
            </div>
          </div>
          <div class="session-actions">
            <n-dropdown 
              trigger="click" 
              :options="sessionDropdownOptions"
              @select="(key: string) => handleSessionAction(key, session)"
            >
              <n-button 
                quaternary 
                circle 
                size="small"
                class="action-button"
              >
                <template #icon>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="1" fill="currentColor"/>
                    <circle cx="12" cy="5" r="1" fill="currentColor"/>
                    <circle cx="12" cy="19" r="1" fill="currentColor"/>
                  </svg>
                </template>
              </n-button>
            </n-dropdown>
          </div>
        </div>
      </div>
      <div v-else class="empty-sessions" v-if="!collapsed">
        <div class="empty-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M21 15C21 15.5304 20.7893 16.0391 20.4142 16.4142C20.0391 16.7893 19.5304 17 19 17H7L3 21V5C3 4.46957 3.21071 3.96086 3.58579 3.58579C3.96086 3.21071 4.46957 3 5 3H19C19.5304 3 20.0391 3.21071 20.4142 3.58579C20.7893 3.96086 21 4.46957 21 5V15Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <p>暂无会话记录</p>
        <n-button type="primary" size="small" @click="createNewSession">
          创建第一个会话
        </n-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useDialog, useMessage } from 'naive-ui'
import { useSessionsStore, type Session } from '@/stores/sessions'

const emit = defineEmits<{
  newSession: []
  sessionClick: [session: Session]
  updateCollapsed: [collapsed: boolean]
}>()

const dialog = useDialog()
const message = useMessage()
const sessionsStore = useSessionsStore()

// 状态
const collapsed = ref(false)
const selectedSessionId = ref<string | null>(null)

// 计算属性
const sessions = computed(() => sessionsStore.sessions)

// 下拉菜单选项
const sessionDropdownOptions = [
  {
    label: '重命名',
    key: 'rename'
  },
  {
    label: '删除',
    key: 'delete'
  }
]

// 切换侧边栏收起状态
const toggleCollapse = () => {
  collapsed.value = !collapsed.value
  emit('updateCollapsed', collapsed.value)
}

// 创建新会话
const createNewSession = () => {
  sessionsStore.createSession()
  selectedSessionId.value = sessionsStore.currentSessionId
  emit('newSession')
}

// 选择会话
const selectSession = (session: Session) => {
  selectedSessionId.value = session.session_id
  emit('sessionClick', session)
}

// 处理会话操作
const handleSessionAction = (key: string, session: Session) => {
  switch (key) {
    case 'rename':
      renameSession(session)
      break
    case 'delete':
      deleteSession(session)
      break
  }
}

// 重命名会话
const renameSession = (session: Session) => {
  dialog.create({
    title: '重命名会话',
    content: '请输入新的会话名称：',
    positiveText: '确认',
    negativeText: '取消',
    showIcon: false,
    maskClosable: false,
    type: 'info',
    transformOrigin: 'center',
    zIndex: 1000,
    positiveButtonProps: {
      type: 'primary'
    },
    negativeButtonProps: {
      type: 'default'
    },
    onPositiveClick: () => {
      const input = document.querySelector('.n-dialog__content input') as HTMLInputElement
      if (input) {
        const newName = input.value.trim()
        if (newName) {
          sessionsStore.renameSession(session.session_id, newName)
          message.success('会话重命名成功')
        } else {
          message.warning('会话名称不能为空')
        }
      }
    }
  })
}

// 删除会话
const deleteSession = (session: Session) => {
  dialog.warning({
    title: '删除会话',
    content: `确定要删除会话"${getSessionPreview(session)}"吗？此操作不可恢复。`,
    positiveText: '确认删除',
    negativeText: '取消',
    showIcon: false,
    maskClosable: false,

    type: 'warning',
    transformOrigin: 'center',
    zIndex: 1000,
    positiveButtonProps: {
      type: 'error'
    },
    negativeButtonProps: {
      type: 'default'
    },
    onPositiveClick: () => {
      sessionsStore.deleteSession(session.session_id)
      message.success('会话已删除')
      
      // 如果删除的是当前选中的会话，清除选中状态
      if (selectedSessionId.value === session.session_id) {
        selectedSessionId.value = sessions.value.length > 0 ? sessions.value[0].session_id : null
      }
    }
  })
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

// 获取会话预览
const getSessionPreview = (session: Session) => {
  // 这里应该从会话中获取第一条消息或使用会话名称
  // 临时使用会话ID的一部分作为预览
  return `会话 ${session.session_id.substring(0, 8)}`
}

// 组件挂载时加载会话
onMounted(() => {
  sessionsStore.loadSessions()
})
</script>

<style scoped>
.session-sidebar {
  width: 280px;
  height: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.session-sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header-title {
  display: flex;
  align-items: center;
  font-weight: 600;
  color: #303133;
}

.collapse-button {
  color: #606266;
}

.new-session-container {
  padding: 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.new-session-button {
  width: 100%;
}

.sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px 16px 8px;
}

.sessions-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.session-item:hover {
  background: rgba(64, 158, 255, 0.1);
}

.session-item.active {
  background: rgba(64, 158, 255, 0.2);
}

.session-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: #409EFF;
  border-radius: 0 2px 2px 0;
}

.session-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.session-time {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.session-preview {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-actions {
  opacity: 0;
  transition: opacity 0.2s ease;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.action-button {
  width: 24px;
  height: 24px;
  color: #909399;
}

.empty-sessions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  text-align: center;
  color: #909399;
}

.empty-icon {
  color: #C0C4CC;
  margin-bottom: 16px;
}

.empty-sessions p {
  margin-bottom: 16px;
}
</style>