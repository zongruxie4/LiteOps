import os
import logging
import time
import subprocess
import tempfile
import re
import shutil
from datetime import datetime
from pathlib import Path
from django.conf import settings
from git import Repo
from git.exc import GitCommandError
from .build_stages import BuildStageExecutor
from .notifier import BuildNotifier
from .log_stream import log_stream_manager
from django.db.models import F
from ..models import BuildTask, BuildHistory
# from ..utils.builder import Builder
# from ..utils.crypto import decrypt_sensitive_data

logger = logging.getLogger('apps')

class Builder:
    def __init__(self, task, build_number, commit_id, history):
        self.task = task
        self.build_number = build_number
        self.commit_id = commit_id
        self.history = history  # 构建历史记录
        self.log_buffer = []  # 缓存日志

        # 检查是否已有指定的版本号
        if self.history.version:
            self.version = self.history.version
            self.send_log(f"使用指定版本: {self.version}", "Version")
        else:
            # 为开发和测试环境生成新的版本号
            self.version = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{commit_id[:8]}"

        # 初始化构建时间信息
        self.build_time = {
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stages_time': []
        }

        # 更新构建历史记录的状态和版本
        self.history.status = 'running'
        if not self.history.version:  # 只有当没有版本号时才更新
            self.history.version = self.version
        self.history.build_time = self.build_time
        self.history.save(update_fields=['status', 'version', 'build_time'])

        # 设置构建目录
        self.build_path = Path(settings.BUILD_ROOT) / task.name / self.version / task.project.name

        # 创建实时日志流
        log_stream_manager.create_build_stream(self.task.task_id, self.build_number)

    def check_if_terminated(self):
        """检查构建是否已被终止"""
        # 从数据库重新加载构建历史记录，以获取最新状态
        try:
            history_record = BuildHistory.objects.get(history_id=self.history.history_id)
            if history_record.status == 'terminated':
                # 如果状态为terminated，构建已被手动终止
                self.send_log("检测到构建已被手动终止，停止后续步骤", "System")
                return True
            return False
        except Exception as e:
            logger.error(f"检查构建状态时出错: {str(e)}", exc_info=True)
            return False

    def _filter_maven_progress(self, message):
        # 只过滤Maven下载进度信息中的Progress()部分
        if 'Progress (' in message and ('KB' in message or 'MB' in message or 'B/s' in message):
            return None

        # 过滤Maven下载进度条
        if re.match(r'^Progress \(\d+\): .+', message.strip()):
            return None

        # 过滤空的进度行
        if re.match(r'^\s*Progress\s*$', message.strip()):
            return None

        # 过滤下载进度百分比
        if re.match(r'^\s*\d+%\s*$', message.strip()):
            return None

        return message

    def send_log(self, message, stage=None, console_only=False, raw_output=False):
        """发送日志到缓存、实时流和控制台
        Args:
            message: 日志消息
            stage: 阶段名称
            console_only: 是否只输出到控制台（保留参数兼容性）
            raw_output: 是否为原始输出（不添加阶段标记）
        """
        # 过滤Maven Progress信息
        filtered_message = self._filter_maven_progress(message)
        if filtered_message is None:
            return  # 跳过被过滤的消息

        # 格式化消息
        if raw_output:
            formatted_message = filtered_message
        else:
            formatted_message = filtered_message

            # 如果有阶段名称，添加阶段标记
            if stage:
                formatted_message = f"[{stage}] {filtered_message}"

        # 缓存日志
        self.log_buffer.append(formatted_message)

        # 推送到实时日志流
        try:
            log_stream_manager.push_log(
                task_id=self.task.task_id,
                build_number=self.build_number,
                message=formatted_message + '\n',
                stage=stage
            )
        except Exception as e:
            # 降低日志级别，避免在清理阶段产生过多错误日志
            if "日志队列不存在" in str(e):
                logger.debug(f"日志队列已清理，跳过推送: {str(e)}")
            else:
                logger.error(f"推送实时日志失败: {str(e)}", exc_info=True)

        # 批量更新数据库中的构建日志
        try:
            should_update_db = (
                len(self.log_buffer) % 10 == 0 or  # 每10条日志更新一次
                not hasattr(self, '_last_db_update') or
                time.time() - getattr(self, '_last_db_update', 0) >= 5  # 每5秒更新一次
            )

            if should_update_db:
                current_log = '\n'.join(self.log_buffer)
                self.history.build_log = current_log
                self.history.save(update_fields=['build_log'])
                self._last_db_update = time.time()
        except Exception as e:
            logger.error(f"批量更新构建日志失败: {str(e)}", exc_info=True)

        # 输出到控制台 - 确保构建日志在控制台显示
        logger.info(formatted_message, extra={
            'from_builder': True,  # 添加标记以区分构建日志
            'task_id': self.task.task_id,
            'build_number': self.build_number
        })

    def _save_build_log(self):
        """保存构建日志到历史记录"""
        try:
            self.history.build_log = '\n'.join(self.log_buffer)
            self.history.save(update_fields=['build_log'])
        except Exception as e:
            logger.error(f"保存构建日志失败: {str(e)}", exc_info=True)

    def clone_repository(self):
        """克隆Git仓库"""
        try:
            # 检查构建是否已被终止
            if self.check_if_terminated():
                return False

            self.send_log("开始克隆代码...", "Git Clone")
            self.send_log(f"构建目录: {self.build_path}", "Git Clone")

            # 确保目录存在
            self.build_path.parent.mkdir(parents=True, exist_ok=True)

            # 获取Git凭证
            repository = self.task.project.repository
            self.send_log(f"仓库地址: {repository}", "Git Clone")
            git_token = self.task.git_token.token if self.task.git_token else None

            # 处理带有token的仓库URL
            if git_token and repository.startswith('http'):
                if '@' in repository:
                    repository = repository.split('@')[1]
                    repository = f'https://oauth2:{git_token}@{repository}'
                else:
                    repository = repository.replace('://', f'://oauth2:{git_token}@')

            # 使用构建历史记录中的分支
            branch = self.history.branch
            self.send_log(f"克隆分支: {branch}", "Git Clone")
            self.send_log("正在克隆代码，请稍候...", "Git Clone")

            # 克隆指定分支的代码
            Repo.clone_from(
                repository,
                str(self.build_path),
                branch=branch,
                progress=self.git_progress
            )

            # 检查构建是否已被终止
            if self.check_if_terminated():
                return False

            # 验证克隆是否成功
            if not os.path.exists(self.build_path) or not os.listdir(self.build_path):
                self.send_log("代码克隆失败：目录为空", "Git Clone")
                return False

            self.send_log("代码克隆完成", "Git Clone")
            self.send_log(f"克隆目录验证成功: {self.build_path}", "Git Clone")
            return True

        except GitCommandError as e:
            self.send_log(f"克隆代码失败: {str(e)}", "Git Clone")
            return False
        except Exception as e:
            self.send_log(f"发生错误: {str(e)}", "Git Clone")
            return False

    def git_progress(self, op_code, cur_count, max_count=None, message=''):
        """Git进度回调"""
        # 每秒检查一次构建是否已被终止
        if int(time.time()) % 5 == 0:  # 每5秒检查一次
            if self.check_if_terminated():
                # 如果构建已被终止，尝试引发异常停止Git克隆
                raise Exception("Build terminated")
        pass

    def clone_external_scripts(self):
        """克隆外部脚本库"""
        try:
            if not self.task.use_external_script:
                return True

            # 检查外部脚本库配置
            config = self.task.external_script_config
            if not config or not config.get('repo_url') or not config.get('directory') or not config.get('branch'):
                self.send_log("外部脚本库配置不完整，跳过克隆", "External Scripts")
                return True

            # 检查构建是否已被终止
            if self.check_if_terminated():
                return False

            repo_url = config.get('repo_url')
            base_directory = config.get('directory')
            branch = config.get('branch')  # 分支为必填项
            token_id = config.get('token_id')

            # 从仓库URL中提取项目名称
            import re
            repo_name_match = re.search(r'/([^/]+?)(?:\.git)?/?$', repo_url)
            if repo_name_match:
                repo_name = repo_name_match.group(1)
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
            else:
                repo_name = 'external-scripts'

            # 完整的克隆目录路径
            directory = os.path.join(base_directory, repo_name)

            self.send_log("开始克隆外部脚本库...", "External Scripts")
            self.send_log(f"仓库地址: {repo_url}", "External Scripts")
            self.send_log(f"基础目录: {base_directory}", "External Scripts")
            self.send_log(f"项目名称: {repo_name}", "External Scripts")
            self.send_log(f"完整目录: {directory}", "External Scripts")
            self.send_log(f"分支: {branch}", "External Scripts")

            # 获取Git Token（如果配置了）
            git_token = None
            if token_id:
                try:
                    from ..models import GitlabTokenCredential
                    credential = GitlabTokenCredential.objects.get(credential_id=token_id)
                    git_token = credential.token
                except:
                    self.send_log("获取Git Token失败，尝试使用公开仓库方式克隆", "External Scripts")

            # 处理带有token的仓库URL
            if git_token and repo_url.startswith('http'):
                if '@' in repo_url:
                    repo_url = repo_url.split('@')[1]
                    repo_url = f'https://oauth2:{git_token}@{repo_url}'
                else:
                    repo_url = repo_url.replace('://', f'://oauth2:{git_token}@')

            # 确保基础目录存在
            os.makedirs(base_directory, exist_ok=True)

            # 如果目标目录已存在且不为空，先清空
            if os.path.exists(directory) and os.listdir(directory):
                self.send_log(f"清空现有目录: {directory}", "External Scripts")
                shutil.rmtree(directory)

            # 克隆外部脚本库
            self.send_log("正在克隆外部脚本库，请稍候...", "External Scripts")

            from git import Repo
            # 使用指定分支克隆
            Repo.clone_from(
                repo_url,
                directory,
                branch=branch
            )

            # 再次检查构建是否已被终止
            if self.check_if_terminated():
                return False

            # 验证克隆是否成功
            if not os.path.exists(directory) or not os.listdir(directory):
                self.send_log("外部脚本库克隆失败：目录为空", "External Scripts")
                return False

            self.send_log("外部脚本库克隆完成", "External Scripts")
            self.send_log(f"克隆目录验证成功: {directory}", "External Scripts")
            return True

        except Exception as e:
            self.send_log(f"克隆外部脚本库失败: {str(e)}", "External Scripts")
            # 如果用户配置了外部脚本库，克隆失败应该终止构建
            self.send_log("外部脚本库克隆失败，终止构建", "External Scripts")
            return False

    def execute_stages(self, stage_executor):
        """执行构建阶段"""
        try:
            if not self.task.stages:
                self.send_log("没有配置构建阶段", "Build Stages")
                return False

            # 检查构建是否已被终止
            if self.check_if_terminated():
                return False

            # 执行所有阶段
            success = stage_executor.execute_stages(self.task.stages, check_termination=self.check_if_terminated)
            return success

        except Exception as e:
            self.send_log(f"执行构建阶段时发生错误: {str(e)}", "Build Stages")
            return False

    def execute(self):
        """执行构建"""
        build_start_time = time.time()
        success = False # 初始化成功状态
        try:
            # 在开始构建前检查构建是否已被终止
            if self.check_if_terminated():
                self._update_build_stats(False)
                self._save_build_log()
                return False

            # 获取环境类型
            environment_type = self.task.environment.type if self.task.environment else None

            # 根据是否有分支信息决定是否需要克隆代码
            should_clone_code = (
                environment_type in ['development', 'testing'] or 
                (environment_type in ['staging', 'production'] and self.history.branch)
            )

            if should_clone_code:
                # 克隆代码
                self.send_log(f"开始克隆代码，分支: {self.history.branch}", "Git Clone")
                clone_start_time = time.time()
                if not self.clone_repository():
                    self._update_build_stats(False)  # 更新失败统计
                    self._update_build_time(build_start_time, False)
                    # 发送构建失败通知
                    notifier = BuildNotifier(self.history)
                    notifier.send_notifications()
                    return False

                # 记录代码克隆阶段的时间
                self.build_time['stages_time'].append({
                    'name': 'Git Clone',
                    'start_time': datetime.fromtimestamp(clone_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': str(int(time.time() - clone_start_time))
                })
            else:
                # 预发布/生产环境使用版本模式，不克隆代码
                # self.send_log(f"预发布/生产环境版本模式，使用版本: {self.history.version}", "Environment")
                # 创建构建目录
                os.makedirs(self.build_path, exist_ok=True)

            # 再次检查构建是否已被终止
            if self.check_if_terminated():
                self._update_build_stats(False)
                self._update_build_time(build_start_time, False)
                return False

            # 克隆外部脚本库（如果配置了）
            external_script_start_time = time.time()
            if not self.clone_external_scripts():
                self._update_build_stats(False)
                self._update_build_time(build_start_time, False)
                # 发送构建失败通知
                notifier = BuildNotifier(self.history)
                notifier.send_notifications()
                return False

            # 记录外部脚本库克隆阶段的时间（如果启用了外部脚本库）
            if self.task.use_external_script:
                self.build_time['stages_time'].append({
                    'name': 'External Scripts Clone',
                    'start_time': datetime.fromtimestamp(external_script_start_time).strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': str(int(time.time() - external_script_start_time))
                })

            # 检查构建是否已被终止
            if self.check_if_terminated():
                self._update_build_stats(False)
                self._update_build_time(build_start_time, False)
                return False

            # 创建阶段执行器，传递send_log方法和构建时间记录回调
            stage_executor = BuildStageExecutor(
                str(self.build_path),
                lambda msg, stage=None, raw_output=False: self.send_log(msg, stage, raw_output=raw_output),
                self._record_stage_time
            )

            # 设置系统内置环境变量
            system_variables = {
                # 编号相关变量
                'BUILD_NUMBER': str(self.build_number),
                'VERSION': self.version,

                # Git相关变量
                'COMMIT_ID': self.commit_id,
                'BRANCH': self.history.branch,

                # 项目相关变量
                'PROJECT_NAME': self.task.project.name,
                'PROJECT_ID': self.task.project.project_id,
                'PROJECT_REPO': self.task.project.repository,

                # 任务相关变量
                'TASK_NAME': self.task.name,
                'TASK_ID': self.task.task_id,

                # 环境相关变量
                'ENVIRONMENT': self.task.environment.name,
                'ENVIRONMENT_TYPE': self.task.environment.type,
                'ENVIRONMENT_ID': self.task.environment.environment_id,

                # 别名(便于使用)
                'service_name': self.task.name,
                'build_env': self.task.environment.name,
                'branch': self.history.branch,
                'version': self.version,

                # 构建路径
                'BUILD_PATH': str(self.build_path),
                'BUILD_WORKSPACE': str(self.build_path),

                # Docker配置
                'DOCKER_BUILDKIT': '0',
                'BUILDKIT_PROGRESS': 'plain',
                
                # Locale配置 - 使用稳定的POSIX locale避免SSH连接时的警告
                'LC_ALL': 'POSIX',
                'LANG': 'POSIX',
            }

            # 添加自定义参数变量
            custom_parameters = {}
            if self.history.parameter_values:
                for param_name, selected_values in self.history.parameter_values.items():
                    custom_parameters[param_name] = ','.join(selected_values)
                    self.send_log(f"设置参数变量: {param_name}={custom_parameters[param_name]}", "Parameters")

            combined_env = {**os.environ, **system_variables, **custom_parameters}
            stage_executor.env = combined_env

            # 保存系统变量和自定义参数到文件
            all_variables = {**system_variables, **custom_parameters}
            stage_executor._save_variables_to_file(all_variables)

            # 执行构建阶段
            success = self.execute_stages(stage_executor)
            return success

        except Exception as e:
            self.send_log(f"构建过程中发生未捕获的异常: {str(e)}", "Error")
            success = False
            return False
        finally:
            # 更新构建统计和时间信息
            self._update_build_stats(success)
            self._update_build_time(build_start_time, success)

            # 确保最终日志保存到数据库
            self._save_build_log()

            # 输出构建完成状态日志
            self.history.refresh_from_db()
            final_status = self.history.status
            self.send_log(f"构建完成，状态: {final_status}", "Build")

            # 确保构建完成状态日志也保存到数据库
            self._save_build_log()

            # 通知日志流管理器构建完成
            try:
                log_stream_manager.complete_build(
                    task_id=self.task.task_id,
                    build_number=self.build_number,
                    status=final_status
                )
            except Exception as e:
                logger.error(f"通知日志流管理器构建完成失败: {str(e)}", exc_info=True)

            # 发送构建通知
            notifier = BuildNotifier(self.history)
            notifier.send_notifications()

    def _record_stage_time(self, stage_name: str, start_time: float, duration: float):
        """记录阶段执行时间
        Args:
            stage_name: 阶段名称
            start_time: 开始时间戳
            duration: 耗时（秒）
        """
        stage_time = {
            'name': stage_name,
            'start_time': datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            'duration': str(int(duration))
        }
        self.build_time['stages_time'].append(stage_time)

        # 更新构建历史记录的阶段信息
        self.history.stages = self.task.stages
        self.history.save(update_fields=['stages'])

    def _update_build_time(self, build_start_time: float, success: bool):
        """更新构建时间信息
        Args:
            build_start_time: 构建开始时间戳
            success: 构建是否成功
        """
        try:
            # 计算总耗时
            total_duration = int(time.time() - build_start_time)

            # 更新构建时间信息
            self.build_time['total_duration'] = str(total_duration)
            self.build_time['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 检查当前构建状态，如果已经是terminated则不覆盖状态
            self.history.refresh_from_db()
            if self.history.status != 'terminated':
                # 只有在状态不是terminated时才更新状态
                self.history.status = 'success' if success else 'failed'

            self.history.build_time = self.build_time
            self.history.save(update_fields=['status', 'build_time'])
        except Exception as e:
            logger.error(f"更新构建时间信息失败: {str(e)}", exc_info=True)

    def _update_build_stats(self, success: bool):
        """更新构建统计信息
        Args:
            success: 构建是否成功
        """
        try:
            # 检查当前构建状态，如果是terminated则不更新统计
            self.history.refresh_from_db()
            if self.history.status == 'terminated':
                return

            # 更新任务的构建统计信息
            if success:
                BuildTask.objects.filter(task_id=self.task.task_id).update(
                    success_builds=F('success_builds') + 1
                )
                # 只有成功的构建才更新版本号
                BuildTask.objects.filter(task_id=self.task.task_id).update(
                    version=self.version
                )
            else:
                BuildTask.objects.filter(task_id=self.task.task_id).update(
                    failure_builds=F('failure_builds') + 1
                )
        except Exception as e:
            logger.error(f"更新构建统计信息失败: {str(e)}", exc_info=True)

