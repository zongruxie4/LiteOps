<template>
  <div class="environment-list">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>环境列表</h2>
        </a-col>
        <a-col>
          <a-button type="primary" @click="handleCreateEnvironment">
            <template #icon><PlusOutlined /></template>
            新建环境
          </a-button>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <!-- 搜索区域 -->
      <div class="search-area">
        <a-form layout="inline" :style="{ display: 'flex', justifyContent: 'flex-end' }">
          <a-form-item label="环境名称">
            <a-input
              v-model:value="searchForm.name"
              placeholder="请输入环境名称"
              allow-clear
              @pressEnter="handleSearch"
            />
          </a-form-item>
          <a-form-item label="环境类型">
            <a-select
              v-model:value="searchForm.type"
              placeholder="请选择环境类型"
              style="width: 160px"
              allow-clear
            >
              <a-select-option value="development">开发环境</a-select-option>
              <a-select-option value="testing">测试环境</a-select-option>
              <a-select-option value="staging">预发布环境</a-select-option>
              <a-select-option value="production">生产环境</a-select-option>
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
        :data-source="environments"
        :loading="loading"
        row-key="environment_id"
        :locale="{ emptyText: '暂无数据' }"
        :pagination="{
          total: total,
          current: current,
          pageSize: pageSize,
          pageSizeOptions: ['10', '20', '50', '100'],
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span class="environment-name" @click="handleEnvironmentDetail(record)">{{ record.name }}</span>
          </template>
          <template v-if="column.key === 'type'">
            <span>{{ getEnvironmentTypeText(record.type) }}</span>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" class="action-button" @click="handleEnvironmentDetail(record)">查看</a-button>
              <!-- <a-button type="link" class="action-button" @click="handleEditEnvironment(record)">编辑</a-button> -->
              <a-button type="link" danger @click="handleDeleteEnvironment(record)">删除</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新建/编辑环境抽屉 -->
    <a-drawer
      v-model:open="drawerVisible"
      :title="isEdit ? '编辑环境' : '新建环境'"
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
            {{ isEdit ? '保存' : '创建' }}
          </a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { message, Modal } from 'ant-design-vue';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { checkPermission, hasFunctionPermission } from '../../utils/permission';

const router = useRouter();
const loading = ref(false);
const environments = ref([]);
const drawerVisible = ref(false);
const formRef = ref();
const submitLoading = ref(false);
const isEdit = ref(false);
const pageSize = ref(10);
const current = ref(1);
const total = ref(0);

const formState = reactive({
  name: '',
  type: undefined,
  description: '',
});

const searchForm = reactive({
  name: '',
  type: undefined,
});

const columns = [
  {
    title: '环境名称',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '环境类型',
    key: 'type',
  },
  {
    title: '环境描述',
    dataIndex: 'description',
    key: 'description',
    ellipsis: true,
  },
  {
    title: '创建者',
    key: 'creator',
    customRender: ({ record }) => record.creator?.name || '未知',
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



const fetchEnvironments = async () => {
  // 检查查看环境列表
  if (!checkPermission('environment', 'view')) {
    return;
  }
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const params = {
      page: current.value,
      page_size: pageSize.value,
      ...searchForm,
    };

    const response = await axios.get('/api/environments/', {
      headers: {
        'Authorization': token
      },
      params: params
    });
    
    if (response.data.code === 200) {
      environments.value = response.data.data;
      total.value = response.data.total;
    } else {
      message.error(response.data.message || '获取环境列表失败');
    }
  } catch (error) {
    message.error('获取环境列表失败');
    console.error('Fetch environments error:', error);
  } finally {
    loading.value = false;
  }
};

const handleCreateEnvironment = () => {
  // 检查创建环境权限
  if (!checkPermission('environment', 'create')) {
    return;
  }
  isEdit.value = false;
  drawerVisible.value = true;
};

const handleEditEnvironment = (record) => {
  // 检查编辑环境权限
  if (!checkPermission('environment', 'edit')) {
    return;
  }
  
  isEdit.value = true;
  Object.assign(formState, {
    environment_id: record.environment_id,
    name: record.name,
    type: record.type,
    description: record.description,
  });
  drawerVisible.value = true;
};

const handleDrawerClose = () => {
  drawerVisible.value = false;
  formRef.value?.resetFields();
  Object.assign(formState, {
    name: '',
    type: undefined,
    description: '',
  });
};

const handleSubmit = async () => {
  if (isEdit.value) {
    if (!checkPermission('environment', 'edit')) {
      return;
    }
  } else {
    if (!checkPermission('environment', 'create')) {
      return;
    }
  }
  
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const url = isEdit.value ? '/api/environments/' : '/api/environments/';
    const method = isEdit.value ? 'put' : 'post';
    const data = isEdit.value ? {
      environment_id: formState.environment_id,
      name: formState.name,
      type: formState.type,
      description: formState.description,
    } : formState;

    const response = await axios[method](url, data, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success(isEdit.value ? '更新环境成功' : '创建环境成功');
      handleDrawerClose();
      fetchEnvironments();
    } else {
      throw new Error(response.data.message || (isEdit.value ? '更新环境失败' : '创建环境失败'));
    }
  } catch (error) {
    message.error(error.response?.data?.message || error.message || (isEdit.value ? '更新环境失败' : '创建环境失败'));
  } finally {
    submitLoading.value = false;
  }
};

const handleEnvironmentDetail = (record) => {
  if (!checkPermission('environment', 'view', record.environment_id)) {
    return;
  }
  router.push({
    path: '/environments/detail',
    query: { environment_id: record.environment_id }
  });
};

const handleDeleteEnvironment = async (record) => {
  // 检查删除权限
  if (!checkPermission('environment', 'delete')) {
    return;
  }
  
  // 显示确认对话框，警告可能的影响
  Modal.confirm({
    title: '确认删除环境',
    content: `确定要删除环境"${record.name}"吗？\n\n⚠️ 注意：删除环境将同时删除该环境下的所有关联构建任务，此操作不可恢复，请谨慎操作！`,
    okText: '确认删除',
    okType: 'primary',
    cancelText: '取消',
    width: 450,
    style: { top: '20vh' },
    async onOk() {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.delete('/api/environments/', {
          headers: {
            'Authorization': token
          },
          data: {
            environment_id: record.environment_id
          }
        });
        
        if (response.data.code === 200) {
          message.success('删除环境成功');
          fetchEnvironments();
        } else {
          message.error(response.data.message || '删除环境失败');
        }
      } catch (error) {
        message.error('删除环境失败');
        console.error('Delete environment error:', error);
      }
    }
  });
};

const handleSearch = () => {
  current.value = 1;
  fetchEnvironments();
};

const handleTableChange = (pagination, filters, sorter) => {
  current.value = pagination.current;
  pageSize.value = pagination.pageSize;
  fetchEnvironments();
};

onMounted(() => {
  fetchEnvironments();
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

.environment-name {
  color: rgba(0, 0, 0);
  cursor: pointer;
}

.environment-name:hover {
  color: rgba(0, 0, 0, 0.65);
}

:deep(.action-button) {
  color: #1890ff;
  padding: 4px 0;
}

:deep(.action-button:hover) {
  color: #40a9ff;
}

:deep(.ant-btn-dangerous.ant-btn-link) {
  padding: 4px 0;
}

:deep(.ant-form-item) {
  margin-bottom: 16px;
  margin-right: 16px;
}

:deep(.ant-form-item:last-child) {
  margin-right: 0;
}
</style> 