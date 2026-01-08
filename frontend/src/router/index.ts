import { createRouter, createWebHistory } from 'vue-router'
import ChatInterface from '../components/ChatInterface.vue'

const routes = [
  {
    path: '/',
    redirect: '/chat'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../components/LoginPage.vue')
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatInterface
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('../components/KnowledgeBaseManager.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router