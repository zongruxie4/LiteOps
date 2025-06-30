<template>
  <div class="notification">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>通知配置</h2>
        </a-col>
        <a-col>
          <a-button type="primary" @click="showAddRobot">
            <template #icon><PlusOutlined /></template>
            添加机器人
          </a-button>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <a-table
        :columns="robotColumns"
        :data-source="robotList"
        :loading="loading"
        :pagination="false"
        row-key="robot_id"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" @click="handleEdit(record)">
                编辑
              </a-button>
              <a-button type="link" @click="handleTestRobot(record)">
                测试
              </a-button>
              <a-popconfirm
                title="确定要删除这个机器人吗？"
                @confirm="handleDeleteRobot(record)"
              >
                <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 添加/编辑机器人抽屉 -->
    <a-drawer
      v-model:open="drawerVisible"
      :title="isEdit ? '编辑机器人' : '添加机器人'"
      placement="right"
      width="500px"
      :closable="false"
      :footer="null"
      @close="handleDrawerClose"
    >
      <a-form
        ref="formRef"
        :model="robotForm"
        layout="vertical"
      >
        <a-form-item
          label="机器人类型"
          name="type"
          :rules="[{ required: true, message: '请选择机器人类型' }]"
        >
          <a-select
            v-model:value="robotForm.type"
            placeholder="请选择机器人类型"
            :disabled="isEdit"
          >
            <a-select-option value="dingtalk">钉钉机器人</a-select-option>
            <a-select-option value="wecom">企业微信机器人</a-select-option>
            <a-select-option value="feishu">飞书机器人</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item
          label="机器人名称"
          name="name"
          :rules="[{ required: true, message: '请输入机器人名称' }]"
        >
          <a-input
            v-model:value="robotForm.name"
            placeholder="请输入机器人名称"
            :maxLength="50"
          />
        </a-form-item>

        <a-form-item
          label="Webhook地址"
          name="webhook"
          :rules="[{ required: true, message: '请输入Webhook地址' }]"
        >
          <a-input
            v-model:value="robotForm.webhook"
            placeholder="请输入Webhook地址"
          />
        </a-form-item>

        <a-form-item
          label="安全设置"
          name="security_type"
          :rules="[{ required: true, message: '请选择安全设置类型' }]"
        >
          <a-select
            v-model:value="robotForm.security_type"
            placeholder="请选择安全设置类型"
          >
            <a-select-option value="none">无</a-select-option>
            <a-select-option value="secret">加签密钥</a-select-option>
            <a-select-option value="keyword">自定义关键词</a-select-option>
            <a-select-option value="ip">IP地址(段)</a-select-option>
          </a-select>
        </a-form-item>

        <template v-if="robotForm.security_type === 'secret'">
          <a-form-item
            label="加签密钥"
            name="secret"
            :rules="[{ required: true, message: '请输入加签密钥' }]"
          >
            <a-input
              v-model:value="robotForm.secret"
              placeholder="请输入加签密钥"
            />
          </a-form-item>
        </template>

        <template v-if="robotForm.security_type === 'keyword'">
          <a-form-item
            label="自定义关键词"
            name="keywords"
            :rules="[{ required: true, message: '请添加关键词' }]"
          >
            <a-select
              v-model:value="robotForm.keywords"
              mode="tags"
              placeholder="请输入关键词后按回车添加"
              :token-separators="[',']"
            />
          </a-form-item>
        </template>

        <template v-if="robotForm.security_type === 'ip'">
          <a-form-item
            label="IP白名单"
            name="ip_list"
            :rules="[{ required: true, message: '请添加IP地址' }]"
          >
            <a-select
              v-model:value="robotForm.ip_list"
              mode="tags"
              placeholder="请输入IP地址后按回车添加"
              :token-separators="[',']"
            />
            <div class="form-item-help">
              支持IP地址或IP地址段，例如: 192.168.1.1 或 192.168.1.1/24
            </div>
          </a-form-item>
        </template>

        <a-form-item
          label="备注"
          name="remark"
        >
          <a-textarea
            v-model:value="robotForm.remark"
            placeholder="请输入备注信息"
            :rows="4"
            :maxLength="200"
          />
        </a-form-item>
      </a-form>

      <template #footer>
        <div style="text-align: left">
          <a-space>
            <a-button @click="handleDrawerClose">取消</a-button>
            <a-button type="primary" :loading="submitLoading" @click="handleSubmit">
              确定
            </a-button>
          </a-space>
        </div>
      </template>
    </a-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { checkPermission, hasFunctionPermission } from '../../utils/permission';

const drawerVisible = ref(false);
const submitLoading = ref(false);
const loading = ref(false);
const isEdit = ref(false);

const robotList = ref([]);

// 表格列定义
const robotColumns = [
  {
    title: '类型',
    dataIndex: 'type',
    key: 'type',
    customRender: ({ text }) => getRobotTypeText(text)
  },
  {
    title: '机器人名称',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: 'Webhook地址',
    dataIndex: 'webhook',
    key: 'webhook',
    ellipsis: true,
  },
  {
    title: '安全设置',
    dataIndex: 'security_type',
    key: 'security_type',
    customRender: ({ text }) => getSecurityTypeText(text)
  },
  {
    title: '备注',
    dataIndex: 'remark',
    key: 'remark',
    ellipsis: true,
  },
  {
    title: '创建时间',
    dataIndex: 'create_time',
    key: 'create_time',
  },
  {
    title: '操作',
    key: 'action',
    fixed: 'right',
  },
];

// 添加/编辑机器人表单
const formRef = ref();
const robotForm = reactive({
  robot_id: '',
  type: undefined,
  name: '',
  webhook: '',
  security_type: 'none',
  secret: '',
  keywords: [],
  ip_list: [],
  remark: '',
});

// 获取机器人列表
const loadRobotList = async () => {
  if (!checkPermission('notification', 'view')) {
    return;
  }
  try {
    loading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/notification/robots/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      robotList.value = response.data.data;
    } else {
      message.error(response.data.message || '获取机器人列表失败');
    }
  } catch (error) {
    console.error('Load robot list error:', error);
    message.error('获取机器人列表失败');
  } finally {
    loading.value = false;
  }
};

// 获取机器人类型文本
const getRobotTypeText = (type) => {
  const types = {
    dingtalk: '钉钉',
    wecom: '企业微信',
    feishu: '飞书',
  };
  return types[type] || type;
};

// 获取安全设置类型文本
const getSecurityTypeText = (type) => {
  const types = {
    none: '无',
    secret: '加签密钥',
    keyword: '关键词',
    ip: 'IP白名单',
  };
  return types[type] || type;
};

// 显示添加机器人抽屉
const showAddRobot = () => {
  if (!checkPermission('notification', 'create')) {
    return;
  }
  isEdit.value = false;
  drawerVisible.value = true;
};

// 显示编辑机器人抽屉
const handleEdit = (record) => {
  if (!checkPermission('notification', 'edit')) {
    return;
  }
  isEdit.value = true;
  Object.assign(robotForm, {
    robot_id: record.robot_id,
    type: record.type,
    name: record.name,
    webhook: record.webhook,
    security_type: record.security_type,
    secret: record.secret,
    keywords: record.keywords || [],
    ip_list: record.ip_list || [],
    remark: record.remark,
  });
  drawerVisible.value = true;
};

const handleDrawerClose = () => {
  drawerVisible.value = false;
  formRef.value?.resetFields();
  // 重置表单
  Object.assign(robotForm, {
    robot_id: '',
    type: undefined,
    name: '',
    webhook: '',
    security_type: 'none',
    secret: '',
    keywords: [],
    ip_list: [],
    remark: '',
  });
};

const handleSubmit = async () => {
  try {
    await formRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const method = isEdit.value ? 'put' : 'post';
    const response = await axios[method]('/api/notification/robots/', robotForm, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      message.success(isEdit.value ? '更新机器人成功' : '添加机器人成功');
      handleDrawerClose();
      loadRobotList();  // 重新加载列表
    } else {
      message.error(response.data.message || (isEdit.value ? '更新机器人失败' : '添加机器人失败'));
    }
  } catch (error) {
    console.error(isEdit.value ? 'Update robot error:' : 'Add robot error:', error);
    message.error(isEdit.value ? '更新机器人失败' : '添加机器人失败');
  } finally {
    submitLoading.value = false;
  }
};

// 测试机器人
const handleTestRobot = async (robot) => {
  // 测试权限
  if (!checkPermission('notification', 'test')) {
    return;
  }
  try {
    const token = localStorage.getItem('token');
    const hide = message.loading('正在发送测试消息...', 0);
    
    const response = await axios.post('/api/notification/robots/test/', {
      robot_id: robot.robot_id
    }, {
      headers: { 'Authorization': token }
    });

    hide();
    
    if (response.data.code === 200) {
      message.success('测试消息发送成功');
    } else {
      message.error(response.data.message || '发送测试消息失败');
    }
  } catch (error) {
    console.error('Test robot error:', error);
    message.error('发送测试消息失败');
  }
};

// 删除机器人
const handleDeleteRobot = async (robot) => {
  // 删除权限
  if (!checkPermission('notification', 'delete')) {
    return;
  }
  try {
    const token = localStorage.getItem('token');
    const response = await axios.delete('/api/notification/robots/', {
      headers: { 'Authorization': token },
      data: { robot_id: robot.robot_id }
    });

    if (response.data.code === 200) {
      message.success('删除成功');
      loadRobotList();  // 重新加载列表
    } else {
      message.error(response.data.message || '删除失败');
    }
  } catch (error) {
    console.error('Delete robot error:', error);
    message.error('删除失败');
  }
};

// 页面加载时获取机器人列表
onMounted(() => {
  loadRobotList();
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

:deep(.ant-drawer-header) {
  padding: 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.ant-drawer-body) {
  padding: 24px;
}

:deep(.ant-drawer-footer) {
  border-top: 1px solid #f0f0f0;
  padding: 10px 16px;
}

:deep(.ant-table-thead > tr > th) {
  background: #fafafa;
}

.form-item-help {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
  margin-top: 4px;
}
</style> 