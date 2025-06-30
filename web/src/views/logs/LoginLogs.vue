<template>
  <div class="login-logs-container">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>登录日志</h2>
        </a-col>
        <a-col>
          <!-- 搜索表单 -->
          <a-form layout="inline">
            <a-form-item label="用户名">
              <a-input v-model:value="searchForm.username" placeholder="请输入用户名" allowClear />
            </a-form-item>
            <a-form-item label="IP地址">
              <a-input v-model:value="searchForm.ip_address" placeholder="请输入IP地址" allowClear />
            </a-form-item>
            <a-form-item label="登录状态">
              <a-select v-model:value="searchForm.status" style="width: 120px" allowClear>
                <a-select-option value="success">成功</a-select-option>
                <a-select-option value="failed">失败</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="handleSearch">查询</a-button>
              <a-button style="margin-left: 8px" @click="handleReset">重置</a-button>
            </a-form-item>
          </a-form>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <!-- 数据表格 -->
      <a-table
        :columns="columns"
        :data-source="tableData"
        :pagination="pagination"
        :loading="loading"
        @change="handleTableChange"
        rowKey="log_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'status'">
            <a-tag :color="record.status === 'success' ? 'rgba(56, 158, 13, 0.8)' : 'rgba(255,77,79,0.8)'">
              {{ record.status === 'success' ? '成功' : '失败' }}
            </a-tag>
          </template>
          <template v-if="column.dataIndex === 'login_time'">
            {{ record.login_time }}
          </template>
          <template v-if="column.dataIndex === 'action'">
            <a-button type="link" @click="handleViewDetails(record)">详情</a-button>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { checkPermission } from '../../utils/permission';

const router = useRouter();

const columns = [
  {
    title: '用户名',
    dataIndex: 'username',
    key: 'username',
  },
  {
    title: 'IP地址',
    dataIndex: 'ip_address',
    key: 'ip_address',
  },
  {
    title: '登录状态',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: '登录时间',
    dataIndex: 'login_time',
    key: 'login_time',
  },
  {
    title: '操作',
    dataIndex: 'action',
    key: 'action',
  }
];

// 表格数据
const tableData = ref([]);
const loading = ref(false);
const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
  showTotal: (total) => `共 ${total} 条记录`,
});

// 搜索表单
const searchForm = reactive({
  username: '',
  ip_address: '',
  status: undefined
});

// 初始化
onMounted(() => {
  // 检查权限
  if (checkPermission('logs_login', 'view')) {
    getLoginLogs();
  }
});

// 获取登录日志数据
const getLoginLogs = async () => {
  try {
    loading.value = true;
    
    // 构建查询参数
    const params = {
      page: pagination.current,
      page_size: pagination.pageSize,
      username: searchForm.username,
      ip_address: searchForm.ip_address,
      status: searchForm.status,
    };
    
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/logs/login/', {
      params,
      headers: {
        'Authorization': token
      }
    });
    
    if (response.data.code === 200) {
      const { logs, total } = response.data.data;
      tableData.value = logs;
      pagination.total = total;
    } else {
      message.error(response.data.message || '获取登录日志失败');
    }
  } catch (error) {
    console.error('获取登录日志失败:', error);
    message.error('获取登录日志失败');
  } finally {
    loading.value = false;
  }
};

const handleSearch = () => {
  pagination.current = 1;
  getLoginLogs();
};

const handleReset = () => {
  // 重置搜索表单
  searchForm.username = '';
  searchForm.ip_address = '';
  searchForm.status = undefined;
  
  // 重置分页并查询
  pagination.current = 1;
  getLoginLogs();
};

const handleTableChange = (pag) => {
  pagination.current = pag.current;
  pagination.pageSize = pag.pageSize;
  getLoginLogs();
};

// 查看详情 - 跳转到详情页
const handleViewDetails = (record) => {
  router.push({
    path: '/logs/login/detail',
    query: { log_id: record.log_id }
  });
};
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

:deep(.ant-form-item) {
  margin-bottom: 16px;
  margin-right: 16px;
}

:deep(.ant-form-item:last-child) {
  margin-right: 0;
}

:deep(.ant-input) {
  width: 140px;
}

:deep(.ant-select) {
  width: 120px;
}
</style>