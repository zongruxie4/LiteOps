<template>
  <div class="environment-detail">
    <div class="page-header">
      <a-page-header
        :title="environment?.name || '环境详情'"
        @back="handleBack"
      >
        <template #extra>
          <a-space>
            <a-button @click="handleEditEnvironment">
              <template #icon><EditOutlined /></template>
              编辑环境
            </a-button>
          </a-space>
        </template>
      </a-page-header>
    </div>

    <!-- 环境基本信息 -->
    <a-card title="环境信息" :loading="loading">
      <div class="info-list">
        <div class="info-item">
          <span class="info-label">环境名称：</span>
          <span class="info-value">{{ environment?.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">环境ID：</span>
          <span class="info-value">{{ environment?.environment_id }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">环境类型：</span>
          <span class="info-value">{{ getEnvironmentTypeText(environment?.type) }}
          </span>
        </div>
        <div class="info-item">
          <span class="info-label">创建者：</span>
          <span class="info-value">{{ environment?.creator?.name || '未知' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">创建时间：</span>
          <span class="info-value">{{ environment?.create_time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">更新时间：</span>
          <span class="info-value">{{ environment?.update_time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">环境描述：</span>
          <span class="info-value">{{ environment?.description || '暂无描述' }}</span>
        </div>
      </div>
    </a-card>

    <!-- 编辑环境抽屉 -->
    <a-drawer
      v-model:open="drawerVisible"
      title="编辑环境"
      width="600px"
      @close="handleDrawerClose"
    >
      <a-form
        :model="formState"
        :rules="rules"
        ref="formRef"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="环境名称" name="name">
          <a-input v-model:value="formState.name" placeholder="请输入环境名称" />
        </a-form-item>

        <a-form-item label="环境类型" name="type">
          <a-select v-model:value="formState.type" placeholder="请选择环境类型">
            <a-select-option value="development">开发环境</a-select-option>
            <a-select-option value="testing">测试环境</a-select-option>
            <a-select-option value="staging">预发布环境</a-select-option>
            <a-select-option value="production">生产环境</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="环境描述" name="description">
          <a-textarea
            v-model:value="formState.description"
            placeholder="请输入环境描述"
            :rows="4"
          />
        </a-form-item>
      </a-form>

      <template #footer>
        <a-space>
          <a-button @click="handleDrawerClose">取消</a-button>
          <a-button
            type="primary"
            :loading="submitLoading"
            @click="handleSubmit"
          >
            保存
          </a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { EditOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { checkPermission, hasFunctionPermission } from '../../utils/permission';

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const environment = ref(null);
const drawerVisible = ref(false);
const formRef = ref();
const submitLoading = ref(false);

const formState = reactive({
  name: '',
  type: undefined,
  description: '',
});



const rules = {
  name: [
    { required: true, message: '请输入环境名称', trigger: 'blur' },
    { min: 2, max: 50, message: '环境名称长度应在 2-50 个字符之间', trigger: 'blur' },
  ],
  type: [
    { required: true, message: '请选择环境类型', trigger: 'change' },
  ],
};

const getEnvironmentTypeText = (type) => {
  const typeMap = {
    development: '开发环境',
    testing: '测试环境',
    staging: '预发布环境',
    production: '生产环境',
  };
  return typeMap[type] || type;
};

const getEnvironmentTypeColor = (type) => {
  const colorMap = {
    development: 'rgba(24,144,255,0.8)',
    testing: 'rgba(8,151,156,0.8)',
    staging: 'rgba(212,107,8,0.8)',
    production: 'rgba(56,158,13,0.8)',
  };
  return colorMap[type] || 'default';
};

const fetchEnvironmentDetail = async () => {
  const environmentId = route.query.environment_id;
  if (!environmentId) {
    message.error('环境ID不能为空');
    router.push('/environments/list');
    return;
  }

  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/environments/', {
      headers: {
        'Authorization': token
      },
      params: {
        environment_id: environmentId
      }
    });
    
    if (response.data.code === 200) {
      environment.value = response.data.data[0];
    } else {
      throw new Error(response.data.message || '获取环境详情失败');
    }
  } catch (error) {
    message.error(error.message);
    router.push('/environments/list');
  } finally {
    loading.value = false;
  }
};

const handleBack = () => {
  router.back();
};

const handleEditEnvironment = () => {
  Object.assign(formState, {
    name: environment.value.name,
    type: environment.value.type,
    description: environment.value.description,
  });
  drawerVisible.value = true;
};

const handleDrawerClose = () => {
  drawerVisible.value = false;
  formRef.value?.resetFields();
};

const handleSubmit = async () => {
  if (!checkPermission('environment', 'edit')) {
    return;
  }
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const response = await axios.put('/api/environments/', {
      environment_id: environment.value.environment_id,
      name: formState.name,
      type: formState.type,
      description: formState.description,
    }, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('更新环境成功');
      handleDrawerClose();
      fetchEnvironmentDetail();
    } else {
      throw new Error(response.data.message || '更新环境失败');
    }
  } catch (error) {
    message.error(error.response?.data?.message || error.message || '更新环境失败');
  } finally {
    submitLoading.value = false;
  }
};

onMounted(() => {
  fetchEnvironmentDetail();
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
}

.info-label {
  color: rgba(0, 0, 0, 0.45);
  min-width: 100px;
}

.info-value {
  color: rgba(0, 0, 0, 0.85);
  flex: 1;
}

:deep(.ant-drawer-body) {
  padding: 24px;
}

:deep(.ant-drawer-footer) {
  text-align: right;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}
</style> 