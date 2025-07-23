<template>
  <div class="basic-settings">
    <div class="page-header">
      <h2>基本设置</h2>
    </div>

    <a-tabs v-model:activeKey="activeTabKey"  @change="handleTabChange">
      <!-- 安全设置 -->
      <a-tab-pane key="security-config" tab="设置">
        <a-card>
          <a-form
            ref="securityFormRef"
            :model="securityConfig"
            :rules="securityRules"
            layout="vertical"
          >
            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="密码最小长度" name="min_password_length">
                  <a-input-number 
                    v-model:value="securityConfig.min_password_length" 
                    :min="1"
                    :max="20"
                    style="width: 100%"
                    placeholder="请输入密码最小长度"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="密码复杂度要求" name="password_complexity">
                  <a-checkbox-group v-model:value="securityConfig.password_complexity">
                    <a-checkbox value="uppercase">包含大写字母</a-checkbox>
                    <a-checkbox value="lowercase">包含小写字母</a-checkbox>
                    <a-checkbox value="number">包含数字</a-checkbox>
                    <a-checkbox value="special">包含特殊字符</a-checkbox>
                  </a-checkbox-group>
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="会话超时时间(分钟)" name="session_timeout">
                  <a-input-number 
                    v-model:value="securityConfig.session_timeout" 
                    :min="1"
                    :max="1440"
                    style="width: 100%"
                    placeholder="请输入会话超时时间"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="登录失败锁定次数" name="max_login_attempts">
                  <a-input-number 
                    v-model:value="securityConfig.max_login_attempts" 
                    :min="1"
                    :max="10"
                    style="width: 100%"
                    placeholder="请输入登录失败锁定次数"
                  />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item label="账户锁定时间(分钟)" name="lockout_duration">
                  <a-input-number 
                    v-model:value="securityConfig.lockout_duration" 
                    :min="1"
                    :max="60"
                    style="width: 100%"
                    placeholder="请输入账户锁定时间"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="启用双因子认证" name="enable_2fa">
                  <a-switch v-model:checked="securityConfig.enable_2fa" />
                </a-form-item>
              </a-col>
            </a-row>

            <a-form-item>
              <a-button
                type="primary"
                @click="saveSecurityConfig"
                :loading="securityLoading"
                v-if="hasFunctionPermission('system_basic', 'edit')"
              >
                保存配置
              </a-button>
            </a-form-item>
          </a-form>

          <a-divider>水印配置</a-divider>

          <!-- 水印功能 -->
          <a-form layout="vertical" v-if="hasFunctionPermission('system_basic', 'edit')">
            <a-row :gutter="24">
              <a-col :span="8">
                <a-form-item label="启用水印">
                  <a-switch
                    v-model:checked="securityConfig.watermark_enabled"
                    checked-children="开启"
                    un-checked-children="关闭"
                  />
                  <div class="form-item-help">
                    开启后将在页面显示水印
                  </div>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="显示时间">
                  <a-switch
                    v-model:checked="securityConfig.watermark_show_time"
                    checked-children="显示"
                    un-checked-children="隐藏"
                    :disabled="!securityConfig.watermark_enabled"
                  />
                  <div class="form-item-help">
                    在水印中显示当天日期
                  </div>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="显示用户名">
                  <a-switch
                    v-model:checked="securityConfig.watermark_show_username"
                    checked-children="显示"
                    un-checked-children="隐藏"
                    :disabled="!securityConfig.watermark_enabled"
                  />
                  <div class="form-item-help">
                    在水印中显示当前用户名
                  </div>
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24">
              <a-col :span="24">
                <a-form-item label="自定义水印内容">
                  <a-textarea
                    v-model:value="securityConfig.watermark_content"
                    placeholder="请输入水印内容，支持多行"
                    :rows="4"
                    :maxLength="500"
                    show-count
                    :disabled="!securityConfig.watermark_enabled"
                  />
                  <div class="form-item-help">
                    支持多行文本，每行一个水印。时间和用户名水印会自动添加到自定义内容中
                  </div>
                </a-form-item>
              </a-col>
            </a-row>
          </a-form>

          <a-divider>日志清理</a-divider>

          <!-- 日志清理功能 -->
          <a-form layout="vertical" v-if="hasFunctionPermission('system_basic', 'edit')">
            <a-row :gutter="24">
              <a-col :span="8">
                <a-form-item label="日志类型">
                  <a-select
                    v-model:value="logCleanupForm.logType"
                    placeholder="请选择日志类型"
                    style="width: 100%"
                    @change="handleLogTypeChange"
                  >
                    <a-select-option value="build">构建日志</a-select-option>
                    <a-select-option value="login">登录日志</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="保留天数">
                  <a-input-number
                    v-model:value="logCleanupForm.daysBefore"
                    :min="1"
                    :max="365"
                    style="width: 100%"
                    placeholder="请输入保留天数"
                    addon-after="天"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="8">
                <a-form-item label="操作">
                  <a-button
                    type="primary"
                    danger
                    @click="handleLogCleanup"
                    :loading="logCleanupLoading"
                    :disabled="!logCleanupForm.logType || !logCleanupForm.daysBefore"
                    style="width: 100%"
                  >
                    清理日志
                  </a-button>
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24" v-if="logCleanupForm.logType === 'build'">
              <a-col :span="24">
                <a-form-item label="选择构建任务">
                  <a-select
                    v-model:value="logCleanupForm.selectedTasks"
                    mode="multiple"
                    placeholder="请选择要清理日志的构建任务，不选择则清理所有任务"
                    style="width: 100%"
                    :loading="buildTasksLoading"
                    show-search
                    :filter-option="filterBuildTasks"
                    allow-clear
                  >
                    <a-select-option
                      v-for="task in buildTasksList"
                      :key="task.task_id"
                      :value="task.task_id"
                    >
                      {{ task.name }} ({{ task.project_name }})
                    </a-select-option>
                  </a-select>
                  <div class="form-item-help">
                    将删除{{ logCleanupForm.selectedTasks.length > 0 ? '选定任务' : '所有任务' }}中超过{{ logCleanupForm.daysBefore || 0 }}天的构建日志
                  </div>
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24" v-if="logCleanupForm.logType === 'login'">
              <a-col :span="24">
                <a-alert
                  message="登录日志清理说明"
                  :description="`将删除超过${logCleanupForm.daysBefore || 0}天的所有登录日志记录，包括成功和失败的登录记录。`"
                  type="info"
                  show-icon
                  style="margin-bottom: 16px"
                />
              </a-col>
            </a-row>
          </a-form>
        </a-card>
      </a-tab-pane>

      <!-- 通知配置 -->
      <a-tab-pane key="notification-config" tab="通知">
        <a-card>
          <div class="notification-header">
            <a-button type="primary" @click="showAddRobot" v-if="hasFunctionPermission('system_basic', 'create')">
              <template #icon><PlusOutlined /></template>
              添加机器人
            </a-button>
          </div>

          <a-table
            :columns="robotColumns"
            :data-source="robotList"
            :loading="notificationLoading"
            :pagination="false"
            row-key="robot_id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'type'">
                {{ getRobotTypeText(record.type) }}
              </template>
              <template v-else-if="column.key === 'security_type'">
                {{ getSecurityTypeText(record.security_type) }}
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" @click="handleEdit(record)" v-if="hasFunctionPermission('system_basic', 'edit')">
                    编辑
                  </a-button>
                  <a-button type="link" @click="handleTestRobot(record)" v-if="hasFunctionPermission('system_basic', 'test')">
                    测试
                  </a-button>
                  <a-popconfirm
                    title="确定要删除这个机器人吗？"
                    @confirm="handleDeleteRobot(record)"
                    v-if="hasFunctionPermission('system_basic', 'delete')"
                  >
                    <a-button type="link" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-tab-pane>

      <!-- 认证配置 -->
      <a-tab-pane key="auth-config" tab="认证">
        <a-card>
          <a-form
            ref="ldapFormRef"
            :model="ldapConfig"
            :rules="ldapRules"
            layout="vertical"
          >
                          <a-row :gutter="24">
                <a-col :span="24">
                  <a-form-item>
                    <a-switch
                      v-model:checked="ldapConfig.enabled"
                      checked-children="启用"
                      un-checked-children="禁用"
                      @change="handleLdapEnabledChange"
                    />
                    <span style="margin-left: 12px; font-weight: 500;">启用LDAP认证</span>
                  </a-form-item>
                </a-col>
              </a-row>

            <template v-if="ldapConfig.enabled">
              <a-divider>服务器配置</a-divider>
              
              <a-row :gutter="24">
                <a-col :span="12">
                  <a-form-item label="服务器地址" name="server_host">
                    <a-input
                      v-model:value="ldapConfig.server_host"
                      placeholder="例如: ldap.example.com"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="6">
                  <a-form-item label="端口" name="server_port">
                    <a-input-number
                      v-model:value="ldapConfig.server_port"
                      :min="1"
                      :max="65535"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="6">
                  <a-form-item label="使用SSL">
                    <a-switch v-model:checked="ldapConfig.use_ssl" />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="24">
                <a-col :span="24">
                  <a-form-item label="Base DN" name="base_dn">
                    <a-input
                      v-model:value="ldapConfig.base_dn"
                      placeholder="例如: dc=example,dc=com"
                    />
                    <div class="form-item-help">
                      LDAP搜索的起始点，通常是你的域名，如: dc=company,dc=com
                    </div>
                  </a-form-item>
                </a-col>
              </a-row>



              <a-divider>高级配置</a-divider>

              <a-row :gutter="24">
                <a-col :span="12">
                  <a-form-item label="绑定DN" name="bind_dn">
                    <a-input
                      v-model:value="ldapConfig.bind_dn"
                      placeholder="cn=admin,dc=example,dc=com"
                    />
                    <div class="form-item-help">
                      管理员账户DN，用于连接LDAP服务器搜索和认证用户
                    </div>
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="绑定密码" name="bind_password">
                    <a-input-password
                      v-model:value="ldapConfig.bind_password"
                      placeholder="输入新密码或留空保持原密码"
                    />
                    <div class="form-item-help">
                      管理员账户密码
                    </div>
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="24">
                <a-col :span="18">
                  <a-form-item label="用户搜索过滤器">
                    <a-input
                      v-model:value="ldapConfig.user_search_filter"
                      placeholder="例如: (uid={username})"
                    />
                    <div class="form-item-help">
                      用于搜索用户的LDAP过滤器，{username} 将被替换为实际用户名
                    </div>
                  </a-form-item>
                </a-col>
                <a-col :span="6">
                  <a-form-item label="连接超时(秒)">
                    <a-input-number
                      v-model:value="ldapConfig.timeout"
                      :min="1"
                      :max="60"
                      style="width: 100%"
                    />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="24">
                <a-col :span="24">
                  <a-form-item label="属性映射配置" name="user_attr_map">
                    <a-textarea
                      v-model:value="userAttrMapJson"
                      placeholder='示例：
{
  "username": "cn",
  "name": "uid",
  "email": "mail"
}'
                      :rows="6"
                      @blur="handleAttrMapChange"
                    />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-divider>用户同步</a-divider>

              <a-row :gutter="24">
                <a-col :span="16">
                  <a-form-item label="搜索条件">
                    <a-input
                      v-model:value="ldapSyncForm.searchFilter"
                      placeholder="例如: uid=user* 或 mail=搜索email"
                    />
                    <div class="form-item-help">
                      可以指定搜索条件来过滤LDAP用户，留空则搜索所有用户
                    </div>
                  </a-form-item>
                </a-col>
                <a-col :span="8">
                  <a-form-item label="操作">
                    <a-button
                      type="primary"
                      @click="handleSearchLdapUsers"
                      :loading="ldapSyncLoading"
                      style="margin-right: 8px"
                    >
                      搜索用户
                    </a-button>
                    <a-button
                      type="default"
                      @click="handleSyncSelectedUsers"
                      :loading="ldapSyncLoading"
                      :disabled="selectedUsers.length === 0"
                    >
                      同步选中
                    </a-button>
                  </a-form-item>
                </a-col>
              </a-row>

              <!-- 搜索结果 -->
              <div v-if="ldapUsers.length > 0">
                <h4>搜索结果：</h4>
                <a-table
                  :columns="ldapUserColumns"
                  :data-source="ldapUsers"
                  :pagination="{ pageSize: 10 }"
                  :row-selection="{ selectedRowKeys: selectedUsers, onChange: onSelectUsers }"
                  row-key="username"
                  size="small"
                  style="margin-bottom: 16px"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'exists'">
                      <a-tag :color="record.exists ? 'rgba(56, 158, 13, 0.8)' : 'rgba(22,119,255,0.8)'">
                        {{ record.exists ? '已存在' : '新用户' }}
                      </a-tag>
                    </template>
                  </template>
                </a-table>
              </div>

              <!-- 同步结果 -->
              <div v-if="syncResult">
                <a-alert
                  :message="syncResult.success ? '用户同步成功' : '用户同步失败'"
                  :description="syncResult.message"
                  :type="syncResult.success ? 'success' : 'error'"
                  show-icon
                  style="margin-bottom: 16px"
                />
                <div v-if="syncResult.success && syncResult.synced_users">
                  <h4>同步详情：</h4>
                  <ul>
                    <li v-for="user in syncResult.synced_users" :key="user.username">
                      <strong>{{ user.username }}</strong> - {{ user.action === 'created' ? '新建' : '更新' }}
                    </li>
                  </ul>
                </div>
              </div>

              <a-row v-if="ldapTestResult" :gutter="24">
                <a-col :span="24">
                  <a-alert
                    :message="ldapTestResult.success ? 'LDAP连接测试成功' : 'LDAP连接测试失败'"
                    :description="ldapTestResult.message"
                    :type="ldapTestResult.success ? 'success' : 'error'"
                    show-icon
                    style="margin-bottom: 16px"
                  />
                  <div v-if="ldapTestResult.success && ldapTestResult.connection_info">
                    <h4>连接信息：</h4>
                    <a-descriptions size="small" bordered>
                      <a-descriptions-item label="服务器">
                        {{ ldapTestResult.connection_info.server }}
                      </a-descriptions-item>
                      <a-descriptions-item label="绑定DN">
                        {{ ldapTestResult.connection_info.bind_dn }}
                      </a-descriptions-item>
                      <a-descriptions-item label="Base DN">
                        {{ ldapTestResult.connection_info.base_dn }}
                      </a-descriptions-item>
                      <a-descriptions-item label="连接状态">
                        {{ ldapTestResult.connection_info.connection_status }}
                      </a-descriptions-item>
                    </a-descriptions>
                  </div>
                </a-col>
              </a-row>
            </template>

            <a-form-item>
              <a-space>
                <a-button
                  type="primary"
                  @click="saveLdapConfig"
                  :loading="ldapConfigLoading"
                  v-if="hasFunctionPermission('system_basic', 'edit')"
                >
                  保存配置
                </a-button>
                <a-button
                  @click="handleLdapTest"
                  :loading="ldapTestLoading"
                  :disabled="!canTestConnection"
                  v-if="hasFunctionPermission('system_basic', 'edit')"
                >
                  测试连接
                </a-button>
              </a-space>
              <div v-if="!canTestConnection" class="form-item-help" style="margin-top: 8px;">
                请先启用LDAP认证并完成所有必要配置，点击保存配置后再测试连接
              </div>
            </a-form-item>
          </a-form>
        </a-card>
      </a-tab-pane>
    </a-tabs>

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
        ref="robotFormRef"
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
import { ref, reactive, onMounted, computed } from 'vue';
import { message, Modal } from 'ant-design-vue';
import { PlusOutlined } from '@ant-design/icons-vue';
import axios from 'axios';
import { hasFunctionPermission, checkPermission } from '../../utils/permission';

const activeTabKey = ref('security-config');

// LDAP配置
const ldapFormRef = ref();
const ldapConfigLoading = ref(false);
const ldapTestLoading = ref(false);
const ldapTestResult = ref(null);

// 是否可以测试连接
const canTestConnection = computed(() => {
  // 是否启用且所有必要配置都已填写
  const hasPassword = ldapConfig.bind_password && 
                     ldapConfig.bind_password.trim() && 
                     ldapConfig.bind_password !== '';
  
  return ldapConfig.enabled && 
         hasPassword &&
         ldapConfig.server_host &&
         ldapConfig.server_host.trim() &&
         ldapConfig.base_dn &&
         ldapConfig.base_dn.trim() &&
         ldapConfig.bind_dn &&
         ldapConfig.bind_dn.trim();
});

const ldapConfig = reactive({
  enabled: false,
  server_host: '',
  server_port: 389,
  use_ssl: false,
  base_dn: '',
  bind_dn: '',
  bind_password: '',
  user_search_filter: '(cn={username})',
  user_attr_map: {
    username: 'cn',
    name: 'uid',
    email: 'mail'
  },
  timeout: 10
});

// LDAP用户同步相关
const ldapSyncForm = reactive({
  searchFilter: ''
});

const ldapUsers = ref([]);
const selectedUsers = ref([]);
const ldapSyncLoading = ref(false);
const syncResult = ref(null);

// 用户属性映射JSON字符串
const userAttrMapJson = ref('');

// LDAP用户表格列定义
const ldapUserColumns = [
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
    title: '状态',
    dataIndex: 'exists',
    key: 'exists',
  },
];

// 验证JSON格式的自定义验证器
const validateAttrMapJson = (rule, value) => {
  // 使用userAttrMapJson的值进行验证
  const jsonValue = userAttrMapJson.value;
  
  if (!jsonValue || !jsonValue.trim()) {
    return Promise.reject('请输入属性映射配置');
  }
  
  try {
    const parsed = JSON.parse(jsonValue);
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      return Promise.reject('属性映射必须是一个JSON对象');
    }
    
    // 检查是否包含必要的字段
    if (!parsed.username) {
      return Promise.reject('属性映射必须包含 username 字段');
    }
    
    return Promise.resolve();
  } catch (error) {
    return Promise.reject('JSON格式错误，请检查语法');
  }
};

const ldapRules = {
  server_host: [
    { required: true, message: '请输入服务器地址', trigger: 'blur' }
  ],
  base_dn: [
    { required: true, message: '请输入Base DN', trigger: 'blur' }
  ],
  bind_dn: [
    { required: true, message: '请输入绑定DN', trigger: 'blur' }
  ],
  bind_password: [
    { required: true, message: '请输入绑定密码', trigger: 'blur' }
  ],
  user_attr_map: [
    { validator: validateAttrMapJson, trigger: 'blur' }
  ]
};

// 安全配置
const securityFormRef = ref();
const securityConfig = reactive({
  min_password_length: 8,
  password_complexity: ['lowercase', 'number'],
  session_timeout: 120,
  max_login_attempts: 5,
  lockout_duration: 30,
  enable_2fa: false,
  watermark_enabled: false,
  watermark_content: '',
  watermark_show_time: false,
  watermark_show_username: false
});

const securityRules = {
  min_password_length: [
    { required: true, message: '请输入密码最小长度', trigger: 'blur' }
  ],
  session_timeout: [
    { required: true, message: '请输入会话超时时间', trigger: 'blur' }
  ]
};

// 日志清理相关
const buildTasksList = ref([]);
const buildTasksLoading = ref(false);
const logCleanupLoading = ref(false);
const logCleanupForm = reactive({
  logType: 'build',
  selectedTasks: [],
  daysBefore: 30
});

// 通知机器人相关
const drawerVisible = ref(false);
const submitLoading = ref(false);
const notificationLoading = ref(false);
const isEdit = ref(false);
const robotList = ref([]);

// 表格列定义
const robotColumns = [
  {
    title: '类型',
    dataIndex: 'type',
    key: 'type',
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
const robotFormRef = ref();
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

const securityLoading = ref(false);

// 标签页切换
const handleTabChange = (key) => {
  if (key === 'notification-config') {
    loadRobotList();
  } else if (key === 'security-config') {
    loadBuildTasksList();
  } else if (key === 'auth-config') {
    fetchLdapConfig();
  }
};

// 获取安全配置
const fetchSecurityConfig = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/system/security/', {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      Object.assign(securityConfig, response.data.data);
    }
  } catch (error) {
    console.error('获取安全配置失败:', error);
  }
};

// 保存安全配置
const saveSecurityConfig = async () => {
  try {
    await securityFormRef.value.validate();
    securityLoading.value = true;

    const token = localStorage.getItem('token');
    const response = await axios.put('/api/system/security/', securityConfig, {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      message.success('安全配置保存成功');
    } else {
      message.error(response.data.message || '保存失败');
    }
  } catch (error) {
    console.error('保存安全配置失败:', error);
    message.error('保存失败');
  } finally {
    securityLoading.value = false;
  }
};

// 获取机器人列表
const loadRobotList = async () => {
  if (!checkPermission('system_basic', 'view')) {
    return;
  }
  try {
    notificationLoading.value = true;
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
    notificationLoading.value = false;
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
  if (!checkPermission('system_basic', 'create')) {
    return;
  }
  isEdit.value = false;
  drawerVisible.value = true;
};

// 显示编辑机器人抽屉
const handleEdit = (record) => {
  if (!checkPermission('system_basic', 'edit')) {
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
  robotFormRef.value?.resetFields();
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

// 提交表单
const handleSubmit = async () => {
  try {
    await robotFormRef.value.validate();
    submitLoading.value = true;
    
    const token = localStorage.getItem('token');
    const method = isEdit.value ? 'put' : 'post';
    const response = await axios[method]('/api/notification/robots/', robotForm, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      message.success(isEdit.value ? '更新机器人成功' : '添加机器人成功');
      handleDrawerClose();
      loadRobotList();
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
  if (!checkPermission('system_basic', 'test')) {
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
  if (!checkPermission('system_basic', 'delete')) {
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
      loadRobotList();
    } else {
      message.error(response.data.message || '删除失败');
    }
  } catch (error) {
    console.error('Delete robot error:', error);
    message.error('删除失败');
  }
};

// 获取构建任务列表
const loadBuildTasksList = async () => {
  try {
    buildTasksLoading.value = true;
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/system/security/build-tasks/', {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      buildTasksList.value = response.data.data;
    } else {
      message.error(response.data.message || '获取构建任务列表失败');
    }
  } catch (error) {
    console.error('Load build tasks error:', error);
    message.error('获取构建任务列表失败');
  } finally {
    buildTasksLoading.value = false;
  }
};

// 构建任务过滤函数
const filterBuildTasks = (input, option) => {
  return option.children[0].children.toLowerCase().includes(input.toLowerCase());
};

// 日志类型变化处理
const handleLogTypeChange = () => {
  // 切换日志类型清空构建任务选择
  logCleanupForm.selectedTasks = [];
};

// 处理日志清理
const handleLogCleanup = async () => {
  try {
    // 生成确认信息
    let confirmContent = '';
    if (logCleanupForm.logType === 'build') {
      const taskCount = logCleanupForm.selectedTasks.length;
      if (taskCount > 0) {
        confirmContent = `确定要清理选定的${taskCount}个构建任务中${logCleanupForm.daysBefore}天前的构建日志吗？`;
      } else {
        confirmContent = `确定要清理所有构建任务中${logCleanupForm.daysBefore}天前的构建日志吗？`;
      }
    } else if (logCleanupForm.logType === 'login') {
      confirmContent = `确定要清理${logCleanupForm.daysBefore}天前的所有登录日志吗？`;
    }
    confirmContent += '此操作不可恢复。';

    // 确认对话框
    const confirmed = await new Promise((resolve) => {
      Modal.confirm({
        title: '确认清理日志',
        content: confirmContent,
        okText: '确定清理',
        okType: 'danger',
        cancelText: '取消',
        onOk: () => resolve(true),
        onCancel: () => resolve(false)
      });
    });

    if (!confirmed) return;

    logCleanupLoading.value = true;
    const token = localStorage.getItem('token');

    // 根据日志类型调用不同的API
    let apiUrl = '';
    let requestData = {};

    if (logCleanupForm.logType === 'build') {
      apiUrl = '/api/system/security/cleanup-build-logs/';
      requestData = {
        task_ids: logCleanupForm.selectedTasks,
        days_before: logCleanupForm.daysBefore
      };
    } else if (logCleanupForm.logType === 'login') {
      apiUrl = '/api/system/security/cleanup-login-logs/';
      requestData = {
        days_before: logCleanupForm.daysBefore
      };
    }

    const response = await axios.post(apiUrl, requestData, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      message.success(response.data.message);
      if (logCleanupForm.logType === 'build') {
        logCleanupForm.selectedTasks = [];
      }
    } else {
      message.error(response.data.message || '日志清理失败');
    }
  } catch (error) {
    console.error('Cleanup logs error:', error);
    message.error('日志清理失败');
  } finally {
    logCleanupLoading.value = false;
  }
};

// LDAP配置相关方法
const fetchLdapConfig = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/system/ldap/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      const configData = response.data.data;
      Object.assign(ldapConfig, configData);
      
      if (configData.bind_password === '******') {
        ldapConfig.bind_password = '******';  // 保持标识，表示后端有密码
      }
      
      // 初始化属性映射JSON字符串
      initUserAttrMapJson();
    } else {
      message.error(response.data.message || '获取LDAP配置失败');
    }
  } catch (error) {
    console.error('获取LDAP配置失败:', error);
    message.error('获取LDAP配置失败');
  }
};

const saveLdapConfig = async () => {
  try {
    await ldapFormRef.value?.validate();
    
    // 验证属性映射JSON格式
    try {
      if (userAttrMapJson.value.trim()) {
        const parsedMap = JSON.parse(userAttrMapJson.value);
        ldapConfig.user_attr_map = parsedMap;
      }
    } catch (error) {
      message.error('属性映射JSON格式错误，请检查语法');
      return;
    }
    
    ldapConfigLoading.value = true;
    
    // 准备发送的数据
    const configToSave = { ...ldapConfig };
    
    if (configToSave.bind_password === '******') {
      delete configToSave.bind_password;
    }
    
    const token = localStorage.getItem('token');
    const response = await axios.put('/api/system/ldap/', configToSave, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      message.success('LDAP配置保存成功');
      // 重新获取配置保状态同步
      await fetchLdapConfig();
    } else {
      message.error(response.data.message || '保存失败');
    }
  } catch (error) {
    console.error('保存LDAP配置失败:', error);
    message.error('保存失败');
  } finally {
    ldapConfigLoading.value = false;
  }
};

// LDAP启用状态变化
const handleLdapEnabledChange = (enabled) => {
  if (!enabled) {
    // 禁用LDAP时清除所有配置
    ldapConfig.server_host = '';
    ldapConfig.server_port = 389;
    ldapConfig.use_ssl = false;
    ldapConfig.base_dn = '';
    ldapConfig.bind_dn = '';
    ldapConfig.bind_password = '';
    ldapConfig.user_search_filter = '(cn={username})';
    ldapConfig.user_attr_map = { username: 'cn', name: 'uid', email: 'mail' };
    ldapConfig.timeout = 10;
    
    // 重置属性映射JSON字符串
    initUserAttrMapJson();
    
    // 清除测试结果
    ldapTestResult.value = null;
    syncResult.value = null;
    ldapUsers.value = [];
    selectedUsers.value = [];
  }
};

// 处理属性映射JSON变化
const handleAttrMapChange = () => {
  try {
    if (userAttrMapJson.value.trim()) {
      const parsedMap = JSON.parse(userAttrMapJson.value);
      ldapConfig.user_attr_map = parsedMap;
    }
  } catch (error) {
    message.error('JSON格式错误，请检查语法');
  }
};

// 初始化属性映射JSON字符串
const initUserAttrMapJson = () => {
  if (ldapConfig.user_attr_map && Object.keys(ldapConfig.user_attr_map).length > 0) {
    userAttrMapJson.value = JSON.stringify(ldapConfig.user_attr_map, null, 2);
  } else {
    // 提供默认的映射配置
    const defaultMapping = {
      username: 'cn',
      name: 'uid', 
      email: 'mail'
    };
    userAttrMapJson.value = JSON.stringify(defaultMapping, null, 2);
    ldapConfig.user_attr_map = defaultMapping;
  }
};

const handleLdapTest = async () => {
  try {
    ldapTestLoading.value = true;
    ldapTestResult.value = null;
    
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/system/ldap/test/', {}, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      ldapTestResult.value = {
        success: true,
        message: response.data.message,
        connection_info: response.data.data
      };
    } else {
      ldapTestResult.value = {
        success: false,
        message: response.data.message
      };
    }
  } catch (error) {
    console.error('LDAP测试失败:', error);
    ldapTestResult.value = {
      success: false,
      message: '测试失败，请稍后重试'
    };
  } finally {
    ldapTestLoading.value = false;
  }
};

// 搜索LDAP用户
const handleSearchLdapUsers = async () => {
  try {
    ldapSyncLoading.value = true;
    syncResult.value = null;
    
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/system/ldap/sync/', {
      action: 'search',
      search_filter: ldapSyncForm.searchFilter
    }, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      // 检查用户是否已存在
      const existingUsers = await getExistingUsers();
      ldapUsers.value = response.data.data.users.map(user => ({
        ...user,
        exists: existingUsers.includes(user.username)
      }));
      selectedUsers.value = [];
      message.success(`找到${ldapUsers.value.length}个LDAP用户`);
    } else {
      message.error(response.data.message || '搜索用户失败');
    }
  } catch (error) {
    console.error('搜索LDAP用户失败:', error);
    message.error('搜索用户失败');
  } finally {
    ldapSyncLoading.value = false;
  }
};

// 获取已存在的用户列表
const getExistingUsers = async () => {
  try {
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/users/', {
      headers: { 'Authorization': token }
    });
    
    if (response.data.code === 200) {
      return response.data.data
        .filter(user => user.user_type === 'ldap')
        .map(user => user.username);
    }
    return [];
  } catch (error) {
    console.error('获取已存在用户失败:', error);
    return [];
  }
};

// 选择用户
const onSelectUsers = (selectedRowKeys) => {
  selectedUsers.value = selectedRowKeys;
};

// 同步选中用户
const handleSyncSelectedUsers = async () => {
  if (selectedUsers.value.length === 0) {
    message.warning('请选择要同步的用户');
    return;
  }

  try {
    ldapSyncLoading.value = true;
    syncResult.value = null;
    
    const usersToSync = ldapUsers.value.filter(user => 
      selectedUsers.value.includes(user.username)
    );
    
    const token = localStorage.getItem('token');
    const response = await axios.post('/api/system/ldap/sync/', {
      action: 'sync',
      users: usersToSync
    }, {
      headers: { 'Authorization': token }
    });

    if (response.data.code === 200) {
      syncResult.value = {
        success: true,
        message: response.data.message,
        synced_users: response.data.data.synced_users
      };
      
      // 刷新用户列表
      await handleSearchLdapUsers();
    } else {
      syncResult.value = {
        success: false,
        message: response.data.message
      };
    }
  } catch (error) {
    console.error('同步用户失败:', error);
    syncResult.value = {
      success: false,
      message: '同步用户失败，请稍后重试'
    };
  } finally {
    ldapSyncLoading.value = false;
  }
};

onMounted(() => {
  fetchSecurityConfig();
  loadBuildTasksList();
  if (!userAttrMapJson.value) {
    initUserAttrMapJson();
  }
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

:deep(.ant-tabs-content-holder) {
  padding: 0;
}

:deep(.ant-form-item-explain-error) {
  font-size: 12px;
}

:deep(.ant-checkbox-group) {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-header {
  margin-bottom: 16px;
  text-align: right;
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

:deep(.ant-input) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

:deep(textarea) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
</style> 