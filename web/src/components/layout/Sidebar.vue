<template>
  <a-layout-sider v-model:collapsed="collapsed" theme="light" collapsible>
    <div class="logo">
      <img v-if="collapsed" src="../../assets/image/liteops.png" alt="Logo" />
      <img v-else src="../../assets/image/liteops-sidebar.png" alt="Logo" />
    </div>
    <div class="menu-container">
      <a-menu
        v-model:selectedKeys="selectedKeys"
        v-model:openKeys="openKeys"
        mode="inline"
        @click="handleMenuClick"
        v-if="permissionStore.initialized"
      >
        <!-- 首页 -->
        <a-menu-item key="/dashboard" v-if="hasMenuPermission('/dashboard')">
          <template #icon>
            <DashboardOutlined />
          </template>
          <span>首页</span>
        </a-menu-item>

        <!-- 项目管理 -->
        <a-sub-menu key="/projects" v-if="hasAnySubMenuPermission('/projects')">
          <template #icon>
            <ProjectOutlined />
          </template>
          <template #title>项目管理</template>
          <a-menu-item key="/projects/list" v-if="hasMenuPermission('/projects/list')">项目列表</a-menu-item>
        </a-sub-menu>

        <!-- 构建与部署 -->
        <a-sub-menu key="/build" v-if="hasAnySubMenuPermission('/build')">
          <template #icon>
            <BuildOutlined />
          </template>
          <template #title>构建与部署</template>
          <a-menu-item key="/build/tasks" v-if="hasMenuPermission('/build/tasks')">构建任务</a-menu-item>
          <a-menu-item key="/build/history" v-if="hasMenuPermission('/build/history')">构建历史</a-menu-item>
        </a-sub-menu>

        <!-- 日志与监控 -->
        <a-sub-menu key="/logs" v-if="hasAnySubMenuPermission('/logs')">
          <template #icon>
            <FileSearchOutlined />
          </template>
          <template #title>日志与监控</template>
          <a-menu-item key="/logs/login" v-if="hasMenuPermission('/logs/login')">登陆日志</a-menu-item>
        </a-sub-menu>

        <!-- 用户与权限管理 -->
        <a-sub-menu key="/user" v-if="hasAnySubMenuPermission('/user')">
          <template #icon>
            <UserOutlined />
          </template>
          <template #title>用户与权限</template>
          <a-menu-item key="/user/list" v-if="hasMenuPermission('/user/list')">用户管理</a-menu-item>
          <a-menu-item key="/user/role" v-if="hasMenuPermission('/user/role')">角色管理</a-menu-item>
        </a-sub-menu>

        <!-- 凭证管理 -->
        <a-menu-item key="/credentials" v-if="hasMenuPermission('/credentials')">
          <template #icon>
            <KeyOutlined />
          </template>
          <span>凭证管理</span>
        </a-menu-item>

        <!-- 环境配置 -->
        <a-sub-menu key="/environments" v-if="hasAnySubMenuPermission('/environments')">
          <template #icon>
            <CloudServerOutlined />
          </template>
          <template #title>环境配置</template>
          <a-menu-item key="/environments/list" v-if="hasMenuPermission('/environments/list')">环境列表</a-menu-item>
        </a-sub-menu>



        <!-- 系统配置 -->
        <a-sub-menu key="/system" v-if="hasAnySubMenuPermission('/system')">
          <template #icon>
            <SettingOutlined />
          </template>
          <template #title>系统配置</template>
          <a-menu-item key="/system/basic" v-if="hasMenuPermission('/system/basic')">基本设置</a-menu-item>
        </a-sub-menu>
      </a-menu>
      <div v-else class="menu-loading">
        <a-spin tip="加载菜单权限中..." />
      </div>
    </div>
  </a-layout-sider>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { hasMenuPermission, hasAnySubMenuPermission, permissionStore } from '../../utils/permission';
import {
  DashboardOutlined,
  ProjectOutlined,
  BuildOutlined,
  FileSearchOutlined,
  UserOutlined,
  SettingOutlined,
  KeyOutlined,
  CloudServerOutlined
} from '@ant-design/icons-vue';

const router = useRouter();
const route = useRoute();
const collapsed = ref(false);
const selectedKeys = ref(['/dashboard']);
const openKeys = ref([]);

// 获取当前路由的父级路径
const getParentPath = (path) => {
  const pathParts = path.split('/');
  return pathParts.length > 2 ? `/${pathParts[1]}` : path;
};

// 初始化菜单状态
onMounted(() => {
  const currentPath = route.path;
  selectedKeys.value = [currentPath];

  if (currentPath !== '/dashboard') {
    const parentPath = getParentPath(currentPath);
    openKeys.value = [parentPath];
  }
});

// 监听路由变化
watch(() => route.path, (newPath) => {
  selectedKeys.value = [newPath];
  const parentPath = getParentPath(newPath);

  if (!openKeys.value.includes(parentPath) && newPath !== '/dashboard') {
    openKeys.value = [parentPath];
  }
});

// 处理菜单点击
const handleMenuClick = ({ key }) => {
  router.push(key);
};
</script>

<style scoped>
.logo {
  height: 65px;
  display: flex;
  justify-content: center;
  align-items: center;
  /* padding: 8px; */
  /* overflow: hidden; */
}

.logo img {
  height: 65px;
  /* height: auto; */
  /* max-height: 50px; */
  max-width: 100%;
  object-fit: contain;
}

.menu-container {
  height: calc(100vh - 64px);
  overflow-y: auto;
  overflow-x: hidden;
}

:deep(.ant-layout-sider) {
  box-shadow: 2px 0 8px 0 rgba(29, 35, 41, 0.05);
  position: relative;
  z-index: 10;
}

:deep(.ant-layout-sider-collapsed .logo) {
  padding: 8px 0;
}

:deep(.ant-layout-sider-collapsed .logo img) {
  max-width: 32px;
}

:deep(.ant-layout-sider-collapsed .ant-menu-item .anticon),
:deep(.ant-layout-sider-collapsed .ant-menu-submenu-title .anticon) {
  margin-right: 0;
  font-size: 16px;
}

:deep(.ant-menu-item) {
  height: 40px !important;
  line-height: 40px !important;
  margin: 4px 0 !important;
  padding-left: 24px !important;
}

:deep(.ant-menu-submenu-title) {
  height: 40px !important;
  line-height: 40px !important;
  margin: 4px 0 !important;
  padding-left: 24px !important;
}

/* 子菜单项的缩进一致 */
:deep(.ant-menu-sub .ant-menu-item) {
  padding-left: 48px !important;
}

/* 图标对齐 */
:deep(.ant-menu-item .anticon),
:deep(.ant-menu-submenu-title .anticon) {
  min-width: 14px;
  margin-right: 10px;
  font-size: 16px;
}

/* 滚动条样式 */
.menu-container::-webkit-scrollbar {
  width: 3px;
}

.menu-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.menu-container::-webkit-scrollbar-track {
  background: transparent;
}

.menu-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style>