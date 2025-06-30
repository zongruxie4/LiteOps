<template>
  <a-card title="构建后操作" class="card-wrapper">
    <a-row :gutter="16">
      <a-col :span="24">
        <a-form-item label="通知方式" name="notification_channels">
          <a-select
            :value="modelValue"
            mode="multiple"
            placeholder="请选择通知方式"
            style="width: 100%"
            :options="robotList"
            :field-names="{
              label: 'label',
              value: 'robot_id',
            }"
            @change="handleChannelsChange"
          />
          <div class="form-item-help">
            选择构建完成后的通知方式，无论构建成功或失败都会发送通知
          </div>
        </a-form-item>
      </a-col>
    </a-row>
  </a-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { message } from 'ant-design-vue';
import axios from 'axios';

const props = defineProps({
  modelValue: {
    type: Array,
    required: true,
    default: () => [],
  },
});

const emit = defineEmits(['update:modelValue']);

// 机器人列表
const robotList = ref([]);

// 获取机器人类型文本
const getRobotTypeText = (type) => {
  const types = {
    dingtalk: '钉钉',
    wecom: '企业微信',
    feishu: '飞书',
  };
  return types[type] || type;
};

// 处理通知方式变更
const handleChannelsChange = (value) => {
  emit('update:modelValue', value);
};

// 加载机器人列表
const loadRobotList = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/build/tasks/', {
      params: { get_robots: true },
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      robotList.value = response.data.data.map(robot => ({
        label: `${getRobotTypeText(robot.type)} - ${robot.name}`,
        robot_id: robot.robot_id,
        type: robot.type,
        name: robot.name,
      }));
    } else {
      message.error(response.data.message || '获取通知机器人列表失败');
    }
  } catch (error) {
    console.error('Load robot list error:', error);
    message.error('获取通知机器人列表失败');
  }
};

// 页面加载时获取机器人列表
onMounted(() => {
  loadRobotList();
});
</script>

<style scoped>
.card-wrapper {
  margin-bottom: 24px;
}

.form-item-help {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 8px;
}
</style> 