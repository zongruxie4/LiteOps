<template>
  <a-layout style="min-height: 100vh">
    <Sidebar />
    <a-layout>
      <Header />
      <Content />
      <Footer />
    </a-layout>
  </a-layout>
</template>

<script setup>
import Sidebar from './Sidebar.vue';
import Header from './Header.vue';
import Content from './Content.vue';
import Footer from './Footer.vue';
</script>

<style scoped>
:deep(.ant-layout) {
  min-height: 100vh;
  height: 100%;
  background: #fff;
}
.site-layout .site-layout-background {
    background: #fff;
}
</style> 