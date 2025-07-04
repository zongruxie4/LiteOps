import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '../components/layout/MainLayout.vue';
import axios from 'axios';
import { permissionStore, initUserPermissions, hasMenuPermission, hasAnySubMenuPermission } from '../utils/permission';
import { message } from 'ant-design-vue';

// 添加axios响应拦截器
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 401) {
      // 清除登录信息
      localStorage.removeItem('token');
      localStorage.removeItem('user_info');
      // 跳转到登录页
      router.push('/login');
    }
    return Promise.reject(error);
  }
);

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('../views/login/LoginView.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('../views/dashboard/Dashboard.vue'),
        meta: { title: '首页', permission: '/dashboard' }
      },
      // 项目管理
      {
        path: 'projects',
        name: 'projects',
        meta: { title: '项目管理', permission: '/projects' },
        redirect: '/projects/list',
        children: [
          {
            path: 'list',
            name: 'project-list',
            component: () => import('../views/projects/ProjectList.vue'),
            meta: { title: '项目列表', permission: '/projects/list' }
          },
          {
            path: 'detail',
            name: 'project-detail',
            component: () => import('../views/projects/ProjectDetail.vue'),
            meta: { title: '项目详情', permission: '/projects/list' }
          }
        ]
      },
      // 构建与部署
      {
        path: 'build',
        name: 'build',
        meta: { title: '构建与部署', permission: '/build' },
        redirect: '/build/tasks',
        children: [
          {
            path: 'tasks',
            name: 'build-tasks',
            component: () => import('../views/build/BuildTasks.vue'),
            meta: { title: '构建任务', permission: '/build/tasks' }
          },
          {
            path: 'tasks/detail',
            name: 'build-task-detail',
            component: () => import('../views/build/BuildTaskDetail.vue'),
            meta: { title: '任务详情', permission: '/build/tasks' }
          },
          {
            path: 'tasks/create',
            name: 'build-task-create',
            component: () => import('../views/build/BuildTaskEdit.vue'),
            meta: { title: '新建构建任务', permission: '/build/tasks' }
          },
          {
            path: 'tasks/edit',
            name: 'build-task-edit',
            component: () => import('../views/build/BuildTaskEdit.vue'),
            meta: { title: '编辑构建任务', permission: '/build/tasks' }
          },
          {
            path: 'tasks/copy',
            name: 'build-task-copy',
            component: () => import('../views/build/BuildTaskEdit.vue'),
            meta: { title: '复制构建任务', permission: '/build/tasks' }
          },
          {
            path: 'history',
            name: 'build-history',
            component: () => import('../views/build/BuildHistory.vue'),
            meta: { title: '构建历史', permission: '/build/history' }
          }
        ]
      },
      // 日志与监控
      {
        path: 'logs',
        name: 'logs',
        meta: { title: '日志与监控', permission: '/logs' },
        redirect: '/logs/login',
        children: [
          {
            path: 'login',
            name: 'login-logs',
            component: () => import('../views/logs/LoginLogs.vue'),
            meta: { title: '登陆日志', permission: '/logs/login' }
          },
          {
            path: 'login/detail',
            name: 'login-log-detail',
            component: () => import('../views/logs/LoginLogDetail.vue'),
            meta: { title: '登录日志详情', permission: '/logs/login' }
          }
        ]
      },
      // 用户与权限
      {
        path: 'user',
        name: 'user',
        meta: { title: '用户与权限', permission: '/user' },
        redirect: '/user/list',
        children: [
          {
            path: 'list',
            name: 'user-list',
            component: () => import('../views/user/UserList.vue'),
            meta: { title: '用户管理', permission: '/user/list' }
          },
          {
            path: 'role',
            name: 'user-role',
            component: () => import('../views/user/UserRole.vue'),
            meta: { title: '角色管理', permission: '/user/role' }
          }
        ]
      },
      // 凭证管理
      {
        path: 'credentials',
        name: 'credentials',
        component: () => import('../views/credentials/CredentialsList.vue'),
        meta: { title: '凭证管理', permission: '/credentials' }
      },
      // 环境配置
      {
        path: 'environments',
        name: 'environments',
        meta: { title: '环境配置', permission: '/environments' },
        redirect: '/environments/list',
        children: [
          {
            path: 'list',
            name: 'environment-list',
            component: () => import('../views/environments/EnvironmentList.vue'),
            meta: { title: '环境列表', permission: '/environments/list' }
          },
          {
            path: 'detail',
            name: 'environment-detail',
            component: () => import('../views/environments/EnvironmentDetail.vue'),
            meta: { title: '环境详情', permission: '/environments/list' }
          }
        ]
      },
      // 系统配置
      {
        path: 'system',
        name: 'system',
        meta: { title: '系统配置', permission: '/system' },
        redirect: '/system/basic',
        children: [
          {
            path: 'basic',
            name: 'system-basic',
            component: () => import('../views/system/BasicSettings.vue'),
            meta: { title: '基本设置', permission: '/system/basic' }
          }
        ]
      },

    ]
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 权限初始化标志
let permissionInitialized = false;

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 如果是登录页，直接通过
  if (to.path === '/login') {
    return next();
  }

  // 检查是否已登录
  const token = localStorage.getItem('token');
  if (!token) {
    return next('/login');
  }

  // 初始化权限
  if (!permissionInitialized && !permissionStore.initialized) {
    permissionInitialized = true;
    const success = await initUserPermissions();

    // 如果权限初始化失败，跳转到登录页
    if (!success) {
      console.error('权限初始化失败，重定向到登录页');
      localStorage.removeItem('token');
      localStorage.removeItem('user_info');
      return next('/login');
    }
  }

  // 检查菜单权限
  if (to.meta && to.meta.permission) {
    const permissionPath = to.meta.permission;
    const pathParts = permissionPath.split('/');
    const isSubMenu = pathParts.length > 2;

    // 如果是子菜单，同时检查直接权限和父菜单的子权限
    const hasPermission = isSubMenu ?
      (hasMenuPermission(permissionPath) || hasAnySubMenuPermission(permissionPath)) :
      hasMenuPermission(permissionPath);

    if (!hasPermission) {
      console.warn(`用户无权访问路由: ${to.path}, 所需权限: ${to.meta.permission}`);
      message.error(`你没有访问${to.meta.title || '该页面'}的权限`);
      return next('/dashboard');
    }
  }

  next();
});

export default router;