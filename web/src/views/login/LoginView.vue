<template>
  <div class="login-container">
    <div class="login-box">
      <div class="login-title">
        <img src="../../assets/image/liteops.png" alt="LiteOps Logo" class="login-logo" />
      </div>
      <a-form
        :model="formState"
        name="loginForm"
        @finish="handleSubmit"
        :rules="rules"
      >
        <a-form-item name="username">
          <a-input
            v-model:value="formState.username"
            size="large"
            placeholder="请输入用户名"
            :class="{ 'input-active': inputFocus.username }"
            @focus="inputFocus.username = true"
            @blur="inputFocus.username = false"
          >
            <template #prefix>
              <UserOutlined :class="{ 'icon-active': inputFocus.username }" />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item name="password">
          <a-input-password
            v-model:value="formState.password"
            size="large"
            placeholder="请输入密码"
            :class="{ 'input-active': inputFocus.password }"
            @focus="inputFocus.password = true"
            @blur="inputFocus.password = false"
          >
            <template #prefix>
              <LockOutlined :class="{ 'icon-active': inputFocus.password }" />
            </template>
          </a-input-password>
        </a-form-item>
        
        <!-- LDAP认证选项 -->
        <a-form-item v-if="ldapEnabled">
          <div class="auth-type-selection">
            <a-switch
              v-model:checked="useLDAP"
              checked-children="LDAP"
              un-checked-children="系统"
              @change="handleAuthTypeChange"
            />
            <span class="auth-type-label">
              {{ useLDAP ? 'LDAP认证' : '系统认证' }}
            </span>
          </div>
        </a-form-item>
        
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            :loading="loading"
            block
            class="login-button"
            :disabled="!formState.username || !formState.password"
          >
            <span class="button-text">登 录</span>
          </a-button>
        </a-form-item>
      </a-form>
      <div class="footer-text">
        <p>© 2024 LiteOps 胡图图不涂涂</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import { useRouter } from 'vue-router';
import axios from 'axios';
import { initUserPermissions } from '../../utils/permission';

const router = useRouter();
const loading = ref(false);
const useLDAP = ref(false);
const ldapEnabled = ref(false);

const formState = reactive({
  username: '',
  password: '',
});

const inputFocus = reactive({
  username: false,
  password: false
});

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
};

const handleAuthTypeChange = (checked) => {
  console.log('认证类型变更:', checked ? 'LDAP' : '系统');
};

// 检查LDAP是否启用
const checkLdapStatus = async () => {
  try {
    const response = await axios.get('/api/system/ldap/status/');
    if (response.data.code === 200) {
      ldapEnabled.value = response.data.data.enabled;
    }
  } catch (error) {
    console.error('检查LDAP状态失败:', error);
    ldapEnabled.value = false;
  }
};

const handleSubmit = async (values) => {
  try {
    loading.value = true;
    const response = await axios.post('/api/login/', {
      username: values.username,
      password: values.password,
      auth_type: useLDAP.value ? 'ldap' : 'system'
    });

    if (response.data.code === 200) {
      const { token, user } = response.data.data;

      localStorage.setItem('token', token);
      localStorage.setItem('user_info', JSON.stringify(user));

      await initUserPermissions();

      message.success('登录成功');
      router.push('/dashboard');
    } else {
      message.error(response.data.message || '登录失败');
    }
  } catch (error) {
    message.error('登录失败，请稍后重试');
    console.error('Login error:', error);
  } finally {
    loading.value = false;
  }
};

// 组件挂载时检查LDAP状态
onMounted(() => {
  checkLdapStatus();
});
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: linear-gradient(to bottom right, #f8fafc, #e6f7ff);
  position: relative;
  overflow: hidden;
}

.login-box {
  width: 450px;
  padding: 60px 50px;
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
  position: relative;
  z-index: 2;
  border: 1px solid rgba(230, 230, 230, 0.5);
  overflow: hidden;
  transition: all 0.3s ease;
}

.login-title {
  text-align: center;
  margin-bottom: 40px;
}

.login-logo {
  height: 100px;
  margin-bottom: 10px;
  transition: all 0.3s ease;
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.15));
}

.auth-type-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 10px;
}

.auth-type-label {
  color: rgba(0, 0, 0, 0.65);
  font-size: 14px;
  font-weight: 500;
}

:deep(.ant-switch-checked) {
  background-color: #1890ff;
}

:deep(.ant-input-affix-wrapper) {
  height: 55px;
  border-radius: 12px;
  border: 2px solid #eaeaea;
  transition: all 0.3s ease;
  margin-bottom: 20px;
  overflow: hidden;
  background: #f9fafc;
}

:deep(.ant-input) {
  font-size: 16px;
  background: #f9fafc;
  transition: all 0.3s ease;
}

:deep(.ant-input-affix-wrapper.input-active) {
  border-color: #1890ff;
  box-shadow: 0 0 0 4px rgba(24, 144, 255, 0.15);
  background: white;
}

:deep(.ant-form-item) {
  margin-bottom: 25px;
}

.login-button {
  height: 55px;
  border-radius: 12px;
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 2px;
  margin-top: 20px;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  overflow: hidden;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border: none;
  box-shadow: 0 8px 15px rgba(24, 144, 255, 0.3);
  position: relative;
}

.login-button:active {
  transform: translateY(-1px);
  box-shadow: 0 5px 10px rgba(24, 144, 255, 0.4);
}

.button-text {
  position: relative;
  z-index: 2;
}

.login-button::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 5px;
  height: 5px;
  background: rgba(255, 255, 255, 0.5);
  opacity: 0;
  border-radius: 100%;
  transform: scale(1, 1) translate(-50%, -50%);
  transform-origin: 50% 50%;
}

.login-button:focus:not(:active)::after {
  animation: ripple 0.8s ease-out;
}

@keyframes ripple {
  0% {
    transform: scale(0, 0);
    opacity: 0.5;
  }
  100% {
    transform: scale(30, 30);
    opacity: 0;
  }
}

:deep(.ant-input-affix-wrapper:hover),
:deep(.ant-input-affix-wrapper:focus),
:deep(.ant-input-affix-wrapper-focused) {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.15);
  background: white;
}

:deep(.anticon) {
  color: #bfbfbf;
  transition: all 0.5s cubic-bezier(0.68, -0.55, 0.27, 1.55);
  font-size: 20px;
}

:deep(.icon-active) {
  color: #1890ff !important;
  transform: scale(1.2);
}

:deep(.ant-input-affix-wrapper:hover .anticon),
:deep(.ant-input-affix-wrapper-focused .anticon) {
  color: #1890ff;
}

.footer-text {
  text-align: center;
  margin-top: 30px;
  color: #8c8c8c;
  font-size: 14px;
  opacity: 0.8;
}
</style>