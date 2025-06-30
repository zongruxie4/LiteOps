<template>
  <div class="build-task-detail">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>构建任务详情</h2>
        </a-col>
        <a-col>
          <a-space>
            <a-button @click="handleBack">
              <template #icon><ArrowLeftOutlined /></template>
              返回
            </a-button>
            <a-button type="primary" @click="handleEdit">
              <template #icon><EditOutlined /></template>
              编辑
            </a-button>
          </a-space>
        </a-col>
      </a-row>
    </div>

    <a-card v-loading="loading">
      <a-descriptions
        title="基本信息"
        bordered
        :column="2"
      >
        <a-descriptions-item label="任务ID">
          {{ taskDetail.task_id }}
        </a-descriptions-item>
        <a-descriptions-item label="任务名称">
          {{ taskDetail.name }}
        </a-descriptions-item>
        <a-descriptions-item label="任务状态">
          {{ getStatusText(taskDetail.status) }}
        </a-descriptions-item>
        <a-descriptions-item label="所属项目">
          {{ taskDetail.project?.name }}
        </a-descriptions-item>
        <a-descriptions-item label="构建环境">
          {{ taskDetail.environment?.name }}
        </a-descriptions-item>
        <a-descriptions-item label="环境类型">
          {{ taskDetail.environment?.type }}
        </a-descriptions-item>
        <a-descriptions-item label="Git仓库">
          {{ taskDetail.project?.repository }}
        </a-descriptions-item>
        <a-descriptions-item label="默认分支">
          <template v-if="taskDetail.branch">
            {{ taskDetail.branch }}
            <!-- <a-tag color="blue" style="margin-left: 8px">推荐分支</a-tag> -->
          </template>
          <template v-else>
            <span style="color: rgba(0,0,0,.45)">未设置（将使用仓库默认分支）</span>
          </template>
        </a-descriptions-item>
        <a-descriptions-item label="Git凭证">
          {{ taskDetail.git_token?.name }}
        </a-descriptions-item>
        <a-descriptions-item label="最新构建号">
          {{ taskDetail.version || '暂无' }}
        </a-descriptions-item>
        <a-descriptions-item label="构建版本">
          {{ taskDetail.version || '暂无' }}
        </a-descriptions-item>
        <a-descriptions-item label="构建需求">
          {{ taskDetail.requirement || '暂无' }}
        </a-descriptions-item>
        <a-descriptions-item label="创建者">
          {{ taskDetail.creator?.name }}
        </a-descriptions-item>
        <a-descriptions-item label="创建时间">
          {{ taskDetail.create_time }}
        </a-descriptions-item>
        <a-descriptions-item label="最近更新">
          {{ taskDetail.update_time }}
        </a-descriptions-item>
        <a-descriptions-item label="任务描述" :span="2">
          {{ taskDetail.description || '暂无描述' }}
        </a-descriptions-item>
      </a-descriptions>

      <a-divider />

      <div class="notification-settings">
        <h3>通知设置</h3>
        <div v-if="robotList.length === 0 && !loading" class="empty-notification">
          <a-empty description="暂无通知设置" />
        </div>
        <div v-else-if="taskDetail.notification_channels && taskDetail.notification_channels.length > 0" class="notification-list">
          <a-tag 
            v-for="robotId in taskDetail.notification_channels" 
            :key="robotId"
            :color="getRobotTagColor(getRobotTypeById(robotId))"
            class="robot-tag"
          >
            <template #icon>
              <DingdingOutlined v-if="getRobotTypeById(robotId) === 'dingtalk'" />
              <WechatOutlined v-else-if="getRobotTypeById(robotId) === 'wecom'" />
              <RocketOutlined v-else-if="getRobotTypeById(robotId) === 'feishu'" />
              <MailOutlined v-else />
            </template>
            {{ getRobotNameById(robotId) }}
          </a-tag>
        </div>
        <div v-else-if="!loading" class="empty-notification">
          <a-empty description="未配置通知机器人" />
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message, Empty } from 'ant-design-vue';
import axios from 'axios';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DingdingOutlined,
  WechatOutlined,
  MailOutlined,
  RocketOutlined,
} from '@ant-design/icons-vue';

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const robotsLoading = ref(false);
const taskDetail = ref({
  notification_channels: []
});
const robotList = ref([]);

// 获取任务详情
const loadTaskDetail = async () => {
  try {
    loading.value = true;
    const taskId = route.query.task_id;
    const token = localStorage.getItem('token');
    const response = await axios.get(`/api/build/tasks/${taskId}`, {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      taskDetail.value = response.data.data;
      if (!taskDetail.value.notification_channels) {
        taskDetail.value.notification_channels = [];
      }
      // 加载机器人列表
      await loadRobotList();
    } else {
      message.error(response.data.message || '获取任务详情失败');
    }
  } catch (error) {
    console.error('Load task detail error:', error);
    message.error('获取任务详情失败');
  } finally {
    loading.value = false;
  }
};

// 加载通知机器人列表
const loadRobotList = async () => {
  try {
    robotsLoading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/notification/robots/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      robotList.value = response.data.data || [];
    } else {
      message.error(response.data.message || '获取通知机器人列表失败');
    }
  } catch (error) {
    console.error('Load robot list error:', error);
    message.error('获取通知机器人列表失败');
  } finally {
    robotsLoading.value = false;
  }
};

// 根据机器人ID获取机器人类型
const getRobotTypeById = (robotId) => {
  const robot = robotList.value.find(r => r.robot_id === robotId);
  return robot ? robot.type : '';
};

// 根据机器人ID获取机器人名称
const getRobotNameById = (robotId) => {
  const robot = robotList.value.find(r => r.robot_id === robotId);
  return robot ? robot.name : robotId;
};

// 获取机器人标签颜色
const getRobotTagColor = (type) => {
  const colors = {
    'dingtalk': '#1890ff',
    'wecom': '#07c160',
    'feishu': '#722ed1',
  };
  return colors[type] || '#2db7f5';
};

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    created: '正常',
    disabled: '已禁用',
    running: '运行中',
    success: '成功',
    failed: '失败',
  };
  return texts[status] || status;
};

// 返回列表页
const handleBack = () => {
  router.push('/build/tasks');
};

// 跳转到编辑页
const handleEdit = () => {
  router.push({
    name: 'build-task-edit',
    query: { task_id: route.query.task_id }
  });
};

onMounted(() => {
  loadTaskDetail();
});
</script>

<style scoped>

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  margin: 0;
  color: rgba(0, 0, 0, 0.85);
  font-weight: 500;
}

:deep(.ant-card) {
  border-radius: 4px;
}

:deep(.ant-descriptions) {
  margin-bottom: 24px;
}

:deep(.ant-descriptions-title) {
  font-size: 16px;
  font-weight: 500;
}

.notification-settings {
  margin-top: 24px;
}

.notification-settings h3 {
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
}

:deep(.ant-checkbox-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.notification-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
}

.robot-tag {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  font-size: 14px;
}

.empty-notification {
  padding: 24px 0;
  text-align: center;
}
</style> 