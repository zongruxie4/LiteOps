import axios from 'axios';
import { ref, reactive } from 'vue';
import { message } from 'ant-design-vue';

// 权限数据存储
export const permissionStore = reactive({
  initialized: false,
  menuPermissions: [],
  functionPermissions: {},
  dataPermissions: {
    project_scope: 'all',
    project_ids: [],
    environment_scope: 'all',
    environment_types: []
  }
});

// 初始化用户权限
export const initUserPermissions = async () => {
  try {
    // 从本地存储获取用户信息
    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');

    if (!userInfo.user_id) {
      console.error('用户信息不存在，权限初始化失败');
      return false;
    }

    // 获取用户的角色权限
    const token = localStorage.getItem('token');
    const response = await axios.get('/api/user/permissions', {
      headers: {
        'Authorization': token
      }
    });

    if (response.data.code === 200) {
      const permissions = response.data.data;

      // 存储权限信息
      permissionStore.menuPermissions = permissions.menu || [];
      permissionStore.functionPermissions = permissions.function || {};
      permissionStore.dataPermissions = permissions.data || {
        project_scope: 'all',
        project_ids: [],
        environment_scope: 'all',
        environment_types: []
      };

      permissionStore.initialized = true;

      return true;
    } else {
      console.error('获取用户权限失败:', response.data.message);
      return false;
    }
  } catch (error) {
    console.error('初始化用户权限失败:', error);
    return false;
  }
};

// 检查菜单权限
export const hasMenuPermission = (menuPath) => {
  if (!permissionStore.initialized) {
    console.warn('权限尚未初始化，拒绝所有菜单权限', menuPath);
    return false;
  }

  const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
  if (userInfo.is_admin) {
    console.log(`用户是管理员，自动拥有菜单权限: ${menuPath}`);
    return true;
  }

  const hasPermission = permissionStore.menuPermissions.includes(menuPath);
  return hasPermission;
};

// 检查是否有子菜单权限
export const hasAnySubMenuPermission = (parentPath) => {
  if (!permissionStore.initialized) {
    return false;
  }

  // 管理员拥有所有权限
  const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
  if (userInfo.is_admin) {
    return true;
  }

  // 检查是否直接拥有父菜单权限
  if (permissionStore.menuPermissions.includes(parentPath)) {
    return true;
  }

  // 检查是否拥有任何以父菜单路径开头的子菜单权限
  return permissionStore.menuPermissions.some(permission =>
    permission !== parentPath && permission.startsWith(`${parentPath}/`)
  );
};

// 检查功能权限
export const hasFunctionPermission = (module, action) => {
  if (!permissionStore.initialized) {
    return false;
  }

  const modulePermissions = permissionStore.functionPermissions[module] || [];
  return modulePermissions.includes(action);
};

// 检查项目数据权限
export const hasProjectPermission = (projectId) => {
  if (!permissionStore.initialized) {
    return false;
  }

  // 如果有所有项目的权限
  if (permissionStore.dataPermissions.project_scope === 'all') {
    return true;
  }

  return permissionStore.dataPermissions.project_ids.includes(projectId);
};

// 检查环境数据权限
export const hasEnvironmentPermission = (environmentType) => {
  if (!permissionStore.initialized) {
    return false;
  }

  // 如果有所有环境的权限
  if (permissionStore.dataPermissions.environment_scope === 'all') {
    return true;
  }

  return permissionStore.dataPermissions.environment_types.includes(environmentType);
};

export const getPermittedProjectIds = () => {
  if (!permissionStore.initialized) {
    return [];
  }

  if (permissionStore.dataPermissions.project_scope === 'all') {
    return null;
  }

  return permissionStore.dataPermissions.project_ids || [];
};

// 获取有权限的环境类型
export const getPermittedEnvironmentTypes = () => {
  if (!permissionStore.initialized) {
    return [];
  }

  if (permissionStore.dataPermissions.environment_scope === 'all') {
    return null;
  }

  return permissionStore.dataPermissions.environment_types || [];
};

// 统一的权限错误提示
export const showPermissionError = (module, action) => {
  let errorMsg = '你没有权限执行此操作';

  if (module && action) {
    const actionText = {
      'view': '查看',
      'create': '创建',
      'edit': '编辑',
      'delete': '删除',
      'execute': '执行',
      'deploy': '部署',
      'rollback': '回滚',
      'approve': '审批',
      'test': '测试',
      'view_log': '查看日志',
      'disable': '禁用/启用',
    }[action] || action;

    const moduleText = {
      'project': '项目',
      'build': '构建任务',
      'build_task': '构建任务',
      'build_history': '构建历史',
      'environment': '环境',
      'credential': '凭证',
      'user': '用户',
      'role': '角色',
      'notification': '通知'
    }[module] || module;

    errorMsg = `你没有${moduleText}${actionText}权限`;
  }

  message.error(errorMsg);
  return false;
};

// 检查功能权限和数据权限
export const checkPermission = (module, action, entityId = null, entityType = 'project') => {
  if (!hasFunctionPermission(module, action)) {
    showPermissionError(module, action);
    return false;
  }

  if (entityId) {
    if (entityType === 'project' && !hasProjectPermission(entityId)) {
      message.error('你没有该项目的访问权限');
      return false;
    } else if (entityType === 'environment' && !hasEnvironmentPermission(entityId)) {
      message.error('你没有该环境的访问权限');
      return false;
    }
  }

  return true;
};