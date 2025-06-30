<template>
  <div class="system-variables">
    <a-button type="link" @click="visible = true">
      <template #icon><InfoCircleOutlined /></template>
      查看可用系统变量
    </a-button>

    <a-modal
      v-model:open="visible"
      title="系统环境变量列表"
      width="800px"
      :footer="null"
    >
      <a-alert
        message="这些变量可以在构建脚本中直接使用"
        description="在脚本中使用变量的格式：$VARIABLE_NAME 或 ${VARIABLE_NAME}"
        type="info"
        show-icon
        style="margin-bottom: 16px"
      />
      
      <a-input-search
        v-model:value="searchText"
        placeholder="搜索变量..."
        style="margin-bottom: 16px"
        enter-button
        @search="onSearch"
      />

      <a-table
        :columns="columns"
        :data-source="filteredVariables"
        :pagination="false"
        :loading="loading"
      >
        <template #bodyCell="{ column, text }">
          <template v-if="column.key === 'name'">
            <code>{{ text }}</code>
          </template>
          <template v-else-if="column.key === 'description'">
            <span>{{ text }}</span>
          </template>
        </template>
      </a-table>
      
      <div class="modal-footer">
        <a-button type="primary" @click="visible = false">关闭</a-button>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { InfoCircleOutlined } from '@ant-design/icons-vue';

const visible = ref(false);
const loading = ref(false);
const searchText = ref('');

// 表格列定义
const columns = [
  {
    title: '变量名',
    dataIndex: 'name',
    key: 'name',
    width: 200,
  },
  {
    title: '说明',
    dataIndex: 'description',
    key: 'description',
  },
];

// 系统变量列表
const systemVariables = [
  // 编号相关变量
  {
    name: 'BUILD_NUMBER',
    description: '当前构建的序号',
    category: '编号'
  },
  {
    name: 'VERSION',
    description: '当前构建的版本号（格式为: 年月日时分秒_CommitID前8位，如20250320112507_029e149e）',
    category: '编号'
  },
  
  // Git相关变量
  {
    name: 'COMMIT_ID',
    description: 'Git提交ID',
    category: 'Git'
  },
  {
    name: 'BRANCH',
    description: '构建分支名称',
    category: 'Git'
  },
  
  // 项目相关变量
  {
    name: 'PROJECT_NAME',
    description: '项目名称',
    category: '项目'
  },
  {
    name: 'PROJECT_ID',
    description: '项目ID',
    category: '项目'
  },
  {
    name: 'PROJECT_REPO',
    description: '项目Git仓库地址',
    category: '项目'
  },
  
  // 任务相关变量
  {
    name: 'TASK_NAME',
    description: '构建任务名称',
    category: '任务'
  },
  {
    name: 'TASK_ID',
    description: '构建任务ID',
    category: '任务'
  },
  
  // 环境相关变量
  {
    name: 'ENVIRONMENT',
    description: '构建环境名称',
    category: '环境'
  },
  {
    name: 'ENVIRONMENT_TYPE',
    description: '构建环境类型',
    category: '环境'
  },
  {
    name: 'ENVIRONMENT_ID',
    description: '构建环境ID',
    category: '环境'
  },
  
  // 构建路径相关变量
  {
    name: 'BUILD_PATH',
    description: '构建目录的绝对路径',
    category: '路径'
  },
  {
    name: 'BUILD_WORKSPACE',
    description: '构建工作区的绝对路径（等同于BUILD_PATH）',
    category: '路径'
  },
  
  {
    name: 'service_name',
    description: '任务名称（TASK_NAME的别名）',
    category: '别名'
  },
  {
    name: 'build_env',
    description: '构建环境名称（ENVIRONMENT的别名）',
    category: '别名'
  },
  {
    name: 'branch',
    description: '分支名称（BRANCH的别名）',
    category: '别名'
  },
  {
    name: 'version',
    description: '版本号（VERSION的别名）',
    category: '别名'
  },
];

// 根据搜索文本过滤变量
const filteredVariables = computed(() => {
  if (!searchText.value) {
    return systemVariables;
  }
  
  const search = searchText.value.toLowerCase();
  return systemVariables.filter(variable => 
    variable.name.toLowerCase().includes(search) || 
    variable.description.toLowerCase().includes(search) ||
    variable.category.toLowerCase().includes(search)
  );
});

// 搜索处理
const onSearch = () => {
};

onMounted(() => {
});
</script>

<style scoped>
.system-variables {
  margin: 12px 0;
}

.modal-footer {
  margin-top: 24px;
  text-align: right;
}

:deep(.ant-table-thead > tr > th) {
  background-color: #fafafa;
  font-weight: 500;
}

code {
  padding: 2px 6px;
  background-color: #f5f5f5;
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
  font-size: 13px;
}
</style> 