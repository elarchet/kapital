import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router'
import './style.css'
import App from './App.vue'
import * as Vue from 'vue'

if (typeof window !== 'undefined') {
  (window as any).Vue = Vue;
  (window as any).router = router;
}

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')

