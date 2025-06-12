import json
import uuid
import hashlib
import hmac
import base64
import time
import logging
import requests
from urllib.parse import quote_plus
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from ..models import NotificationRobot, User
from ..utils.auth import jwt_auth_required

logger = logging.getLogger('apps')

def generate_id():
    """生成唯一ID"""
    return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()[:32]

@method_decorator(csrf_exempt, name='dispatch')
class NotificationRobotView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request, robot_id=None):
        """获取机器人列表或单个机器人详情"""
        try:
            if robot_id:
                try:
                    robot = NotificationRobot.objects.select_related('creator').get(robot_id=robot_id)
                    return JsonResponse({
                        'code': 200,
                        'message': '获取机器人详情成功',
                        'data': {
                            'robot_id': robot.robot_id,
                            'type': robot.type,
                            'name': robot.name,
                            'webhook': robot.webhook,
                            'security_type': robot.security_type,
                            'secret': robot.secret,
                            'keywords': robot.keywords,
                            'ip_list': robot.ip_list,
                            'remark': robot.remark,
                            'creator': {
                                'user_id': robot.creator.user_id,
                                'name': robot.creator.name
                            } if robot.creator else None,
                            'create_time': robot.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                            'update_time': robot.update_time.strftime('%Y-%m-%d %H:%M:%S')
                        }
                    })
                except NotificationRobot.DoesNotExist:
                    return JsonResponse({
                        'code': 404,
                        'message': '机器人不存在'
                    })

            # 获取所有机器人列表
            robots = NotificationRobot.objects.select_related('creator').all()
            robot_list = []
            for robot in robots:
                robot_list.append({
                    'robot_id': robot.robot_id,
                    'type': robot.type,
                    'name': robot.name,
                    'webhook': robot.webhook,
                    'security_type': robot.security_type,
                    'secret': robot.secret,
                    'keywords': robot.keywords,
                    'ip_list': robot.ip_list,
                    'remark': robot.remark,
                    'creator': {
                        'user_id': robot.creator.user_id,
                        'name': robot.creator.name
                    } if robot.creator else None,
                    'create_time': robot.create_time.strftime('%Y-%m-%d %H:%M:%S')
                })

            return JsonResponse({
                'code': 200,
                'message': '获取机器人列表成功',
                'data': robot_list
            })

        except Exception as e:
            logger.error(f'获取机器人失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def post(self, request):
        """创建机器人"""
        try:
            data = json.loads(request.body)
            robot_type = data.get('type')
            name = data.get('name')
            webhook = data.get('webhook')
            security_type = data.get('security_type', 'none')
            secret = data.get('secret')
            keywords = data.get('keywords', [])
            ip_list = data.get('ip_list', [])
            remark = data.get('remark')

            # 验证必要字段
            if not all([robot_type, name, webhook]):
                return JsonResponse({
                    'code': 400,
                    'message': '机器人类型、名称和Webhook地址不能为空'
                })

            # 验证机器人类型
            if robot_type not in ['dingtalk', 'wecom', 'feishu']:
                return JsonResponse({
                    'code': 400,
                    'message': '不支持的机器人类型'
                })

            # 验证安全设置
            if security_type == 'secret' and not secret:
                return JsonResponse({
                    'code': 400,
                    'message': '使用加签密钥时，密钥不能为空'
                })
            elif security_type == 'keyword' and not keywords:
                return JsonResponse({
                    'code': 400,
                    'message': '使用自定义关键词时，关键词不能为空'
                })
            elif security_type == 'ip' and not ip_list:
                return JsonResponse({
                    'code': 400,
                    'message': '使用IP白名单时，IP列表不能为空'
                })

            # 创建机器人
            creator = User.objects.get(user_id=request.user_id)
            robot = NotificationRobot.objects.create(
                robot_id=generate_id(),
                type=robot_type,
                name=name,
                webhook=webhook,
                security_type=security_type,
                secret=secret,
                keywords=keywords,
                ip_list=ip_list,
                remark=remark,
                creator=creator
            )

            return JsonResponse({
                'code': 200,
                'message': '创建机器人成功',
                'data': {
                    'robot_id': robot.robot_id
                }
            })

        except Exception as e:
            logger.error(f'创建机器人失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def put(self, request):
        """更新机器人"""
        try:
            data = json.loads(request.body)
            robot_id = data.get('robot_id')
            name = data.get('name')
            webhook = data.get('webhook')
            security_type = data.get('security_type')
            secret = data.get('secret')
            keywords = data.get('keywords')
            ip_list = data.get('ip_list')
            remark = data.get('remark')

            if not robot_id:
                return JsonResponse({
                    'code': 400,
                    'message': '机器人ID不能为空'
                })

            try:
                robot = NotificationRobot.objects.get(robot_id=robot_id)
            except NotificationRobot.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '机器人不存在'
                })

            # 验证必要字段
            if name:
                robot.name = name
            if webhook:
                robot.webhook = webhook
            if security_type:
                robot.security_type = security_type
            if secret is not None:
                robot.secret = secret
            if keywords is not None:
                robot.keywords = keywords
            if ip_list is not None:
                robot.ip_list = ip_list
            if remark is not None:
                robot.remark = remark

            # 验证安全设置
            if robot.security_type == 'secret' and not robot.secret:
                return JsonResponse({
                    'code': 400,
                    'message': '使用加签密钥时，密钥不能为空'
                })
            elif robot.security_type == 'keyword' and not robot.keywords:
                return JsonResponse({
                    'code': 400,
                    'message': '使用自定义关键词时，关键词不能为空'
                })
            elif robot.security_type == 'ip' and not robot.ip_list:
                return JsonResponse({
                    'code': 400,
                    'message': '使用IP白名单时，IP列表不能为空'
                })

            robot.save()

            return JsonResponse({
                'code': 200,
                'message': '更新机器人成功'
            })

        except Exception as e:
            logger.error(f'更新机器人失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

    @method_decorator(jwt_auth_required)
    def delete(self, request):
        """删除机器人"""
        try:
            data = json.loads(request.body)
            robot_id = data.get('robot_id')

            if not robot_id:
                return JsonResponse({
                    'code': 400,
                    'message': '机器人ID不能为空'
                })

            try:
                robot = NotificationRobot.objects.get(robot_id=robot_id)
                robot.delete()
                return JsonResponse({
                    'code': 200,
                    'message': '删除机器人成功'
                })
            except NotificationRobot.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '机器人不存在'
                })

        except Exception as e:
            logger.error(f'删除机器人失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class NotificationTestView(View):
    def _sign_dingtalk(self, secret, timestamp):
        """钉钉机器人签名"""
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def _sign_feishu(self, secret, timestamp):
        """飞书机器人签名"""
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    @method_decorator(jwt_auth_required)
    def post(self, request, *args, **kwargs):
        """测试机器人"""
        try:
            data = json.loads(request.body)
            robot_id = data.get('robot_id')

            if not robot_id:
                return JsonResponse({
                    'code': 400,
                    'message': '机器人ID不能为空'
                })

            try:
                robot = NotificationRobot.objects.get(robot_id=robot_id)
            except NotificationRobot.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '机器人不存在'
                })

            # 准备测试消息
            timestamp = str(int(time.time() * 1000))
            test_message = "这是一条测试消息，如果您收到了这条消息，说明机器人配置正确。"

            # 根据不同类型的机器人发送测试消息
            try:
                if robot.type == 'dingtalk':
                    # 钉钉机器人
                    webhook = robot.webhook
                    
                    # 如果使用加签方式
                    if robot.security_type == 'secret' and robot.secret:
                        sign = self._sign_dingtalk(robot.secret, timestamp)
                        webhook = f"{webhook}&timestamp={timestamp}&sign={quote_plus(sign)}"
                    
                    # 构建消息内容
                    message_data = {
                        "msgtype": "text",
                        "text": {
                            "content": test_message
                        }
                    }
                    
                    response = requests.post(webhook, json=message_data)

                elif robot.type == 'wecom':
                    # 企业微信机器人
                    response = requests.post(robot.webhook, json={
                        "msgtype": "text",
                        "text": {
                            "content": test_message
                        }
                    })

                elif robot.type == 'feishu':
                    # 飞书机器人
                    headers = {}
                    if robot.security_type == 'secret' and robot.secret:
                        sign = self._sign_feishu(robot.secret, timestamp)
                        headers.update({
                            "X-Timestamp": timestamp,
                            "X-Sign": sign
                        })
                    
                    response = requests.post(robot.webhook, json={
                        "msg_type": "text",
                        "content": {
                            "text": test_message
                        }
                    }, headers=headers)

                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get('errcode') == 0 or resp_json.get('StatusCode') == 0 or resp_json.get('code') == 0:
                        return JsonResponse({
                            'code': 200,
                            'message': '测试消息发送成功'
                        })
                    else:
                        return JsonResponse({
                            'code': 400,
                            'message': f'测试消息发送失败: {response.text}'
                        })
                else:
                    return JsonResponse({
                        'code': 400,
                        'message': f'测试消息发送失败: {response.text}'
                    })

            except Exception as e:
                logger.error(f'发送测试消息失败: {str(e)}', exc_info=True)
                return JsonResponse({
                    'code': 500,
                    'message': f'发送测试消息失败: {str(e)}'
                })

        except Exception as e:
            logger.error(f'测试机器人失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 