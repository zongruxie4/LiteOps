<template>
  <div class="user-role">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>角色管理</h2>
        </a-col>
        <a-col>
          <a-button type="primary" @click="showCreateModal">
            <template #icon><PlusOutlined /></template>
            添加角色
          </a-button>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <a-table
        :columns="columns"
        :data-source="roles"
        :loading="loading"
        :pagination="{
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: ['10', '20', '50', '100'],
          showTotal: total => `共 ${total} 条记录`
        }"
        rowKey="role_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="showEditModal(record)">编辑</a>
              <a-divider type="vertical" />
              <a-popconfirm
                title="确定要删除此角色吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(record)"
              >
                <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
              <a-divider type="vertical" />
              <a @click="showPermissionModal(record)">权限配置</a>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 创建/编辑角色模态框 -->
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
        <a-form-item label="角色名称" name="name">
          <a-input v-model:value="formState.name" placeholder="请输入角色名称" />
        </a-form-item>
        <a-form-item label="角色描述" name="description">
          <a-textarea
            v-model:value="formState.description"
            placeholder="请输入角色描述"
            :rows="4"
            show-count
            :maxlength="200"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 权限配置模态框 -->
    <a-modal
      v-model:open="permissionModalVisible"
      title="角色权限配置"
      width="800px"
      :maskClosable="false"
      :footer="null"
    >
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="menu" tab="菜单权限">
          <a-tree
            v-model:checkedKeys="menuCheckedKeys"
            :treeData="menuTreeData"
            checkable
            :defaultExpandAll="true"
          />
        </a-tab-pane>

        <a-tab-pane key="function" tab="功能权限">
          <div class="function-permissions">
            <a-collapse v-model:activeKey="activeCollapseKeys">
              <a-collapse-panel
                v-for="module in functionModules"
                :key="module.key"
                :header="module.title"
              >
                <a-checkbox-group
                  v-model:value="functionCheckedKeys[module.key]"
                  :options="module.permissions"
                />
              </a-collapse-panel>
            </a-collapse>
          </div>
        </a-tab-pane>

        <a-tab-pane key="data" tab="数据权限">
          <div class="data-permissions">
            <a-form :model="dataPermissionForm" layout="vertical">
              <a-form-item label="项目权限">
                <a-radio-group v-model:value="dataPermissionForm.project_scope">
                  <a-radio value="all">所有项目</a-radio>
                  <a-radio value="custom">自定义项目</a-radio>
                </a-radio-group>
                <template v-if="dataPermissionForm.project_scope === 'custom'">
                  <a-spin :spinning="projectsLoading">
                    <a-select
                      v-model:value="dataPermissionForm.project_ids"
                      mode="multiple"
                      style="width: 100%; margin-top: 16px"
                      placeholder="请选择项目"
                      :options="projects.map(p => ({ value: p.project_id, label: p.name }))"
                    >
                      <div v-if="!projectsLoading && projects.length === 0" class="empty-message">
                        暂无项目可选
                      </div>
                    </a-select>
                  </a-spin>
                </template>
              </a-form-item>

              <a-form-item label="环境权限">
                <a-radio-group v-model:value="dataPermissionForm.environment_scope">
                  <a-radio value="all">所有环境</a-radio>
                  <a-radio value="custom">自定义环境</a-radio>
                </a-radio-group>
                <template v-if="dataPermissionForm.environment_scope === 'custom'">
                  <a-spin :spinning="environmentsLoading">
                    <a-select
                      v-model:value="dataPermissionForm.environment_types"
                      mode="multiple"
                      style="width: 100%; margin-top: 16px"
                      placeholder="请选择环境类型"
                      :options="environments.map(e => ({ value: e.type, label: e.name }))"
                    >
                      <div v-if="!environmentsLoading && environments.length === 0" class="empty-message">
                        暂无环境类型可选
                      </div>
                    </a-select>
                  </a-spin>
                </template>
              </a-form-item>
            </a-form>
          </div>
        </a-tab-pane>
      </a-tabs>

      <div class="permission-footer">
        <a-space>
          <a-button @click="permissionModalVisible = false">取消</a-button>
          <a-button type="primary" :loading="permissionSubmitting" @click="savePermissions">保存配置</a-button>
        </a-space>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import { message } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import axios from 'axios';

// 表格列定义
const columns = [
  {
    title: '角色名称',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '描述',
    dataIndex: 'description',
    key: 'description',
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

// 数据相关的响应式变量
const roles = ref([]);
const projects = ref([]);
const environments = ref([]);
const loading = ref(false);
const projectsLoading = ref(false);
const environmentsLoading = ref(false);
const formRef = ref(null);

// 获取角色列表
const fetchRoles = async () => {
  loading.value = true;
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
    loading.value = false;
  }
};

// 获取项目列表
const fetchProjects = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/projects/', {
      headers: {
        'Authorization': token
      }
    });
    if (response.data.code === 200) {
      projects.value = response.data.data;
    }
  } catch (error) {
    console.error('获取项目列表失败:', error);
  }
};

// 获取环境列表
const fetchEnvironments = async () => {
  environmentsLoading.value = true;
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/environments/types/', {
      headers: {
        'Authorization': token
      }
    });
    if (response.data.code === 200) {
      environments.value = response.data.data || [];
    } else {
      message.error(response.data.message || '获取环境列表失败');
    }
  } catch (error) {
    console.error('获取环境列表失败:', error);
    message.error('获取环境列表失败');
  } finally {
    environmentsLoading.value = false;
  }
};

// 表单相关的响应式变量
const modalVisible = ref(false);
const submitting = ref(false);
const formState = reactive({
  role_id: '',
  name: '',
  description: '',
});

const formRules = {
  name: [
    { required: true, message: '请输入角色名称', trigger: 'blur' },
    { min: 2, max: 20, message: '角色名称长度必须在2-20个字符之间', trigger: 'blur' }
  ],
};

// 计算属性
const modalTitle = computed(() => {
  return formState.role_id ? '编辑角色' : '添加角色';
});

// 显示创建模态框
const showCreateModal = () => {
  resetForm();
  modalVisible.value = true;
};

// 显示编辑模态框
const showEditModal = (record) => {
  resetForm();
  formState.role_id = record.role_id;
  formState.name = record.name;
  formState.description = record.description;
  modalVisible.value = true;
};

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields();
  }
  Object.assign(formState, {
    role_id: '',
    name: '',
    description: '',
  });
};

// 提交表单
const handleSubmitForm = () => {
  formRef.value.validate().then(async () => {
    submitting.value = true;
    try {
      const url = '/api/roles/';
      const method = formState.role_id ? 'put' : 'post';

      const token = localStorage.getItem('token');
      const response = await axios({
        method,
        url,
        data: formState,
        headers: {
          'Authorization': token
        }
      });

      if (response.data.code === 200) {
        message.success(formState.role_id ? '更新角色成功' : '创建角色成功');
        modalVisible.value = false;
        fetchRoles();
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

const handleDelete = async (record) => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios({
      method: 'delete',
      url: '/api/roles/',
      data: {
        role_id: record.role_id
      },
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('删除角色成功');
      fetchRoles();
    } else {
      message.error(response.data.message || '删除角色失败');
    }
  } catch (error) {
    console.error('删除角色失败:', error);
    message.error('删除角色失败');
  }
};

// 权限配置相关
const permissionModalVisible = ref(false);
const permissionSubmitting = ref(false);
const currentRoleId = ref('');
const activeTab = ref('menu');
const activeCollapseKeys = ref(['project', 'build_task', 'build_history', 'system_basic']);

// 菜单权限树
const menuTreeData = [
  {
    title: '首页',
    key: '/dashboard',
  },
  {
    title: '项目管理',
    key: '/projects',
    children: [
      {
        title: '项目列表',
        key: '/projects/list',
      },
    ],
  },
  {
    title: '构建与部署',
    key: '/build',
    children: [
      {
        title: '构建任务',
        key: '/build/tasks',
      },
      {
        title: '构建历史',
        key: '/build/history',
      },
    ],
  },
  {
    title: '日志与监控',
    key: '/logs',
    children: [
      {
        title: '登陆日志',
        key: '/logs/login',
      },
    ],
  },
  {
    title: '用户与权限',
    key: '/user',
    children: [
      {
        title: '用户管理',
        key: '/user/list',
      },
      {
        title: '角色管理',
        key: '/user/role',
      },
    ],
  },
  {
    title: '凭证管理',
    key: '/credentials',
  },
  {
    title: '环境配置',
    key: '/environments',
    children: [
      {
        title: '环境列表',
        key: '/environments/list',
      },
    ],
  },

  {
    title: '系统配置',
    key: '/system',
    children: [
      {
        title: '基本设置',
        key: '/system/basic',
      },
    ],
  },
];

// 功能权限模块
const functionModules = [
  {
    key: 'project',
    title: '项目管理',
    permissions: [
      { label: '查看项目', value: 'view' },
      { label: '创建项目', value: 'create' },
      { label: '编辑项目', value: 'edit' },
      { label: '删除项目', value: 'delete' },
    ],
  },
  {
    key: 'build_task',
    title: '构建任务管理',
    permissions: [
      { label: '查看任务', value: 'view' },
      { label: '创建任务', value: 'create' },
      { label: '编辑任务', value: 'edit' },
      { label: '删除任务', value: 'delete' },
      { label: '执行构建', value: 'execute' },
      { label: '查看日志', value: 'view_log' },
      { label: '禁用任务', value: 'disable' },
    ],
  },
  {
    key: 'build_history',
    title: '构建历史管理',
    permissions: [
      { label: '查看构建历史', value: 'view' },
      { label: '查看构建日志', value: 'view_log' },
      { label: '回滚构建版本', value: 'rollback' },
    ],
  },
  {
    key: 'logs_login',
    title: '登录日志管理',
    permissions: [
      { label: '查看登录日志', value: 'view' },
    ],
  },
  {
    key: 'environment',
    title: '环境管理',
    permissions: [
      { label: '查看环境', value: 'view' },
      { label: '创建环境', value: 'create' },
      { label: '编辑环境', value: 'edit' },
      { label: '删除环境', value: 'delete' },
    ],
  },
  {
    key: 'credential',
    title: '凭证管理',
    permissions: [
      { label: '查看凭证', value: 'view' },
      { label: '创建凭证', value: 'create' },
      { label: '编辑凭证', value: 'edit' },
      { label: '删除凭证', value: 'delete' },
    ],
  },
  {
    key: 'user',
    title: '用户管理',
    permissions: [
      { label: '查看用户', value: 'view' },
      { label: '创建用户', value: 'create' },
      { label: '编辑用户', value: 'edit' },
      { label: '删除用户', value: 'delete' },
      { label: '启用/禁用用户', value: 'toggle_status' },
      { label: '重置密码', value: 'reset_password' },
    ],
  },
  {
    key: 'role',
    title: '角色管理',
    permissions: [
      { label: '查看角色', value: 'view' },
      { label: '创建角色', value: 'create' },
      { label: '编辑角色', value: 'edit' },
      { label: '删除角色', value: 'delete' },
      { label: '分配权限', value: 'assign_permission' },
    ],
  },
  {
    key: 'system_basic',
    title: '基本设置管理',
    permissions: [
      { label: '查看基本设置', value: 'view' },
      { label: '编辑安全配置', value: 'edit' },
      { label: '创建通知机器人', value: 'create' },
      { label: '删除通知机器人', value: 'delete' },
      { label: '测试通知机器人', value: 'test' },
    ],
  },
];

// 选中的权限
const menuCheckedKeys = ref(['dashboard', 'project-list']);
const functionCheckedKeys = ref({});
const dataPermissionForm = reactive({
  project_scope: 'all',
  project_ids: [],
  environment_scope: 'all',
  environment_types: [],
  operations: ['view'],
});

// 初始化
onMounted(() => {
  fetchRoles();
  fetchProjects();
  fetchEnvironments();
});

// 重置权限选择
const resetPermissions = () => {
  menuCheckedKeys.value = [];
  functionCheckedKeys.value = {};
  dataPermissionForm.project_scope = 'all';
  dataPermissionForm.project_ids = [];
  dataPermissionForm.environment_scope = 'all';
  dataPermissionForm.environment_types = [];
};

// 显示权限配置模态框
const showPermissionModal = (role) => {
  currentRoleId.value = role.role_id;
  resetPermissions();

  if (role.permissions) {
    try {
      let permissionsObj = role.permissions;
      if (typeof permissionsObj === 'string') {
        try {
          permissionsObj = JSON.parse(permissionsObj);
        } catch (parseErr) {
          console.error('解析权限字符串失败:', parseErr);
          message.error('解析权限数据失败');
          return;
        }
      }

      if (permissionsObj.menu && Array.isArray(permissionsObj.menu)) {
        menuCheckedKeys.value = permissionsObj.menu;
      }

      if (permissionsObj.function && typeof permissionsObj.function === 'object') {
        functionCheckedKeys.value = permissionsObj.function;
      }

      if (permissionsObj.data && typeof permissionsObj.data === 'object') {
        const dataPerms = permissionsObj.data;

        if (dataPerms.project_scope) {
          dataPermissionForm.project_scope = dataPerms.project_scope;
        }

        if (dataPerms.project_ids && Array.isArray(dataPerms.project_ids)) {
          dataPermissionForm.project_ids = dataPerms.project_ids;
        }

        if (dataPerms.environment_scope) {
          dataPermissionForm.environment_scope = dataPerms.environment_scope;
        }

        if (dataPerms.environment_types && Array.isArray(dataPerms.environment_types)) {
          dataPermissionForm.environment_types = dataPerms.environment_types;
        }

        if (dataPerms.operations && Array.isArray(dataPerms.operations)) {
          dataPermissionForm.operations = dataPerms.operations;
        }
      }
    } catch (error) {
      console.error('解析权限数据出错:', error);
      message.error('解析权限数据失败');
    }
  }

  // 加载项目和环境数据
  if (projects.value.length === 0) {
    fetchProjects();
  }
  if (environments.value.length === 0) {
    fetchEnvironments();
  }

  permissionModalVisible.value = true;
};

// 保存权限配置
const savePermissions = async () => {
  permissionSubmitting.value = true;
  try {
    // 构建权限对象
    const permissions = {
      menu: menuCheckedKeys.value,
      function: functionCheckedKeys.value,
      data: {
        project_scope: dataPermissionForm.project_scope,
        project_ids: dataPermissionForm.project_ids,
        environment_scope: dataPermissionForm.environment_scope,
        environment_types: dataPermissionForm.environment_types,
        operations: dataPermissionForm.operations
      }
    };

    const token = localStorage.getItem('token');
    const response = await axios({
      method: 'put',
      url: '/api/roles/',
      data: {
        role_id: currentRoleId.value,
        permissions: permissions
      },
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('权限配置保存成功');
      permissionModalVisible.value = false;
      fetchRoles();
    } else {
      message.error(response.data.message || '保存权限配置失败');
    }
  } catch (error) {
    console.error('保存权限配置失败:', error);
    message.error('保存权限配置失败');
  } finally {
    permissionSubmitting.value = false;
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

:deep(.ant-card) {
  border-radius: 4px;
}

.function-permissions {
  max-width: 800px;
}

:deep(.ant-collapse) {
  border: none;
  background: none;
}

:deep(.ant-collapse-item) {
  border-radius: 4px;
  margin-bottom: 12px;
  border: 1px solid #f0f0f0;
}

:deep(.ant-collapse-header) {
  background: #fafafa;
}

:deep(.ant-checkbox-group) {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  padding: 8px;
}

.data-permissions {
  max-width: 800px;
}

:deep(.ant-radio-group) {
  width: 100%;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

:deep(.ant-form-item) {
  margin-bottom: 24px;
}

.permission-footer {
  margin-top: 24px;
  text-align: right;
  border-top: 1px solid #f0f0f0;
  padding-top: 16px;
}

.empty-message {
  color: #999;
  padding: 8px 0;
  text-align: center;
}
.mt-2 {
  margin-top: 8px;
}
.mt-3 {
  margin-top: 12px;
}
</style>