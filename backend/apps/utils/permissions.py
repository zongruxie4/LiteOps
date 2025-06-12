import json
import logging
from ..models import User, UserRole

logger = logging.getLogger('apps')

def get_user_permissions(user_id):
    """
    获取用户的权限信息
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 用户权限信息，包含菜单权限、功能权限和数据权限
    """
    try:
        # 获取用户信息
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            logger.error(f'获取用户权限时用户不存在: {user_id}')
            return {
                'menu': [],
                'function': {},
                'data': {
                    'project_scope': 'all',
                    'project_ids': [],
                    'environment_scope': 'all',
                    'environment_types': []
                }
            }
        
        # 获取用户的所有角色
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        # 合并所有角色的权限
        menu_permissions = set()
        function_permissions = {}
        data_permissions = {
            'project_scope': 'all',
            'project_ids': [],
            'environment_scope': 'all',
            'environment_types': []
        }
        
        has_custom_project_scope = False
        has_custom_environment_scope = False
        
        for user_role in user_roles:
            role = user_role.role
            permissions = role.permissions
            
            # 如果permissions是字符串，解析为JSON
            if isinstance(permissions, str):
                try:
                    permissions = json.loads(permissions)
                except:
                    permissions = {}
            
            # 合并菜单权限
            if permissions.get('menu'):
                menu_permissions.update(permissions['menu'])
            
            # 合并功能权限
            if permissions.get('function'):
                for module, actions in permissions['function'].items():
                    if module not in function_permissions:
                        function_permissions[module] = []
                    function_permissions[module].extend(actions)
                    # 确保不重复
                    function_permissions[module] = list(set(function_permissions[module]))
            
            # 合并数据权限
            if permissions.get('data'):
                data_perms = permissions['data']
                
                # 项目权限
                if data_perms.get('project_scope') == 'custom':
                    has_custom_project_scope = True
                    if data_permissions['project_scope'] == 'all':
                        data_permissions['project_scope'] = 'custom'
                        data_permissions['project_ids'] = data_perms.get('project_ids', [])
                    else:
                        # 合并项目ID列表
                        data_permissions['project_ids'].extend(data_perms.get('project_ids', []))
                        # 确保不重复
                        data_permissions['project_ids'] = list(set(data_permissions['project_ids']))
                
                # 环境权限
                if data_perms.get('environment_scope') == 'custom':
                    has_custom_environment_scope = True
                    if data_permissions['environment_scope'] == 'all':
                        data_permissions['environment_scope'] = 'custom'
                        data_permissions['environment_types'] = data_perms.get('environment_types', [])
                    else:
                        # 合并环境类型列表
                        data_permissions['environment_types'].extend(data_perms.get('environment_types', []))
                        # 确保不重复
                        data_permissions['environment_types'] = list(set(data_permissions['environment_types']))
        
        # 如果没有任何角色有自定义项目/环境范围，保持为'all'
        if not has_custom_project_scope:
            data_permissions['project_scope'] = 'all'
            data_permissions['project_ids'] = []
        
        if not has_custom_environment_scope:
            data_permissions['environment_scope'] = 'all'
            data_permissions['environment_types'] = []
        
        return {
            'menu': list(menu_permissions),
            'function': function_permissions,
            'data': data_permissions
        }
    except Exception as e:
        logger.error(f'获取用户权限失败: {str(e)}', exc_info=True)
        # 返回默认的空权限
        return {
            'menu': [],
            'function': {},
            'data': {
                'project_scope': 'all',
                'project_ids': [],
                'environment_scope': 'all',
                'environment_types': []
            }
        } 