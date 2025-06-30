<template>
  <div class="log-detail">
    <div class="page-header">
      <a-page-header
        title="登录日志详情"
        @back="handleBack"
      />
    </div>

    <!-- 日志详情信息 -->
    <a-card title="日志信息" :loading="loading">
      <div class="info-list" v-if="logDetail">
        <div class="info-item">
          <span class="info-label">日志ID：</span>
          <span class="info-value">{{ logDetail.log_id }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">用户名：</span>
          <span class="info-value">{{ logDetail.username || '未知用户' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">用户姓名：</span>
          <span class="info-value">{{ logDetail.user_name || '未知' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">登录状态：</span>
          <span class="info-value">
            {{ logDetail.status === 'success' ? '成功' : '失败' }}
          </span>
        </div>
        <div class="info-item" v-if="logDetail.fail_reason">
          <span class="info-label">失败原因：</span>
          <span class="info-value">{{ logDetail.fail_reason }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">登录IP：</span>
          <span class="info-value">{{ logDetail.ip_address }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">登录时间：</span>
          <span class="info-value">{{ logDetail.login_time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">用户代理：</span>
          <span class="info-value user-agent-info">{{ logDetail.user_agent }}</span>
        </div>
      </div>
      <a-empty v-else description="未找到日志信息" />
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import axios from 'axios';
import { checkPermission } from '../../utils/permission';

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const logDetail = ref(null);



const fetchLogDetail = async () => {
  const logId = route.query.log_id;
  if (!logId) {
    message.error('日志ID不能为空');
    router.push('/logs/login');
    return;
  }

  // 检查权限
  if (!checkPermission('logs_login', 'view')) {
    router.push('/dashboard');
    return;
  }

  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get(`/api/logs/login/${logId}/`, {
      headers: {
        'Authorization': token
      }
    });
    
    if (response.data.code === 200) {
      logDetail.value = response.data.data;
    } else {
      throw new Error(response.data.message || '获取日志详情失败');
    }
  } catch (error) {
    message.error(error.message || '获取日志详情失败');
    router.push('/logs/login');
  } finally {
    loading.value = false;
  }
};

const handleBack = () => {
  router.push('/logs/login');
};

onMounted(() => {
  fetchLogDetail();
});
</script>

<style scoped>

.page-header {
  margin-bottom: 24px;
  background: #fff;
}

:deep(.ant-page-header) {
  padding: 16px 24px;
}

.info-list {
  padding: 8px 0;
}

.info-item {
  line-height: 32px;
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
}

.info-label {
  color: rgba(0, 0, 0, 0.45);
  min-width: 100px;
}

.info-value {
  color: rgba(0, 0, 0, 0.85);
  flex: 1;
}

.user-agent-info {
  word-break: break-all;
}
</style> 