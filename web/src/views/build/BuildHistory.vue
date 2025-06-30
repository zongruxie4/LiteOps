<template>
  <div class="build-history">
    <div class="page-header">
      <a-row justify="space-between" align="middle">
        <a-col>
          <h2>构建历史</h2>
        </a-col>
        <a-col>
          <a-space>
            <a-select
              v-model:value="projectId"
              style="width: 200px"
              placeholder="选择项目"
              :loading="projectsLoading"
              @change="handleProjectChange"
            >
              <a-select-option value="all">全部项目</a-select-option>
              <a-select-option 
                v-for="project in projects" 
                :key="project.project_id" 
                :value="project.project_id"
              >
                {{ project.name }}
              </a-select-option>
            </a-select>
            <a-select
              v-model:value="environmentId"
              style="width: 200px"
              placeholder="选择环境"
              :loading="environmentsLoading"
              @change="handleEnvironmentChange"
            >
              <a-select-option value="all">全部环境</a-select-option>
              <a-select-option 
                v-for="env in environments" 
                :key="env.environment_id" 
                :value="env.environment_id"
              >
                {{ env.name }}
              </a-select-option>
            </a-select>
            <a-input
              v-model:value="taskName"
              placeholder="搜索任务名称"
              style="width: 200px"
              allow-clear
              @pressEnter="handleSearch"
            >
              <template #prefix>
                <SearchOutlined style="color: rgba(0, 0, 0, 0.25)" />
              </template>
            </a-input>
            <a-button type="primary" :loading="loading" @click="handleSearch">
              <template #icon><SearchOutlined /></template>
              搜索
            </a-button>
          </a-space>
        </a-col>
      </a-row>
    </div>

    <a-card>
      <a-timeline>
        <a-timeline-item
          v-for="record in buildRecords"
          :key="record.id"
          :color="getStatusColor(record.status)"
        >
          <template #dot>
            <CheckCircleOutlined v-if="record.status === 'success'" />
            <CloseCircleOutlined v-if="record.status === 'failed'" />
            <StopOutlined v-if="record.status === 'terminated'" />
            <LoadingOutlined v-if="record.status === 'running' || record.status === 'pending'" />
          </template>
          
          <div class="history-item">
            <div class="history-header">
              <div class="build-info">
                <span class="build-id">构建 #{{ record.build_number }}</span>
                <a-tag :color="getStatusColor(record.status)">
                  {{ getStatusText(record.status) }}
                </a-tag>
                <span class="build-branch">{{ record.branch }}</span>
              </div>
              <div class="build-meta">
                <span>构建时间: {{ record.startTime }}</span>
                <span>总耗时: {{ record.duration }}</span>
              </div>
            </div>

            <div class="history-content">
              <a-descriptions :column="2">
                <a-descriptions-item label="构建任务">
                  <a-space>
                    <span class="build-branch">{{ record.task.name }}</span>
                  </a-space>
                </a-descriptions-item>
                <a-descriptions-item label="Git Commit">
                  <span class="build-branch">{{ record.commit }}</span>
                </a-descriptions-item>
                <a-descriptions-item label="构建版本">
                  <span class="build-branch">{{ record.version }}</span>
                </a-descriptions-item>
                <a-descriptions-item label="构建环境">
                  <span class="build-branch">{{ record.environment }}</span>
                </a-descriptions-item>
                <a-descriptions-item label="构建人">
                  <span class="build-branch">{{ record.operator }}</span>
                </a-descriptions-item>
                <a-descriptions-item label="构建需求">
                  <span class="build-branch">{{ record.requirement }}</span>
                </a-descriptions-item>
              </a-descriptions>

              <div class="stages-info">
                <div class="stages-header">
                  <span class="stages-title">构建阶段</span>
                  <span class="total-duration">
                    总耗时: {{ record.duration }}
                  </span>
                </div>
                <div class="stages-timeline">
                  <a-timeline>
                    <a-timeline-item
                      v-for="stage in record.stages"
                      :key="stage.name"
                      :color="getStatusColor(stage.status)"
                    >
                      <template #dot>
                        <template v-if="stage.status === 'success'">
                          <CheckCircleOutlined />
                        </template>
                        <template v-else-if="stage.status === 'failed'">
                          <CloseCircleOutlined />
                        </template>
                        <template v-else-if="stage.status === 'terminated'">
                          <StopOutlined />
                        </template>
                      </template>
                      <div class="stage-info">
                        <div class="stage-header">
                          <span class="stage-name">{{ stage.name }}</span>
                          <a-tag :color="getStatusColor(stage.status)" :bordered="false">
                            {{ getStageStatusText(stage.status) }}
                          </a-tag>
                        </div>
                        <div class="stage-details">
                          <span class="stage-time">
                            <ClockCircleOutlined /> 开始时间: {{ stage.startTime }}
                          </span>
                          <a-divider type="vertical" />
                          <span class="stage-duration">
                            耗时: {{ stage.duration }}
                          </span>
                          <a-button 
                            type="link" 
                            size="small" 
                            @click="handleViewStageLog(record, stage)"
                          >
                            查看日志
                          </a-button>
                        </div>
                      </div>
                    </a-timeline-item>
                  </a-timeline>
                </div>
              </div>

              <div class="action-buttons">
                <a-space>
                  <a-button type="primary" @click="handleViewLog(record)">
                    查看日志
                  </a-button>
                  <a-button 
                    type="primary" 
                    danger 
                    @click="handleRollback(record)"
                  >
                    回滚到此版本
                  </a-button>
                </a-space>
              </div>
            </div>
          </div>
        </a-timeline-item>
      </a-timeline>

      <!-- 分页器 -->
      <div class="pagination" v-if="total > 0">
        <a-pagination
          v-model:current="page"
          :total="total"
          :pageSize="pageSize"
          show-quick-jumper
          show-size-changer
          :pageSizeOptions="['10', '20', '50', '100']"
          @change="handlePageChange"
          @showSizeChange="handleSizeChange"
        />
      </div>
    </a-card>

    <!-- 日志查看弹窗 -->
    <a-modal
      v-model:open="logModalVisible"
      title="构建日志"
      width="1000px"
      :footer="null"
    >
      <div class="log-content">
        <FullscreenLogViewer 
          :logContent="selectedLog" 
          title="构建日志"
        />
      </div>
    </a-modal>

    <a-modal
      v-model:open="rollbackModalVisible"
      title="确认回滚"
      @ok="confirmRollback"
      :confirmLoading="rollbackLoading"
      okText="确认回滚"
      cancelText="取消"
    >
      <p>确定要回滚 {{ selectedTaskName  }}任务 到版本 {{ selectedVersion }} 吗？</p>
      <p style="color: #ff4d4f;">注意：回滚操作不可逆，请谨慎操作！</p>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { message } from 'ant-design-vue';
import axios from 'axios';
import {
  SearchOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  InfoCircleOutlined,
  DownloadOutlined,
  StopOutlined,
} from '@ant-design/icons-vue';
import FullscreenLogViewer from './components/FullscreenLogViewer.vue';

// 状态变量
const loading = ref(false);
const projectsLoading = ref(false);
const environmentsLoading = ref(false);
const projects = ref([]);
const environments = ref([]);
const projectId = ref('all');
const environmentId = ref('all');
const taskName = ref('');
const buildRecords = ref([]);
const logModalVisible = ref(false);
const selectedLog = ref('');
const rollbackModalVisible = ref(false);
const rollbackLoading = ref(false);
const selectedVersion = ref('');
const selectedTaskName = ref('');
const selectedHistoryId = ref('');
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);

// 获取项目列表
const loadProjects = async () => {
  try {
    projectsLoading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/projects/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      projects.value = response.data.data;
    }
  } catch (error) {
    message.error('加载项目列表失败');
  } finally {
    projectsLoading.value = false;
  }
};

// 获取环境列表
const loadEnvironments = async () => {
  try {
    environmentsLoading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/environments/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      environments.value = response.data.data;
    }
  } catch (error) {
    message.error('加载环境列表失败');
  } finally {
    environmentsLoading.value = false;
  }
};

// 加载构建历史
const loadBuildHistory = async () => {
  try {
    loading.value = true;
    const token = localStorage.getItem('token');
    
    // 构建查询参数
    const params = {
      page: page.value,
      page_size: pageSize.value
    };
    
    if (projectId.value && projectId.value !== 'all') {
      params.project_id = projectId.value;
    }
    
    if (environmentId.value && environmentId.value !== 'all') {
      params.environment_id = environmentId.value;
    }

    if (taskName.value) {
      params.task_name = taskName.value;
    }
    
    const response = await axios.get('/api/build/history/', {
      params,
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      buildRecords.value = response.data.data;
      total.value = response.data.total;
    }
  } catch (error) {
    console.error('Load build history error:', error);
    message.error('加载构建历史失败');
  } finally {
    loading.value = false;
  }
};

// 获取构建日志
const fetchBuildLog = async (historyId) => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get(`/api/build/history/log/${historyId}/`, {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      return response.data.data.log;
    }
    return '获取日志失败';
  } catch (error) {
    return '获取日志失败: ' + error.response.data.message;
  }
};

// 获取阶段日志
const fetchStageLog = async (historyId, stageName) => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get(`/api/build/history/stage-log/${historyId}/${stageName}/`, {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      return response.data.data.log;
    }
    return '获取阶段日志失败';
  } catch (error) {
    return '获取阶段日志失败: ' + error.response.data.message;
  }
};

const executeRollback = async () => {
  try {
    rollbackLoading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/build/history/', {
      history_id: selectedHistoryId.value
    }, {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      message.success('开始回滚');
      rollbackModalVisible.value = false;
    } else {
      throw new Error(response.data.message);
    }
  } catch (error) {
    console.error('Rollback error:', error);
    message.error('回滚失败: ' + error.response.data.message);
  } finally {
    rollbackLoading.value = false;
  }
};

// 事件处理函数
const handleProjectChange = () => {
  page.value = 1;
  loadBuildHistory();
};

const handleEnvironmentChange = () => {
  page.value = 1;
  loadBuildHistory();
};

const handleSearch = () => {
  page.value = 1;
  loadBuildHistory();
};

const handleViewLog = async (record) => {
  selectedHistoryId.value = record.id;
  selectedLog.value = '正在加载日志...';
  logModalVisible.value = true;
  selectedLog.value = await fetchBuildLog(record.id);
};

const handleViewStageLog = async (record, stage) => {
  selectedLog.value = '正在加载日志...';
  logModalVisible.value = true;
  selectedLog.value = await fetchStageLog(record.id, stage.name);
};

const handleRollback = (record) => {
  selectedVersion.value = record.version;
  selectedTaskName.value = record.task.name
  selectedHistoryId.value = record.id;
  rollbackModalVisible.value = true;
};

const confirmRollback = () => {
  executeRollback();
};

const handlePageChange = (current) => {
  page.value = current;
  loadBuildHistory();
};

const handleSizeChange = (current, size) => {
  page.value = 1;
  pageSize.value = size;
  loadBuildHistory();
};

// 处理日志弹窗关闭
const handleLogModalClose = () => {
  logModalVisible.value = false;
  selectedLog.value = '';
  selectedHistoryId.value = '';
};


// 工具函数
const getStatusColor = (status) => {
  const statusMap = {
    'success': 'rgba(135,208,104,0.8)',
    'failed': 'rgba(255,77,79,0.8)',
    'running': 'processing',
    'pending': 'warning',
    'terminated': 'rgba(128, 128, 128, 0.8)' // 灰色
  };
  return statusMap[status] || 'default';
};

const getStatusText = (status) => {
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '构建中',
    'pending': '等待中',
    'terminated': '已终止'
  };
  return statusMap[status] || status;
};

const getStageStatusText = (status) => {
  const statusMap = {
    'success': '成功',
    'failed': '失败',
    'running': '构建中',
    'pending': '等待中',
    'terminated': '已终止'
  };
  return statusMap[status] || status;
};

// 生命周期钩子
onMounted(() => {
  // 检查是否有URL查询参数
  const urlParams = new URLSearchParams(window.location.search);
  const taskIdParam = urlParams.get('task_id');
  const taskNameParam = urlParams.get('task_name');
  
  if (taskNameParam) {
    taskName.value = taskNameParam;
  }
  
  loadProjects();
  loadEnvironments();
  
  // 延迟加载构建历史
  setTimeout(() => {
    loadBuildHistory();
  }, 100);
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

.history-item {
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
  margin: 8px 0;
}

.history-header {
  margin-bottom: 16px;
}

.build-info {
  margin-bottom: 8px;
}

.build-id {
  font-weight: 500;
  margin-right: 8px;
}

.build-branch {
  margin-left: 8px;
  color: #666;
}

.build-meta {
  display: flex;
  gap: 24px;
  color: rgba(0, 0, 0, 0.45);
}

.history-content {
  background: #fff;
  padding: 16px;
  border-radius: 4px;
}

.action-buttons {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.log-content {
  display: flex;
  flex-direction: column;
  height: 650px;
}

.log-body {
  flex: 1;
  overflow-y: auto;
  background: #1e1e1e;
  padding: 16px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
}

.log-body pre {
  margin: 0;
  color: #fff;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.log-footer {
  padding: 12px;
  background: #f5f5f5;
  border-top: 1px solid #e8e8e8;
}

.log-controls {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.stages-info {
  margin: 16px 0;
  padding: 16px;
  background: #fafafa;
  border-radius: 4px;
}

.stages-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.stages-title {
  font-size: 14px;
  font-weight: 500;
}

.total-duration {
  color: rgba(0, 0, 0, 0.45);
}

.stages-timeline {
  background: #fff;
  padding: 16px;
  border-radius: 4px;
}

.stage-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stage-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stage-name {
  font-weight: 500;
  font-size: 14px;
}

.stage-details {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 13px;
}

:deep(.ant-timeline-item-content) {
  margin-left: 28px;
}

:deep(.ant-timeline-item) {
  padding-bottom: 20px;
}

:deep(.ant-timeline-item-last) {
  padding-bottom: 0;
}

.pagination {
  margin-top: 24px;
  text-align: right;
}
</style> 