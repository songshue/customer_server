import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import router from './router'
import { 
  create, 
  NButton, 
  NCard, 
  NInput, 
  NAlert, 
  NDropdown, 
  NIcon, 
  NAvatar,
  NTooltip,
  NTag,
  NMessageProvider,
  NDialogProvider
} from 'naive-ui'
import 'virtual:uno.css'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia()

pinia.use(piniaPluginPersistedstate)

// Naive UI 配置
const naive = create({
  components: [
    NButton, 
    NCard, 
    NInput, 
    NAlert, 
    NDropdown, 
    NIcon, 
    NAvatar,
    NTooltip,
    NTag,
    NMessageProvider,
    NDialogProvider
  ]
})

app.use(pinia)
app.use(router)
app.use(naive)

app.mount('#app')