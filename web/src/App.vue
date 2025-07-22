<template>
  <a-watermark
    v-if="shouldShowWatermark"
    :content="watermarkContent"
  >
    <a-config-provider :locale="zhCN" :theme="theme">
      <router-view></router-view>
    </a-config-provider>
  </a-watermark>
  <a-config-provider
    v-else
    :locale="zhCN"
    :theme="theme"
  >
    <router-view></router-view>
  </a-config-provider>
</template>

<script setup>
import { reactive, computed, onMounted, watch, ref } from 'vue';
import { useRoute } from 'vue-router';
import zhCN from "ant-design-vue/es/locale/zh_CN";
import axios from 'axios';

const route = useRoute();

const theme = {
  token: {
    fontFamily: "'PingFangCustom', Arial, sans-serif",
  },
};

// 水印配置
const watermarkConfig = reactive({
  enabled: false,
  content: '',
  showTime: false,
  showUsername: false
});

// 用户信息
const userInfo = reactive({
  username: '',
  name: ''
});

// 当前日期（年月日）
const currentDate = ref('');

const shouldShowWatermark = computed(() => {
  // 排除登陆页面显示水印
  if (route.path === '/login') {
    return false;
  }
  return watermarkConfig.enabled;
});

const watermarkContent = computed(() => {
  const contents = [];

  // 添加自定义水印内容
  if (watermarkConfig.content) {
    const customContents = watermarkConfig.content.split('\n').filter(line => line.trim());
    contents.push(...customContents);
  }

  // 添加日期水印
  if (watermarkConfig.showTime && currentDate.value) {
    contents.push(currentDate.value);
  }

  // 添加用户名水印
  if (watermarkConfig.showUsername && userInfo.name) {
    contents.push(userInfo.name);
  }

  return contents.length > 0 ? contents : [];
});

// 更新日期（年月日）
const updateDate = () => {
  const now = new Date();
  currentDate.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  });
};

// 获取水印配置
const fetchWatermarkConfig = async () => {
  try {
    const response = await axios.get('/api/system/watermark/');
    if (response.data.code === 200) {
      watermarkConfig.enabled = response.data.data.watermark_enabled;
      watermarkConfig.content = response.data.data.watermark_content;
      watermarkConfig.showTime = response.data.data.watermark_show_time;
      watermarkConfig.showUsername = response.data.data.watermark_show_username;
    }
  } catch (error) {
    console.error('获取水印配置失败:', error);
    // 使用默认配置
  }
};

// 获取用户信息
const fetchUserInfo = async () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return;

    const response = await axios.get('/api/user/current/', {
      headers: { 'Authorization': token }
    });
    if (response.data.code === 200) {
      userInfo.username = response.data.data.username;
      userInfo.name = response.data.data.name;
    }
  } catch (error) {
    console.error('获取用户信息失败:', error);
  }
};

// 监听路由变化，在非登录页面获取用户信息
watch(() => route.path, (newPath) => {
  if (newPath !== '/login') {
    fetchUserInfo();
  }
}, { immediate: true });

onMounted(() => {
  fetchWatermarkConfig();

  updateDate();
});
</script>

<style>
#app {
  width: 100%;
  height: 100vh;
  overflow: hidden;
  font-family: 'PingFangCustom', Arial, sans-serif !important;
}

body {
  margin: 0;
  padding: 0;
  background-color: #f0f2f5;
  font-family: 'PingFangCustom', Arial, sans-serif !important;
}

.ant-config-provider {
  font-family: 'PingFangCustom', Arial, sans-serif !important;
}
</style>