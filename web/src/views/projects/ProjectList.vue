<template>
  <div class="project-list">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>项目列表</h2>
        </a-col>
        <a-col>
          <a-button type="primary" @click="handleCreateProject">
            <template #icon><PlusOutlined /></template>
            新建项目
          </a-button>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <!-- 搜索区域 -->
      <div class="search-area">
        <a-form layout="inline" :style="{ display: 'flex', justifyContent: 'flex-end' }">
          <a-form-item label="项目名称">
            <a-input
              v-model:value="searchForm.name"
              placeholder="请输入项目名称"
              allow-clear
            />
          </a-form-item>
          <a-form-item label="服务类别">
            <a-select
              v-model:value="searchForm.category"
              placeholder="请选择服务类别"
              style="width: 200px"
              allow-clear
            >
              <a-select-option value="frontend">前端服务</a-select-option>
              <a-select-option value="backend">后端服务</a-select-option>
              <a-select-option value="mobile">移动端服务</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item>
            <a-button type="primary" :loading="loading" @click="handleSearch">
              <template #icon><SearchOutlined /></template>
              搜索
            </a-button>
          </a-form-item>
        </a-form>
      </div>

      <a-table
        :columns="columns"
        :data-source="filteredProjects"
        :loading="loading"
        row-key="project_id"
        :locale="{ emptyText: '暂无数据' }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span class="project-name" @click="handleViewProject(record)">{{ record.name }}</span>
          </template>
          <template v-if="column.key === 'category'">
            {{ getCategoryText(record.category) }}
          </template>
          <template v-if="column.key === 'creator'">
            {{ record.creator.name }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" class="action-button" @click="handleViewProject(record)">查看</a-button>
              <a-popconfirm
                title="确定要删除这个项目吗？"
                @confirm="handleDeleteProject(record)"
              >
                <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建项目抽屉 -->
    <a-drawer
      v-model:open="drawerVisible"
      title="新建项目"
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

        <a-form-item label="服务类别" name="category">
          <a-select
            v-model:value="formState.category"
            placeholder="请选择服务类别"
          >
            <a-select-option value="frontend">前端服务</a-select-option>
            <a-select-option value="backend">后端服务</a-select-option>
            <a-select-option value="mobile">移动端服务</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="GitLab仓库" name="repository">
          <a-input
            v-model:value="formState.repository"
            placeholder="请输入完整的GitLab仓库地址"
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
            创建
          </a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { message } from 'ant-design-vue';
import { PlusOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { 
  getPermittedProjectIds, 
  checkPermission
} from '../../utils/permission';

const router = useRouter();
const loading = ref(false);
const projects = ref([]);
const drawerVisible = ref(false);
const formRef = ref();
const submitLoading = ref(false);

const formState = reactive({
  name: '',
  description: '',
  category: undefined,
  repository: '',
});

const searchForm = reactive({
  name: '',
  category: undefined
});

const columns = [
  {
    title: '项目名称',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '项目描述',
    dataIndex: 'description',
    key: 'description',
  },
  {
    title: '服务类别',
    dataIndex: 'category',
    key: 'category',
  },
  {
    title: '仓库地址',
    dataIndex: 'repository',
    key: 'repository',
  },
  {
    title: '创建者',
    key: 'creator',
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
    key: 'create_time',
  },
  {
    title: '操作',
    key: 'action',
  },
];

const rules = {
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

const filteredProjects = computed(() => {
  const permittedProjectIds = getPermittedProjectIds();
  
  if (permittedProjectIds === null) {
    return projects.value;
  }
  
  return projects.value.filter(project => 
    permittedProjectIds.includes(project.project_id)
  );
});

const getCategoryText = (category) => {
  const texts = {
    frontend: '前端服务',
    backend: '后端服务',
  };
  return texts[category] || '其他服务';
};

const fetchProjects = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const params = {};
    
    if (searchForm.name) {
      params.name = searchForm.name;
    }
    if (searchForm.category) {
      params.category = searchForm.category;
    }

    const response = await axios.get('/api/projects/', {
      headers: {
        'Authorization': token
      },
      params: params
    });
    
    if (response.data.code === 200) {
      projects.value = response.data.data;
    } else {
      message.error(response.data.message || '获取项目列表失败');
    }
  } catch (error) {
    message.error('获取项目列表失败');
    console.error('Fetch projects error:', error);
  } finally {
    loading.value = false;
  }
};

const handleCreateProject = () => {
  if (!checkPermission('project', 'create')) {
    return;
  }
  drawerVisible.value = true;
};

const handleDrawerClose = () => {
  drawerVisible.value = false;
  formRef.value?.resetFields();
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/projects/', {
      name: formState.name,
      description: formState.description,
      category: formState.category,
      repository: formState.repository,
    }, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('项目创建成功');
      handleDrawerClose();
      fetchProjects();
    } else {
      throw new Error(response.data.message || '创建项目失败');
    }
  } catch (error) {
    message.error(error.response?.data?.message || error.message || '创建项目失败');
  } finally {
    submitLoading.value = false;
  }
};

const handleViewProject = (record) => {
  if (!checkPermission('project', 'view', record.project_id)) {
    return;
  }
  router.push({
    path: '/projects/detail',
    query: { project_id: record.project_id }
  });
};

const handleDeleteProject = async (record) => {
  if (!checkPermission('project', 'delete', record.project_id)) {
    return;
  }
  
  try {
    const token = localStorage.getItem('token');
    const response = await axios.delete('/api/projects/', {
      headers: {
        'Authorization': token
      },
      data: {
        project_id: record.project_id
      }
    });
    
    if (response.data.code === 200) {
      message.success('删除项目成功');
      fetchProjects();
    } else {
      message.error(response.data.message || '删除项目失败');
    }
  } catch (error) {
    message.error('删除项目失败');
    console.error('Delete project error:', error);
  }
};

const handleSearch = () => {
  fetchProjects();
};

onMounted(() => {
  fetchProjects();
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

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
}

:deep(.ant-drawer-body) {
  padding: 24px;
}

:deep(.ant-drawer-footer) {
  text-align: right;
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}

.search-area {
  margin-bottom: 16px;
}

.project-name {
  color: rgba(0, 0, 0);
  cursor: pointer;
}

.project-name:hover {
  color: rgba(0, 0, 0, 0.65);
}

.action-button {
  color: #1890ff;
}

.action-button:hover {
  color: #40a9ff;
}

:deep(.ant-btn-link) {
  padding: 4px 8px;
}

:deep(.ant-form-item) {
  margin-bottom: 16px;
  margin-right: 16px;
}

:deep(.ant-form-item:last-child) {
  margin-right: 0;
}
</style> 