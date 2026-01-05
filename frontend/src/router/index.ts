import { createRouter, createWebHistory } from 'vue-router'
import ChatInterface from '../components/ChatInterface.vue'

const routes = [
  {
    path: '/',
    redirect: '/login'
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router