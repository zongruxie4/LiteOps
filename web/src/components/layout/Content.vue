<template>
  <a-layout-content>
    <div class="content-container">
      <router-view></router-view>
    </div>
  </a-layout-content>
</template>

<script setup>
</script>

<style scoped>
.content-container {
  padding: 24px;
  background: #fff;
  min-height: 360px;
  border-radius: 4px;
  overflow-y: auto;
  /* 设置最大高度，内容超出时可以滚动 */
  max-height: calc(100vh - 112px);
}

:deep(.ant-layout-content) {
  margin: 24px;
  background: transparent;
  position: relative;
  flex: 1;
  overflow: hidden;
}
</style>