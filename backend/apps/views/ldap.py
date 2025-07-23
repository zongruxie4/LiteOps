import json
import uuid
import hashlib
import logging
import ldap3
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from ..models import User, LDAPConfig
from ..utils.auth import jwt_auth_required
from ..utils.crypto import CryptoUtils

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

class LDAPError(Exception):
    """LDAP相关异常"""
    pass

class APIResponse:
    """统一的API响应处理"""
    @staticmethod
    def success(message, data=None):
        return JsonResponse({'code': 200, 'message': message, 'data': data})
    
    @staticmethod
    def error(code, message):
        return JsonResponse({'code': code, 'message': message})

@method_decorator(csrf_exempt, name='dispatch')
class LDAPConfigView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取LDAP配置"""
        try:
            config = self._get_or_create_config()
            return APIResponse.success('获取LDAP配置成功', self._serialize_config(config))
        except Exception as e:
            logger.error(f'获取LDAP配置失败: {str(e)}', exc_info=True)
            return APIResponse.error(500, f'服务器错误: {str(e)}')

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """更新LDAP配置"""
        try:
            with transaction.atomic():
                data = json.loads(request.body)
                config = self._get_or_create_config()
                self._update_config(config, data)
                config.save()
                return APIResponse.success('更新LDAP配置成功')
        except Exception as e:
            logger.error(f'更新LDAP配置失败: {str(e)}', exc_info=True)
            return APIResponse.error(500, f'服务器错误: {str(e)}')

    def _get_or_create_config(self):
        """获取或创建LDAP配置"""
        config, created = LDAPConfig.objects.get_or_create(
            defaults={
                'enabled': False,
                'server_host': '',
                'server_port': 389,
                'use_ssl': False,
                'base_dn': '',
                'bind_dn': '',
                'bind_password': '',
                'user_search_filter': '(cn={username})',
                'user_attr_map': {'username': 'cn', 'name': 'uid', 'email': 'mail'},
                'timeout': 10
            }
        )
        return config

    def _serialize_config(self, config):
        """序列化配置，隐藏敏感信息"""
        return {
            'enabled': config.enabled,
            'server_host': config.server_host,
            'server_port': config.server_port,
            'use_ssl': config.use_ssl,
            'base_dn': config.base_dn,
            'bind_dn': config.bind_dn,
            'bind_password': '******' if config.bind_password else '',  # 隐藏密码或显示为空
            'user_search_filter': config.user_search_filter,
            'user_attr_map': config.user_attr_map,
            'timeout': config.timeout,
            'update_time': config.update_time.strftime('%Y-%m-%d %H:%M:%S') if config.update_time else None
        }

    def _update_config(self, config, data):
        """更新配置字段"""
        update_fields = [
            'enabled', 'server_host', 'server_port', 'use_ssl', 'base_dn',
            'bind_dn', 'user_search_filter', 'user_attr_map', 'timeout'
        ]
        
        # 检查是否禁用LDAP认证
        if 'enabled' in data and not data['enabled']:
            # 如果禁用LDAP，清除所有配置数据
            config.enabled = False
            config.server_host = ''
            config.server_port = 389
            config.use_ssl = False
            config.base_dn = ''
            config.bind_dn = ''
            config.bind_password = ''
            config.user_search_filter = '(cn={username})'
            config.user_attr_map = {'username': 'cn', 'name': 'uid', 'email': 'mail'}
            config.timeout = 10
        else:
            # 启用状态下正常更新字段
            for field in update_fields:
                if field in data:
                    setattr(config, field, data[field])
            
            if 'bind_password' in data:
                if data['bind_password']:
                    config.bind_password = CryptoUtils.encrypt_password(data['bind_password'])

@method_decorator(csrf_exempt, name='dispatch')
class LDAPTestView(View):
    @method_decorator(jwt_auth_required)
    def post(self, request):
        """测试LDAP管理员账户连接"""
        try:
            config = self._get_config()
            
            if not all([config.bind_dn, config.bind_password]):
                return APIResponse.error(400, '绑定DN和绑定密码是必需的')
                
            result = self._test_admin_connection(config)
            return APIResponse.success('LDAP服务器连接测试成功', result)
            
        except LDAPError as e:
            return APIResponse.error(400, str(e))
        except Exception as e:
            logger.error(f'LDAP测试失败: {str(e)}', exc_info=True)
            return APIResponse.error(500, f'服务器错误: {str(e)}')

    def _get_config(self):
        """获取LDAP配置"""
        try:
            config = LDAPConfig.objects.get()
        except LDAPConfig.DoesNotExist:
            raise LDAPError('LDAP配置不存在，请先配置LDAP服务器')
        
        if not all([config.server_host, config.base_dn, config.bind_dn]):
            raise LDAPError('LDAP配置不完整，请检查服务器地址、Base DN和绑定DN')
        
        return config

    def _test_admin_connection(self, config):
        """测试LDAP管理员账户连接"""
        try:
            server_uri = f"{'ldaps://' if config.use_ssl else 'ldap://'}{config.server_host}:{config.server_port}"
            server = ldap3.Server(server_uri, use_ssl=config.use_ssl, connect_timeout=config.timeout)
            
            logger.info(f"LDAP测试 - 服务器: {server_uri}")
            logger.info(f"LDAP测试 - 绑定DN: {config.bind_dn}")
            logger.info(f"LDAP测试 - Base DN: {config.base_dn}")
            
            # 解密绑定密码
            bind_password = CryptoUtils.decrypt_password(config.bind_password)
            
            # 使用管理员账户连接
            connection = ldap3.Connection(
                server, 
                user=config.bind_dn, 
                password=bind_password, 
                auto_bind=True
            )
            
            # 测试基本搜索功能
            connection.search(
                search_base=config.base_dn,
                search_filter='(objectClass=*)',
                search_scope=ldap3.BASE,
                attributes=['*']
            )
            
            connection.unbind()
            
            return {
                'server': server_uri,
                'bind_dn': config.bind_dn,
                'base_dn': config.base_dn,
                'connection_status': '连接成功'
            }

        except ldap3.core.exceptions.LDAPBindError as e:
            logger.error(f"LDAP绑定错误: {str(e)}")
            if 'invalidCredentials' in str(e):
                raise LDAPError('管理员账户认证失败，请检查绑定DN和密码')
            elif 'invalidDNSyntax' in str(e):
                raise LDAPError('绑定DN格式错误，请检查DN语法是否正确')
            else:
                raise LDAPError(f'绑定失败: {str(e)}')
        except ldap3.core.exceptions.LDAPSocketOpenError as e:
            logger.error(f"LDAP连接错误: {str(e)}")
            raise LDAPError('LDAP服务器连接失败，请检查服务器地址和端口')
        except ldap3.core.exceptions.LDAPSocketReceiveError as e:
            logger.error(f"LDAP超时错误: {str(e)}")
            raise LDAPError('LDAP服务器连接超时，请检查网络连接')
        except ldap3.core.exceptions.LDAPException as e:
            logger.error(f"LDAP通用错误: {str(e)}")
            raise LDAPError(f'LDAP错误: {str(e)}')
        except Exception as e:
            logger.error(f"LDAP测试未知错误: {str(e)}", exc_info=True)
            raise LDAPError(f'连接失败: {str(e)}')



@method_decorator(csrf_exempt, name='dispatch')
class LDAPSyncView(View):
    """LDAP用户同步视图"""
    
    @method_decorator(jwt_auth_required)
    def post(self, request):
        """同步LDAP用户到系统"""
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            config = self._get_config()
            
            if action == 'search':
                # 搜索LDAP用户
                search_filter = data.get('search_filter', '')
                users = self._search_ldap_users(config, search_filter)
                return APIResponse.success('搜索LDAP用户成功', {'users': users})
                
            elif action == 'sync':
                # 同步用户到系统
                users_data = data.get('users', [])
                if not users_data:
                    return APIResponse.error(400, '请选择要同步的用户')
                
                synced_users = self._sync_users_to_system(config, users_data)
                return APIResponse.success(
                    f'成功同步{len(synced_users)}个用户',
                    {'synced_users': synced_users}
                )
            
            else:
                return APIResponse.error(400, '无效的操作类型')
                
        except LDAPError as e:
            return APIResponse.error(400, str(e))
        except Exception as e:
            logger.error(f'LDAP用户同步失败: {str(e)}', exc_info=True)
            return APIResponse.error(500, f'服务器错误: {str(e)}')

    def _get_config(self):
        """获取LDAP配置"""
        try:
            config = LDAPConfig.objects.get()
            if not config.enabled:
                raise LDAPError('LDAP未启用')
        except LDAPConfig.DoesNotExist:
            raise LDAPError('LDAP配置不存在')

        if not all([config.server_host, config.base_dn, config.bind_dn, config.bind_password]):
            raise LDAPError('LDAP配置不完整')
        
        return config

    def _search_ldap_users(self, config, search_filter=''):
        """搜索LDAP用户"""
        try:
            server_uri = f"{'ldaps://' if config.use_ssl else 'ldap://'}{config.server_host}:{config.server_port}"
            server = ldap3.Server(server_uri, use_ssl=config.use_ssl, connect_timeout=config.timeout)
            
            # 解密绑定密码
            bind_password = CryptoUtils.decrypt_password(config.bind_password)
            
            # 使用管理员账户连接
            connection = ldap3.Connection(
                server, 
                user=config.bind_dn, 
                password=bind_password, 
                auto_bind=True
            )
            
            # 构建搜索过滤器
            if search_filter:
                final_filter = f"(&(objectClass=person)({search_filter}))"
            else:
                final_filter = "(objectClass=person)"
            
            # 搜索用户
            connection.search(
                search_base=config.base_dn,
                search_filter=final_filter,
                attributes=list(config.user_attr_map.values())
            )
            
            users = []
            for entry in connection.entries:
                user_info = self._extract_user_info(entry, config.user_attr_map)
                if user_info.get('username'):  # 确保有用户名
                    users.append(user_info)
            
            connection.unbind()
            return users
            
        except ldap3.core.exceptions.LDAPException as e:
            logger.error(f"LDAP搜索用户错误: {str(e)}")
            raise LDAPError(f'搜索用户失败: {str(e)}')
        except Exception as e:
            logger.error(f"搜索LDAP用户未知错误: {str(e)}", exc_info=True)
            raise LDAPError(f'搜索失败: {str(e)}')

    def _extract_user_info(self, entry, attr_map):
        """提取用户信息"""
        user_info = {'dn': entry.entry_dn}
        for local_attr, ldap_attr in attr_map.items():
            if hasattr(entry, ldap_attr):
                attr_value = getattr(entry, ldap_attr)
                if attr_value:
                    user_info[local_attr] = str(attr_value.value) if hasattr(attr_value, 'value') else str(attr_value)
        return user_info

    def _sync_users_to_system(self, config, users_data):
        """同步用户到系统"""
        synced_users = []
        
        for user_data in users_data:
            try:
                with transaction.atomic():
                    username = user_data.get('username')
                    if not username:
                        continue
                    
                    # 检查用户是否已存在
                    try:
                        user = User.objects.get(username=username)
                        if user.user_type != 'ldap':
                            logger.warning(f'用户{username}已存在但不是LDAP用户，跳过')
                            continue
                        
                        # 更新用户信息
                        user.name = user_data.get('name', username)
                        user.email = user_data.get('email')
                        user.ldap_dn = user_data.get('dn')
                        user.save()
                        
                        synced_users.append({
                            'username': username,
                            'action': 'updated'
                        })
                        
                    except User.DoesNotExist:
                        # 创建新用户
                        user = User.objects.create(
                            user_id=generate_id(),
                            username=username,
                            name=user_data.get('name', username),
                            email=user_data.get('email'),
                            user_type='ldap',
                            ldap_dn=user_data.get('dn'),
                            status=1
                        )
                        
                        synced_users.append({
                            'username': username,
                            'action': 'created'
                        })
                        
            except Exception as e:
                logger.error(f'同步用户{user_data.get("username")}失败: {str(e)}')
                continue
        
        return synced_users

@method_decorator(csrf_exempt, name='dispatch')
class LDAPStatusView(View):
    def get(self, request):
        """检查LDAP是否启用（无需认证）"""
        try:
            try:
                config = LDAPConfig.objects.get()
                enabled = config.enabled
            except LDAPConfig.DoesNotExist:
                enabled = False
            
            return APIResponse.success('获取LDAP状态成功', {'enabled': enabled})
        except Exception as e:
            logger.error(f'获取LDAP状态失败: {str(e)}', exc_info=True)
            return APIResponse.error(500, f'服务器错误: {str(e)}')

class LDAPAuthenticator:
    """LDAP认证器"""

    @staticmethod
    def authenticate(username, password):
        """LDAP用户认证 - 只认证已存在的用户"""
        try:
            config = LDAPAuthenticator._validate_config()
            # 先检查用户是否存在于本地数据库
            user = LDAPAuthenticator._get_existing_user(username)
            # 进行LDAP认证
            LDAPAuthenticator._ldap_authenticate(config, username, password)
            return True, user
        except LDAPError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f'LDAP认证失败: {str(e)}', exc_info=True)
            return False, f'认证失败: {str(e)}'

    @staticmethod
    def _validate_config():
        """验证LDAP配置"""
        try:
            config = LDAPConfig.objects.get()
            if not config.enabled:
                raise LDAPError('未启用LDAP认证')
        except LDAPConfig.DoesNotExist:
            raise LDAPError('LDAP配置不存在')

        if not all([config.server_host, config.base_dn, config.bind_dn, config.bind_password]):
            raise LDAPError('LDAP配置不完整，缺少必要的服务器信息或管理员账户')
        
        return config

    @staticmethod
    def _ldap_authenticate(config, username, password):
        """执行LDAP认证 - 只使用绑定DN模式"""
        try:
            server_uri = f"{'ldaps://' if config.use_ssl else 'ldap://'}{config.server_host}:{config.server_port}"
            server = ldap3.Server(server_uri, use_ssl=config.use_ssl, connect_timeout=config.timeout)

            # 解密绑定密码
            bind_password = CryptoUtils.decrypt_password(config.bind_password)
            
            # 先用管理员账户连接并搜索用户
            admin_conn = ldap3.Connection(server, user=config.bind_dn, password=bind_password, auto_bind=True)
            
            # 搜索用户 - 支持两种过滤器格式
            search_filter = config.user_search_filter
            if '{username}' in search_filter:
                search_filter = search_filter.format(username=username)
            elif '%(user)s' in search_filter:
                search_filter = search_filter.replace('%(user)s', username)
            else:
                # 如果都不匹配，尝试直接替换
                search_filter = search_filter.format(username=username)
            admin_conn.search(
                search_base=config.base_dn,
                search_filter=search_filter,
                attributes=list(config.user_attr_map.values())
            )
            
            if not admin_conn.entries:
                admin_conn.unbind()
                raise LDAPError('用户不存在于LDAP服务器')
            
            # 获取搜索到的用户DN
            found_user_dn = admin_conn.entries[0].entry_dn
            admin_conn.unbind()
            
            # DN和用户密码进行认证
            user_conn = ldap3.Connection(server, user=found_user_dn, password=password, auto_bind=True)
            user_conn.unbind()
            
        except ldap3.core.exceptions.LDAPBindError as e:
            if 'invalidCredentials' in str(e):
                raise LDAPError('用户名或密码错误')
            else:
                raise LDAPError('LDAP认证失败')
        except ldap3.core.exceptions.LDAPSocketOpenError:
            raise LDAPError('LDAP服务器连接失败')
        except ldap3.core.exceptions.LDAPSocketReceiveError:
            raise LDAPError('LDAP服务器连接超时')
        except ldap3.core.exceptions.LDAPException as e:
            raise LDAPError(f'LDAP错误: {str(e)}')

    @staticmethod
    def _get_existing_user(username):
        """获取已存在的LDAP用户"""
        try:
            return User.objects.get(username=username, user_type='ldap')
        except User.DoesNotExist:
            raise LDAPError(f'用户{username}不存在，请联系管理员同步LDAP用户')

 