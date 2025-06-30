<template>
  <a-layout-header style="background: #fff; padding: 0; display: flex; justify-content: space-between; align-items: center;">
    <div class="header-content">
      <div class="header-left">
        <a-breadcrumb>
          <template v-if="breadcrumbItems.length">
            <a-breadcrumb-item v-for="item in breadcrumbItems" :key="item.path || item.title">
              <router-link v-if="item.clickable" :to="item.path">{{ item.title }}</router-link>
              <span v-else>{{ item.title }}</span>
            </a-breadcrumb-item>
          </template>
          <a-breadcrumb-item v-else>
            <router-link to="/dashboard">首页</router-link>
          </a-breadcrumb-item>
        </a-breadcrumb>
      </div>
      <div class="header-right">
        <a-dropdown>
          <a class="ant-dropdown-link" @click.prevent>
            <UserOutlined /> {{ userName }}
          </a>
          <template #overlay>
            <a-menu>
              <a-menu-item key="profile" @click="handleProfile">个人信息</a-menu-item>
              <a-menu-item key="logout" @click="handleLogout">退出登录</a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </div>
  </a-layout-header>

  <!-- 个人信息弹窗 -->
  <a-modal
    v-model:open="profileModalVisible"
    title="个人信息"
    width="500px"
    :footer="null"
    :maskClosable="true"
  >
    <a-spin :spinning="loading">
      <div class="user-profile-info">
        <div class="info-item">
          <span class="info-label">用户名</span>
          <span class="info-value">{{ userInfo.username }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">姓名</span>
          <span class="info-value">{{ userInfo.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">邮箱</span>
          <span class="info-value">{{ userInfo.email }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">状态</span>
          <span class="info-value">
              {{ userInfo.status === 1 ? '正常' : '禁用' }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">最后登录</span>
          <span class="info-value">{{ userInfo.login_time || '暂无记录' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">创建时间</span>
          <span class="info-value">{{ userInfo.create_time }}</span>
        </div>
      </div>

      <a-divider /> <!-- 分割线 -->

      <div class="user-profile-roles" v-if="userInfo.roles && userInfo.roles.length > 0">
        <div class="info-item">
          <span class="info-label">角色</span>
          <span class="info-value">
            <a-space>
              <span v-for="role in userInfo.roles" :key="role.role_id">
                {{ role.name }}
              </span>
            </a-space>
          </span>
        </div>
      </div>
      <div class="user-profile-roles" v-else>
        <div class="info-item">
          <span class="info-label">角色</span>
          <span class="info-value">暂无角色信息</span>
        </div>
      </div>
    </a-spin>
  </a-modal>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { UserOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import axios from 'axios';

const route = useRoute();
const router = useRouter();

// 弹窗相关状态
const profileModalVisible = ref(false);
const loading = ref(false);
const userInfo = ref({
  user_id: '',
  username: '',
  name: '',
  email: '',
  status: 1,
  roles: [],
  login_time: '',
  create_time: '',
  update_time: ''
});

const breadcrumbItems = computed(() => {
  const items = [];
  const matched = route.matched;
  
  // 如果当前路由是首页，不显示面包屑项
  if (route.path === '/dashboard' || route.path === '/') {
    return items;
  }

  // 首页可以被点击
  items.push({
    title: '首页',
    path: '/dashboard',
    clickable: true
  });

  // 定义一级菜单
  const parentMenus = ['/projects', '/build', '/logs', '/user', '/environments', '/system'];

  matched.forEach((item) => {
    if (item.path !== '/' && item.meta && item.meta.title) {
      // 判断是否为一级菜单
      const isParentMenu = parentMenus.includes(item.path);
      
      items.push({
        title: item.meta.title,
        path: item.path,
        clickable: !isParentMenu // 只有一级菜单不可点击
      });
    }
  });

  return items;
});

// 获取用户名
const userName = computed(() => {
  const userInfo = localStorage.getItem('user_info');
  if (userInfo) {
    return JSON.parse(userInfo).name;
  }
  return '';
});

// 获取用户信息
const fetchUserProfile = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/user/profile/', {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      userInfo.value = response.data.data;
    } else {
      message.error(response.data.message || '获取用户信息失败');
    }
  } catch (error) {
    console.error('获取用户信息失败:', error);
    message.error('获取用户信息失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 显示个人信息弹窗
const handleProfile = () => {
  profileModalVisible.value = true;
  fetchUserProfile();
};

// 退出登录
const handleLogout = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/logout/', {}, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('退出成功');
      localStorage.removeItem('token');
      localStorage.removeItem('user_info');
      router.push('/login');
    } else {
      message.error(response.data.message || '退出失败');
    }
  } catch (error) {
    message.error('退出失败，请稍后重试');
    console.error('Logout error:', error);
  }
};
</script>

<style scoped>
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  height: 100%;
}

.header-left {
  margin-left: 24px;
}

.header-right {
  margin-right: 24px;
}

:deep(.ant-layout-header) {
  padding: 0;
  height: 64px;
  line-height: 64px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

:deep(.ant-dropdown-link) {
  color: rgba(0, 0, 0, 0.85);
  padding: 0 12px;
  cursor: pointer;
}

:deep(.ant-breadcrumb a) {
  color: rgba(0, 0, 0, 0.45);
  transition: color 0.3s;
}

:deep(.ant-breadcrumb a:hover) {
  color: rgba(0, 0, 0, 0.85);
}

:deep(.ant-breadcrumb span) {
  color: rgba(0, 0, 0, 0.45);
}

/* 弹窗相关样式 */
:deep(.ant-divider) {
  margin: 16px 0;
}

:deep(.ant-modal-body) {
  padding: 24px;
  max-height: 70vh;
  overflow-y: auto;
}

.user-profile-info,
.user-profile-roles {
  padding: 0 8px;
}

.info-item {
  display: flex;
  margin-bottom: 12px;
  align-items: center;
}

.info-label {
  width: 80px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

.info-value {
  flex: 1;
  color: rgba(0, 0, 0, 0.85);
  font-weight: 500;
  font-size: 14px;
}
</style>