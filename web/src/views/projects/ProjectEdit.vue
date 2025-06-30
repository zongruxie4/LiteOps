<template>
  <div class="project-edit">
    <div class="page-header">
      <a-page-header
        title="编辑项目"
        @back="handleBack"
      />
    </div>

    <a-card>
      <a-form
        :model="formState"
        :rules="rules"
        ref="formRef"
        :label-col="{ span: 4 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="项目名称" name="name">
          <a-input v-model:value="formState.name" placeholder="请输入项目名称" />
        </a-form-item>

        <a-form-item label="项目描述" name="description">
          <a-textarea
            v-model:value="formState.description"
            placeholder="请输入项目描述"
            :rows="4"
          />
        </a-form-item>

        <a-form-item label="GitLab 仓库" name="repository">
          <a-input
            v-model:value="formState.repository"
            placeholder="请输入完整的GitLab仓库地址，例如：git.example.com/group/project.git"
          />
        </a-form-item>

        <a-form-item label="GitLab凭证" name="gitlabCredentialId">
          <a-select
            v-model:value="formState.gitlabCredentialId"
            placeholder="请选择GitLab凭证"
            :options="gitlabCredentials"
            :loading="credentialsLoading"
          >
            <template #suffixIcon>
              <ReloadOutlined
                :spin="credentialsLoading"
                @click="loadGitlabCredentials"
              />
            </template>
          </a-select>
        </a-form-item>

        <a-form-item :wrapper-col="{ offset: 4, span: 16 }">
          <a-space>
            <a-button type="primary" :loading="submitLoading" @click="handleSubmit">保存修改</a-button>
            <a-button @click="handleReset">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { message } from 'ant-design-vue';
import { ReloadOutlined } from '@ant-design/icons-vue';
import axios from 'axios';

const router = useRouter();
const route = useRoute();
const formRef = ref();
const credentialsLoading = ref(false);
const submitLoading = ref(false);
const gitlabCredentials = ref([]);
const loading = ref(false);

const formState = reactive({
  name: '',
  description: '',
  repository: '',
  gitlabCredentialId: undefined,
  project_id: '',
});

const rules = {
  name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 3, max: 50, message: '项目名称长度应在 3-50 个字符之间', trigger: 'blur' },
  ],
  repository: [
    { required: true, message: '请输入 GitLab 仓库地址', trigger: 'blur' },
  ],
  gitlabCredentialId: [
    { required: true, message: '请选择 GitLab 凭证', trigger: 'change' },
  ],
};

// 加载GitLab凭证列表
const loadGitlabCredentials = async () => {
  credentialsLoading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/gitlab-credentials/', {
      headers: {
        'Authorization': token
      }
    });
    
    if (response.data.code === 200) {
      gitlabCredentials.value = response.data.data.map(item => ({
        label: item.name,
        value: item.credential_id
      }));
    } else {
      message.error(response.data.message || '加载GitLab凭证失败');
    }
  } catch (error) {
    message.error('加载GitLab凭证失败');
    console.error('Load credentials error:', error);
  } finally {
    credentialsLoading.value = false;
  }
};

// 加载项目详情
const loadProjectDetail = async () => {
  const projectId = route.query.project_id;
  if (!projectId) {
    message.error('项目ID不能为空');
    router.push('/projects/list');
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
      const projectData = response.data.data.find(item => item.project_id === projectId);
      if (projectData) {
        formState.project_id = projectData.project_id;
        formState.name = projectData.name;
        formState.description = projectData.description || '';
        formState.repository = projectData.repository;
        formState.gitlabCredentialId = projectData.gitlab_credential?.credential_id;
      } else {
        throw new Error('未找到项目信息');
      }
    } else {
      throw new Error(response.data.message || '加载项目详情失败');
    }
  } catch (error) {
    message.error(error.message || '加载项目详情失败');
    console.error('Load project detail error:', error);
    router.push('/projects/list');
  } finally {
    loading.value = false;
  }
};

const handleBack = () => {
  router.back();
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const response = await axios.put('/api/projects/', {
      project_id: formState.project_id,
      name: formState.name,
      description: formState.description,
      repository: formState.repository,
      gitlabCredentialId: formState.gitlabCredentialId
    }, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('更新项目成功');
      router.push('/projects/list');
    } else {
      throw new Error(response.data.message || '更新项目失败');
    }
  } catch (error) {
    message.error(error.response?.data?.message || error.message);
    console.error('Update project error:', error);
  } finally {
    submitLoading.value = false;
  }
};

const handleReset = () => {
  loadProjectDetail(); 
};

onMounted(() => {
  loadGitlabCredentials();
  loadProjectDetail();
});
</script>

<style scoped>
.project-edit {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
  background: #fff;
  border-radius: 4px;
}

:deep(.ant-page-header) {
  padding: 16px 24px;
}

:deep(.ant-card) {
  border-radius: 4px;
}

:deep(.ant-form) {
  padding: 24px 0;
}
</style> 