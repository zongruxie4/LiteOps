<template>
  <div class="project-detail">
    <div class="page-header">
      <a-page-header
        :title="project?.name || '项目详情'"
        @back="handleBack"
      >
        <template #extra>
          <a-space>
            <a-button @click="handleEditProject">
              <template #icon><EditOutlined /></template>
              编辑项目
            </a-button>
          </a-space>
        </template>
      </a-page-header>
    </div>

    <!-- 项目基本信息 -->
    <a-card title="项目信息" :loading="loading">
      <div class="info-list">
        <div class="info-item">
          <span class="info-label">项目名称：</span>
          <span class="info-value">{{ project?.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">项目ID：</span>
          <span class="info-value">{{ project?.project_id }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">服务类别：</span>
          <span class="info-value">{{ getCategoryText(project?.category) }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">GitLab仓库：</span>
          <span class="info-value">{{ project?.repository }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">创建者：</span>
          <span class="info-value">{{ project?.creator?.name }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">创建时间：</span>
          <span class="info-value">{{ project?.create_time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">更新时间：</span>
          <span class="info-value">{{ project?.update_time }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">项目描述：</span>
          <span class="info-value">{{ project?.description || '暂无描述' }}</span>
        </div>
      </div>
    </a-card>

    <!-- 编辑项目抽屉 -->
    <a-drawer
      v-model:open="projectDrawerVisible"
      title="编辑项目"
      width="600px"
      @close="handleProjectDrawerClose"
    >
      <a-form
        :model="projectForm"
        :rules="projectRules"
        ref="projectFormRef"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="项目名称" name="name">
          <a-input v-model:value="projectForm.name" placeholder="请输入项目名称" />
        </a-form-item>

        <a-form-item label="项目描述" name="description">
          <a-textarea
            v-model:value="projectForm.description"
            placeholder="请输入项目描述"
            :rows="4"
          />
        </a-form-item>

        <a-form-item label="服务类别" name="category">
          <a-select
            v-model:value="projectForm.category"
            placeholder="请选择服务类别"
          >
            <a-select-option value="frontend">前端服务</a-select-option>
            <a-select-option value="backend">后端服务</a-select-option>
            <a-select-option value="mobile">移动端服务</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="GitLab仓库" name="repository">
          <a-input
            v-model:value="projectForm.repository"
            placeholder="请输入完整的GitLab仓库地址"
          />
        </a-form-item>
      </a-form>

      <template #footer>
        <a-space>
          <a-button @click="handleProjectDrawerClose">取消</a-button>
          <a-button
            type="primary"
            :loading="projectSubmitLoading"
            @click="handleProjectSubmit"
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
import {
  EditOutlined,
  ReloadOutlined
} from '@ant-design/icons-vue';
import axios from 'axios';
import { checkPermission } from '../../utils/permission';

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const project = ref(null);

// 项目编辑相关
const projectDrawerVisible = ref(false);
const projectFormRef = ref();
const projectSubmitLoading = ref(false);

const projectForm = ref({
  name: '',
  description: '',
  category: '',
  repository: '',
});

const projectRules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 3, max: 50, message: '项目名称长度应在 3-50 个字符之间', trigger: 'blur' },
  ],
  category: [
    { required: true, message: '请选择服务类别', trigger: 'change' },
  ],
  repository: [
    { required: true, message: '请输入GitLab仓库地址', trigger: 'blur' },
  ],
};

const getCategoryText = (category) => {
  const texts = {
    frontend: '前端服务',
    backend: '后端服务',
    mobile: '移动端服务'
  };
  return texts[category] || '其他服务';
};

const fetchProjectDetail = async () => {
  const projectId = route.query.project_id;
  if (!projectId) {
    message.error('项目ID不能为空');
    router.push('/projects/list');
    return;
  }

  if (!checkPermission('project', 'view')) {
    router.push('/dashboard');
    return;
  }

  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/projects/', {
      headers: {
        'Authorization': token
      },
      params: {
        project_id: projectId
      }
    });
    
    if (response.data.code === 200) {
      project.value = response.data.data[0];
      
      // 检查用户是否有权限访问此项目
      if (!checkPermission('project', 'view', project.value.project_id)) {
        router.push('/projects/list');
        return;
      }
    } else {
      throw new Error(response.data.message || '获取项目详情失败');
    }
  } catch (error) {
    message.error(error.message);
    router.push('/projects/list');
  } finally {
    loading.value = false;
  }
};

const handleBack = () => {
  router.back();
};

const handleEditProject = () => {
  if (!checkPermission('project', 'edit', project.value.project_id)) {
    return;
  }
  
  projectForm.value = {
    name: project.value.name,
    description: project.value.description,
    category: project.value.category,
    repository: project.value.repository,
  };
  projectDrawerVisible.value = true;
};

const handleProjectDrawerClose = () => {
  projectDrawerVisible.value = false;
  projectFormRef.value?.resetFields();
};

const handleProjectSubmit = async () => {
  try {
    await projectFormRef.value.validate();
    projectSubmitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const response = await axios.put('/api/projects/', {
      project_id: project.value.project_id,
      name: projectForm.value.name,
      description: projectForm.value.description,
      category: projectForm.value.category,
      repository: projectForm.value.repository,
    }, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('更新项目成功');
      handleProjectDrawerClose();
      fetchProjectDetail();
    } else {
      throw new Error(response.data.message || '更新项目失败');
    }
  } catch (error) {
    message.error(error.response?.data?.message || error.message || '更新项目失败');
  } finally {
    projectSubmitLoading.value = false;
  }
};

onMounted(() => {
  fetchProjectDetail();
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