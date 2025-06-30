import { createApp } from 'vue'
// import './style.css'
import App from './App.vue'
import Antd from 'ant-design-vue';
import './assets/css/reset.css';
import './assets/css/global.css';
import axios from 'axios'
import router from './router'
// import permissionDirective from './directives/permission';

// 配置 axios
// 使用环境变量中的API URL
axios.defaults.baseURL = import.meta.env.VITE_API_URL;

const app = createApp(App);

// 使用 Ant Design Vue 和 Vue Router
// app.use(router).use(Antd).use(permissionDirective);
app.use(router).use(Antd)

// 将 axios 添加到 Vue 实例的全局属性中
app.config.globalProperties.$axios = axios;

app.mount('#app')