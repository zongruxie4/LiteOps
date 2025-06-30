<template>
  <a-config-provider :locale="zhCN" :theme="theme">
    <router-view></router-view>
  </a-config-provider>
</template>

<script setup>
import zhCN from "ant-design-vue/es/locale/zh_CN";

// 配置 Ant Design Vue 主题，强制使用自定义 PingFang 字体
const theme = {
  token: {
    fontFamily: "'PingFangCustom', Arial, sans-serif",
  },
};
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