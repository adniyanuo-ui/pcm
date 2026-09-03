import { createApp } from 'vue'
import { ElIcon } from 'element-plus'
import 'element-plus/theme-chalk/base.css'
import 'element-plus/theme-chalk/el-icon.css'
import 'element-plus/theme-chalk/el-dialog.css'
import 'element-plus/theme-chalk/el-overlay.css'
import 'element-plus/theme-chalk/el-message.css'
import 'element-plus/theme-chalk/el-message-box.css'
import 'element-plus/theme-chalk/el-button.css'
import './styles/main.css'
import App from './App.vue'

createApp(App).component('ElIcon', ElIcon).mount('#app')
