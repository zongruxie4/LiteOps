<template>
  <div class="user-list">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>用户管理</h2>
        </a-col>
        <a-col>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><UserAddOutlined /></template>
            添加用户
          </a-button>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <a-table 
        :columns="columns" 
        :data-source="users" 
        :loading="loading"
        :pagination="{ 
          showSizeChanger: true, 
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          showTotal: total => `共 ${total} 条记录`
        }"
        rowKey="user_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <span :style="{ color: record.status === 0 ? '#ff4d4f' : 'inherit' }">
              {{ record.status === 1 ? '正常' : '锁定' }}
            </span>
          </template>
          <template v-else-if="column.key === 'roles'">
            <a-space>
              <a-tag v-for="role in record.roles" :key="role.role_id" color="">
                {{ role.name }}
              </a-tag>
            </a-space>
          </template>
          <template v-else-if="column.key === 'user_type'">
            <a-tag :color="record.user_type === 'ldap' ? 'rgba(56, 158, 13, 0.8)' : 'rgba(22,119,255,0.8)'">
              {{ record.user_type === 'ldap' ? 'LDAP' : '系统' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a @click="showEditModal(record)">编辑</a>
              <a-divider type="vertical" />
              <a-popconfirm
                title="确定要删除此用户吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(record)"
              >
              <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
              <a-divider type="vertical" />
              <a-popconfirm
                :title="record.status === 1 ? '确定要锁定此用户吗？' : '确定要解锁此用户吗？'"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleToggleStatus(record)"
              >
                <a>{{ record.status === 1 ? '锁定' : '解锁' }}</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 创建/编辑用户模态框 -->
    <a-modal
      v-model:open="modalVisible"
      :title="modalTitle"
      :maskClosable="false"
      @ok="handleSubmitForm"
      @cancel="resetForm"
      :confirm-loading="submitting"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :rules="formRules"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item label="用户名" name="username">
          <a-input v-model:value="formState.username" :disabled="!!formState.user_id" />
        </a-form-item>
        <a-form-item label="姓名" name="name">
          <a-input 
            v-model:value="formState.name" 
            :disabled="formState.user_type === 'ldap'"
          />
          <div v-if="formState.user_type === 'ldap'" class="form-help">LDAP用户信息由LDAP服务器管理</div>
        </a-form-item>
        <a-form-item label="邮箱" name="email">
          <a-input 
            v-model:value="formState.email" 
            :disabled="formState.user_type === 'ldap'"
          />
          <div v-if="formState.user_type === 'ldap'" class="form-help">LDAP用户信息由LDAP服务器管理</div>
        </a-form-item>
        <a-form-item label="密码" name="password" v-if="formState.user_type !== 'ldap'">
          <a-input-password v-model:value="formState.password" />
          <div v-if="!!formState.user_id" class="form-help">不修改请留空</div>
        </a-form-item>
        <a-form-item label="角色" name="role_ids">
          <a-select 
            v-model:value="formState.role_ids" 
            mode="multiple" 
            placeholder="请选择角色"
            :loading="rolesLoading"
          >
            <a-select-option v-for="role in roles" :key="role.role_id" :value="role.role_id">
              {{ role.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态" name="status">
          <a-radio-group v-model:value="formState.status">
            <a-radio :value="1">正常</a-radio>
            <a-radio :value="0">锁定</a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import { UserAddOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { checkPermission } from '../../utils/permission';

// 表格列定义
const columns = [
  {
    title: '用户名',
    dataIndex: 'username',
    key: 'username',
  },
  {
    title: '姓名',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '邮箱',
    dataIndex: 'email',
    key: 'email',
  },
  {
    title: '角色',
    dataIndex: 'roles',
    key: 'roles',
  },
  {
    title: '用户类型',
    dataIndex: 'user_type',
    key: 'user_type',
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
  },
  {
    title: '最后登录时间',
    dataIndex: 'login_time',
    key: 'login_time',
  },
  {
    title: '操作',
    key: 'action',
  },
];

// 数据相关的响应式变量
const users = ref([]);
const roles = ref([]);
const loading = ref(false);
const rolesLoading = ref(false);
const formRef = ref(null);

// 安全配置
const securityConfig = ref({
  min_password_length: 8,
  password_complexity: ['lowercase', 'number']
});

// 获取安全配置
const fetchSecurityConfig = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/system/security/', {
      headers: { 'Authorization': token }
    });
    if (response.data.code === 200) {
      securityConfig.value = response.data.data;
    }
  } catch (error) {
    console.error('获取安全配置失败:', error);
  }
};

// 获取用户列表
const fetchUsers = async () => {
  loading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/users/', {
      headers: {
        'Authorization': token
      }
    });
    if (response.data.code === 200) {
      users.value = response.data.data;
    } else {
      message.error(response.data.message || '获取用户列表失败');
    }
  } catch (error) {
    console.error('获取用户列表失败:', error);
    message.error('获取用户列表失败');
  } finally {
    loading.value = false;
  }
};

// 获取角色列表
const fetchRoles = async () => {
  rolesLoading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/roles/', {
      headers: {
        'Authorization': token
      }
    });
    if (response.data.code === 200) {
      roles.value = response.data.data;
    } else {
      message.error(response.data.message || '获取角色列表失败');
    }
  } catch (error) {
    console.error('获取角色列表失败:', error);
    message.error('获取角色列表失败');
  } finally {
    rolesLoading.value = false;
  }
};

// 初始化
onMounted(() => {
  fetchSecurityConfig();
  fetchUsers();
  fetchRoles();
});

const modalVisible = ref(false);
const submitting = ref(false);
const formState = reactive({
  user_id: '',
  username: '',
  name: '',
  email: '',
  password: '',
  role_ids: [],
  status: 1,
  user_type: 'system'
});

// 动态密码验证规则
const passwordValidator = (rule, value) => {
  // LDAP用户不需要验证密码
  if (formState.user_type === 'ldap') {
    return Promise.resolve();
  }
  if (formState.user_id && !value) {
    return Promise.resolve();
  }
  if (!value) {
    return Promise.reject('请输入密码');
  }
  
  const config = securityConfig.value;
  
  // 检查密码长度
  if (value.length < config.min_password_length) {
    return Promise.reject(`密码长度不能少于${config.min_password_length}位`);
  }
  
  // 检查密码复杂度
  const complexityChecks = {
    'uppercase': { pattern: /[A-Z]/, description: '大写字母' },
    'lowercase': { pattern: /[a-z]/, description: '小写字母' },
    'number': { pattern: /[0-9]/, description: '数字' },
    'special': { pattern: /[!@#$%^&*(),.?":{}|<>]/, description: '特殊字符' }
  };
  
  const missingRequirements = [];
  for (const requirement of config.password_complexity) {
    if (complexityChecks[requirement]) {
      const { pattern, description } = complexityChecks[requirement];
      if (!pattern.test(value)) {
        missingRequirements.push(description);
      }
    }
  }
  
  if (missingRequirements.length > 0) {
    return Promise.reject(`密码必须包含: ${missingRequirements.join(', ')}`);
  }
  
  return Promise.resolve();
};

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 20, message: '用户名长度必须在3-20个字符之间', trigger: 'blur' }
  ],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { validator: passwordValidator, trigger: 'blur' }
  ],
  role_ids: [
    { required: true, type: 'array', message: '请选择至少一个角色', trigger: 'change' }
  ],
  status: [
    { required: true, message: '请选择状态', trigger: 'change' }
  ]
};

// 计算属性
const modalTitle = computed(() => {
  return formState.user_id ? '编辑用户' : '添加用户';
});

// 显示创建模态框
const showCreateModal = () => {
  if (!checkPermission('user', 'create')) {
    message.error('你没有权限执行此操作');
    return;
  }
  
  resetForm();
  modalVisible.value = true;
};

// 显示编辑模态框
const showEditModal = (record) => {
  if (!checkPermission('user', 'edit')) {
    message.error('你没有权限执行此操作');
    return;
  }
  
  resetForm();
  formState.user_id = record.user_id;
  formState.username = record.username;
  formState.name = record.name;
  formState.email = record.email;
  formState.status = record.status;
  formState.user_type = record.user_type || 'system';
  formState.role_ids = record.roles.map(role => role.role_id);
  modalVisible.value = true;
};

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  Object.assign(formState, {
    user_id: '',
    username: '',
    name: '',
    email: '',
    password: '',
    role_ids: [],
    status: 1,
    user_type: 'system'
  });
};

// 提交表单
const handleSubmitForm = () => {
  formRef.value.validate().then(async () => {
    submitting.value = true;
    try {
      // 创建或更新用户
      const url = formState.user_id ? '/api/users/' : '/api/users/';
      const method = formState.user_id ? 'put' : 'post';
      
      // 如果是编辑模式且密码为空，则不发送密码字段
      const data = { ...formState };
      if (formState.user_id && !formState.password) {
        delete data.password;
      }
      
      const token = localStorage.getItem('token');
      const response = await axios({
        method,
        url,
        data,
        headers: {
          'Authorization': token
        }
      });
      
      if (response.data.code === 200) {
        message.success(formState.user_id ? '更新用户成功' : '创建用户成功');
        modalVisible.value = false;
        fetchUsers();
      } else {
        message.error(response.data.message || '操作失败');
      }
    } catch (error) {
      console.error('操作失败:', error);
      message.error('操作失败');
    } finally {
      submitting.value = false;
    }
  }).catch(errors => {
    console.log('表单验证失败:', errors);
  });
};

// 删除用户
const handleDelete = async (record) => {
  // 检查用户是否有权限删除用户
  if (!checkPermission('user', 'delete')) {
    message.error('你没有权限执行此操作');
    return;
  }
  
  try {
    const token = localStorage.getItem('token');
    const response = await axios({
      method: 'delete',
      url: '/api/users/',
      data: {
        user_id: record.user_id
      },
      headers: {
        'Authorization': token
      }
    });
    
    if (response.data.code === 200) {
      message.success('删除用户成功');
      fetchUsers();
    } else {
      message.error(response.data.message || '删除用户失败');
    }
  } catch (error) {
    console.error('删除用户失败:', error);
    message.error('删除用户失败');
  }
};

// 切换用户状态
const handleToggleStatus = async (record) => {
  // 检查用户是否有权限切换用户状态
  if (!checkPermission('user', 'toggle_status')) {
    message.error('你没有权限执行此操作');
    return;
  }
  
  try {
    const token = localStorage.getItem('token');
    const response = await axios({
      method: 'put',
      url: '/api/users/',
      data: {
        user_id: record.user_id,
        status: record.status === 1 ? 0 : 1
      },
      headers: {
        'Authorization': token
      }
    });
    
    if (response.data.code === 200) {
      message.success(record.status === 1 ? '用户已锁定' : '用户已解锁');
      fetchUsers();
    } else {
      message.error(response.data.message || '更新用户状态失败');
    }
  } catch (error) {
    console.error('更新用户状态失败:', error);
    message.error('更新用户状态失败');
  }
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

.form-help {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  margin-top: 4px;
}
</style> 