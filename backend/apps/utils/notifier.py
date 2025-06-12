import json
import time
import hmac
import base64
import hashlib
import logging
import requests
from urllib.parse import quote_plus
from django.conf import settings
from ..models import NotificationRobot, BuildHistory

logger = logging.getLogger('apps')

class BuildNotifier:
    """构建通知工具类"""
    
    def __init__(self, history: BuildHistory):
        self.history = history
        self.task = history.task
        self.project = history.task.project
        self.environment = history.task.environment

    def _sign_dingtalk(self, secret: str, timestamp: str) -> str:
        """钉钉机器人签名"""
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def _sign_feishu(self, secret: str, timestamp: str) -> str:
        """飞书机器人签名"""
        string_to_sign = f'{timestamp}\n{secret}'
        hmac_code = hmac.new(
            secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(hmac_code).decode('utf-8')

    def _get_build_status_emoji(self) -> str:
        """获取构建状态对应的emoji"""
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'running': '🔄',
            'pending': '⏳',
            'terminated': '🛑'
        }
        return status_emoji.get(self.history.status, '❓')

    def _get_duration_text(self) -> str:
        """获取构建耗时文本"""
        if not self.history.build_time or 'total_duration' not in self.history.build_time:
            return '未完成'
        
        duration = int(self.history.build_time['total_duration'])
        if duration < 60:
            return f'{duration}秒'
        minutes = duration // 60
        seconds = duration % 60
        return f'{minutes}分{seconds}秒'

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_texts = {
            'success': '构建成功',
            'failed': '构建失败',
            'running': '构建中',
            'pending': '等待中',
            'terminated': '构建已终止'
        }
        return status_texts.get(self.history.status, self.history.status)

    def _get_build_url(self) -> str:
        """获取构建历史页面URL"""
        base_url = getattr(settings, 'WEB_URL', 'http://localhost:5173')  # 如果未配置，使用默认值
        return f"{base_url}/build/history?history_id={self.history.history_id}"

    def _format_dingtalk_message(self) -> dict:
        """格式化钉钉通知消息"""
        status_text = self._get_status_text()
        build_url = self._get_build_url()
        
        content = [
            f"## 🔔 构建通知：{status_text}",
            "---",
            "**构建详情：**",
            f"- **任务名称**：{self.task.name}",
            f"- **构建编号**：#{self.history.build_number}",
            f"- **构建版本**：{self.history.version}",
            f"- **构建分支**：{self.history.branch}",
            f"- **提交ID**：{self.history.commit_id[:8] if self.history.commit_id else '无'}",
            f"- **构建环境**：{self.environment.name}",
            f"- **构建人员**：{self.history.operator.name if self.history.operator else '系统'}",
            f"- **构建耗时**：{self._get_duration_text()}",
            "",
            "**构建需求：**",
            f"> {self.history.requirement or '无'}",
            "",
            f"**查看详情：**[点击查看构建日志]({build_url})",
            "",
            "---",
            "**注意事项：**",
            "1. 此为自动通知，请勿回复",
            "2. 如遇构建失败，请先查看构建日志进行排查",
            "3. 如需帮助，请联系运维同学"
        ]
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "title": f"{status_text}: {self.task.name} #{self.history.build_number}",
                "text": "\n".join(content)
            },
            "at": {
                "isAtAll": True
            }
        }

    def _format_wecom_message(self) -> dict:
        """格式化企业微信通知消息"""
        status_text = self._get_status_text()
        build_url = self._get_build_url()
        
        content = [
            f"## 🔔 构建通知：{status_text}",
            "---",
            "@all",  # 企业微信使用 @all 来@所有人
            "",
            "**构建详情：**",
            f"- **任务名称**：{self.task.name}",
            f"- **构建编号**：#{self.history.build_number}",
            f"- **构建版本**：{self.history.version}",
            f"- **构建分支**：{self.history.branch}",
            f"- **提交ID**：{self.history.commit_id[:8] if self.history.commit_id else '无'}",
            f"- **构建环境**：{self.environment.name}",
            f"- **构建人员**：{self.history.operator.name if self.history.operator else '系统'}",
            f"- **构建耗时**：{self._get_duration_text()}",
            "",
            "**构建需求：**",
            f"> {self.history.requirement or '无'}",
            "",
            f"**查看详情：**[点击查看构建日志]({build_url})",
            "",
            "---",
            "**注意事项：**",
            "1. 此为自动通知，请勿回复",
            "2. 如遇构建失败，请先查看构建日志进行排查",
            "3. 如需帮助，请联系运维同学"
        ]
        
        return {
            "msgtype": "markdown",
            "markdown": {
                "content": "\n".join(content)
            }
        }

    def _format_feishu_message(self) -> dict:
        """格式化飞书通知消息"""
        status_text = self._get_status_text()
        build_url = self._get_build_url()
        
        content = [
            f"🔔 构建通知：{status_text}",
            "---",
            "<at user_id=\"all\">所有人</at>",  # 飞书使用这种格式@所有人
            "",
            "**构建详情：**",
            f"- **任务名称**：{self.task.name}",
            f"- **构建编号**：#{self.history.build_number}",
            f"- **构建版本**：{self.history.version}",
            f"- **构建分支**：{self.history.branch}",
            f"- **提交ID**：{self.history.commit_id[:8] if self.history.commit_id else '无'}",
            f"- **构建环境**：{self.environment.name}",
            f"- **构建人员**：{self.history.operator.name if self.history.operator else '系统'}",
            f"- **构建耗时**：{self._get_duration_text()}",
            "",
            "**构建需求：**",
            f"> {self.history.requirement or '无'}",
            "",
            f"**查看详情：**[点击查看构建日志]({build_url})",
            "",
            "---",
            "**注意事项：**",
            "1. 此为自动通知，请勿回复",
            "2. 如遇构建失败，请先查看构建日志进行排查",
            "3. 如需帮助，请联系运维同学"
        ]
        
        return {
            "msg_type": "text",
            "content": {
                "text": "\n".join(content)
            }
        }

    def send_notifications(self):
        """发送构建通知"""
        if not self.task.notification_channels:
            logger.info(f"任务 {self.task.name} 未配置通知方式")
            return
        
        # 获取需要通知的机器人
        robots = NotificationRobot.objects.filter(robot_id__in=self.task.notification_channels)
        
        for robot in robots:
            try:
                webhook = robot.webhook
                timestamp = str(int(time.time() * 1000))
                headers = {}
                
                # 根据机器人类型处理安全设置
                if robot.security_type == 'secret' and robot.secret:
                    if robot.type == 'dingtalk':
                        sign = self._sign_dingtalk(robot.secret, timestamp)
                        webhook = f"{webhook}&timestamp={timestamp}&sign={quote_plus(sign)}"
                    elif robot.type == 'feishu':
                        sign = self._sign_feishu(robot.secret, timestamp)
                        headers.update({
                            "X-Timestamp": timestamp,
                            "X-Sign": sign
                        })
                
                # 根据机器人类型获取消息内容
                if robot.type == 'dingtalk':
                    message = self._format_dingtalk_message()
                elif robot.type == 'wecom':
                    message = self._format_wecom_message()
                elif robot.type == 'feishu':
                    message = self._format_feishu_message()
                else:
                    logger.error(f"不支持的机器人类型: {robot.type}")
                    continue
                
                # 发送通知
                response = requests.post(webhook, json=message, headers=headers)
                
                if response.status_code == 200:
                    resp_json = response.json()
                    if resp_json.get('errcode') == 0 or resp_json.get('StatusCode') == 0 or resp_json.get('code') == 0:
                        logger.info(f"发送 {robot.type} 通知成功: {robot.name}")
                    else:
                        logger.error(f"发送 {robot.type} 通知失败: {response.text}")
                else:
                    logger.error(f"发送 {robot.type} 通知失败: {response.text}")
                    
            except Exception as e:
                logger.error(f"发送 {robot.type} 通知出错: {str(e)}", exc_info=True) 