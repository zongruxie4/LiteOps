import os
import subprocess
import logging
import time
import tempfile
from typing import List, Dict, Any, Callable

logger = logging.getLogger('apps')

class BuildStageExecutor:
    """构建阶段执行器"""

    def __init__(self, build_path: str, send_log: Callable, record_time: Callable):
        """
        初始化构建阶段执行器
        Args:
            build_path: 构建目录路径
            send_log: 发送日志的回调函数
            record_time: 记录时间的回调函数
        """
        self.build_path = build_path
        self.send_log = send_log
        self.record_time = record_time
        self.env = {} # 初始化为空字典，将由 Builder 设置

        # 用于存储临时变量文件的路径
        self.vars_file = os.path.join(self.build_path, '.build_vars')
        self._init_vars_file()

    def _init_vars_file(self):
        """初始化变量文件"""
        try:
            with open(self.vars_file, 'w') as f:
                f.write('#!/bin/bash\n# 构建变量\n')
            # 设置执行权限
            os.chmod(self.vars_file, 0o755)
        except Exception as e:
            logger.error(f"初始化变量文件失败: {str(e)}", exc_info=True)

    def _save_variables_to_file(self, variables):
        """
        将变量保存到文件
        Args:
            variables: 变量字典
        """
        try:
            if not variables:
                return

            # 追加变量到变量文件
            with open(self.vars_file, 'a') as f:
                for name, value in variables.items():
                    if name.startswith(('_', 'BASH_', 'SHELL', 'HOME', 'PATH', 'PWD', 'OLDPWD')):
                        continue
                    safe_value = self._escape_shell_value(str(value))
                    f.write(f'export {name}={safe_value}\n')
        except Exception as e:
            logger.error(f"保存变量到文件失败: {str(e)}", exc_info=True)

    def _escape_shell_value(self, value):
        """
        转义shell变量值
        Args:
            value: 要转义的值
        Returns:
            str: 转义后的值
        """
        try:
            # 如果值为空，返回空字符串
            if not value:
                return '""'

            # 如果值只包含安全字符（字母、数字、下划线、点、斜杠、冒号），不需要引号
            import re
            if re.match(r'^[a-zA-Z0-9_./:-]+$', value):
                return value

            # 用单引号包围，并转义其中的单引号
            escaped_value = value.replace("'", "'\"'\"'")
            return f"'{escaped_value}'"
        except Exception as e:
            logger.error(f"转义shell值失败: {str(e)}", exc_info=True)
            return '""'

    def _is_variable_assignment(self, line):
        """
        检查是否是变量赋值语句
        Args:
            line: 要检查的行
        Returns:
            bool: 是否是变量赋值语句
        """
        try:
            import re
            # 去除前导空格
            line = line.strip()

            # 检查是否是 export VAR=value 格式
            if line.startswith('export '):
                line = line[7:].strip()  # 移除 'export ' 前缀

            # 检查是否符合变量赋值格式：VAR=value
            # 变量名必须以字母或下划线开头，后面可以跟字母、数字、下划线
            pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*='
            return bool(re.match(pattern, line))
        except Exception as e:
            logger.error(f"检查变量赋值语句失败: {str(e)}", exc_info=True)
            return False

    def _process_echo_commands(self, script_content: str) -> str:
        """
        处理脚本内容中的echo命令，使其不显示执行过程
        """
        try:
            import re
            lines = script_content.split('\n')
            processed_lines = []
            
            for line in lines:
                # 保留原始缩进
                leading_whitespace = len(line) - len(line.lstrip())
                stripped_line = line.strip()
                indent = line[:leading_whitespace]
                
                # 使用正则表达式匹配echo命令
                # 匹配echo格式：echo、echo -n、echo -e
                echo_pattern = r'^echo(\s+-[a-zA-Z]*)?(\s+.*)?\s*$'
                
                if stripped_line and re.match(echo_pattern, stripped_line):
                    wrapped_line = f"{indent}{{ set +x; }} 2>/dev/null; {stripped_line}; {{ set -x; }} 2>/dev/null"
                    processed_lines.append(wrapped_line)
                else:
                    # 不是echo命令，保持原样
                    processed_lines.append(line)
            
            return '\n'.join(processed_lines)
            
        except Exception as e:
            logger.error(f"处理echo命令失败: {str(e)}", exc_info=True)
            # 如果处理失败，返回原始内容
            return script_content

    def _create_temp_script_file(self, script_content: str, stage_name: str) -> str:
        """
        创建临时脚本文件，支持Jenkins风格的命令显示
        Args:
            script_content: 内联脚本内容
            stage_name: 阶段名称
        Returns:
            str: 临时脚本文件路径
        """
        try:
            # 创建临时脚本文件
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.sh', 
                prefix=f'.build_stage_{stage_name}_',
                dir=self.build_path,
                delete=False
            ) as temp_file:
                # 写入脚本头部
                temp_file.write('#!/bin/bash\n')
                temp_file.write('set -e  # 遇到错误立即退出\n')
                temp_file.write('set -o pipefail  # 管道命令中任何一个失败都视为失败\n')
                temp_file.write('\n')
                
                # 加载变量文件
                temp_file.write(f'# 加载构建变量\n')
                temp_file.write(f'source "{self.vars_file}" 2>/dev/null || true\n')
                temp_file.write('\n')
                
                # 启用命令显示（bash调试模式）
                temp_file.write('set -x  # 显示执行的命令\n')
                temp_file.write('\n')
                
                temp_file.write('# 用户脚本开始\n')
                
                # 处理脚本内容，将echo命令包装为不显示执行过程的形式
                processed_content = self._process_echo_commands(script_content)
                temp_file.write(processed_content)
                
                temp_file.write('\n')
                
                script_path = temp_file.name
            
            # 设置执行权限
            os.chmod(script_path, 0o755)
            return script_path
            
        except Exception as e:
            self.send_log(f"创建临时脚本文件失败: {str(e)}", stage_name)
            return None

    def _execute_script_unified(self, script_path: str, stage_name: str, check_termination: Callable = None) -> bool:
        try:
            # 检查是否应该终止
            if check_termination and check_termination():
                self.send_log("构建已被终止，跳过脚本执行", stage_name)
                return False

            # 执行脚本，合并stdout和stderr到同一个流，保持输出顺序
            process = subprocess.Popen(
                ['/bin/bash', script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 将stderr重定向到stdout，保持输出顺序
                cwd=self.build_path,
                env=self.env,
                universal_newlines=True,
                bufsize=1  # 行缓冲，确保输出能够实时获取
            )

            # 实时读取并发送输出
            import fcntl
            import os

            # 设置非阻塞模式
            fd = process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

            # 持续读取直到进程结束
            while process.poll() is None:
                # 检查是否终止
                if check_termination and check_termination():
                    process.terminate()
                    self.send_log("构建已被终止，停止当前脚本", stage_name)
                    return False

                try:
                    line = process.stdout.readline()
                    if line:
                        line = line.rstrip()
                        self.send_log(line, stage_name, raw_output=True)
                except BlockingIOError:
                    time.sleep(0.01)
                    continue

            remaining_output = process.stdout.read()
            if remaining_output:
                for line in remaining_output.splitlines():
                    if line.strip():
                        self.send_log(line.rstrip(), stage_name, raw_output=True)

            # 检查执行结果
            success = process.returncode == 0

            if not success:
                self.send_log(f"脚本执行失败，返回码: {process.returncode}", stage_name)

            return success

        except Exception as e:
            self.send_log(f"执行脚本时发生错误: {str(e)}", stage_name)
            return False
        finally:
            if script_path.startswith(tempfile.gettempdir()) or '/.build_stage_' in script_path:
                try:
                    # 清理临时脚本文件
                    # pass
                    os.unlink(script_path)
                except Exception as e:
                    logger.debug(f"清理临时脚本文件失败: {str(e)}")

    def execute_stage(self, stage: Dict[str, Any], check_termination: Callable = None) -> bool:
        """
        执行单个构建阶段
        Args:
            stage: 阶段配置信息
            check_termination: 检查是否终止的回调函数
        Returns:
            bool: 执行是否成功
        """
        try:
            stage_name = stage.get('name', '未命名阶段')

            if check_termination and check_termination():
                self.send_log("构建已被终止，跳过此阶段", stage_name)
                return False

            # 记录阶段开始时间
            stage_start_time = time.time()

            # 执行脚本
            success = self._execute_inline_script(stage, check_termination)

            # 记录阶段耗时
            stage_duration = time.time() - stage_start_time
            self.record_time(stage_name, stage_start_time, stage_duration)

            return success

        except Exception as e:
            self.send_log(f"执行阶段时发生错误: {str(e)}", stage_name)
            return False

    def _execute_inline_script(self, stage: Dict[str, Any], check_termination: Callable = None) -> bool:
        """
        执行内联脚本
        Args:
            stage: 阶段配置信息
            check_termination: 检查是否终止的回调函数
        Returns:
            bool: 执行是否成功
        """
        stage_name = stage.get('name', '未命名阶段')
        try:
            script_content = stage.get('script', '').strip()
            if not script_content:
                self.send_log("脚本内容为空", stage_name)
                return False

            # 创建临时脚本文件
            script_path = self._create_temp_script_file(script_content, stage_name)
            if not script_path:
                return False

            # 脚本执行方法
            success = self._execute_script_unified(script_path, stage_name, check_termination)
            
            return success

        except Exception as e:
            self.send_log(f"执行内联脚本时发生错误: {str(e)}", stage_name)
            return False

    def execute_stages(self, stages: List[Dict[str, Any]], check_termination: Callable = None) -> bool:
        """
        执行所有构建阶段
        Args:
            stages: 阶段配置列表
            check_termination: 检查是否终止的回调函数
        Returns:
            bool: 所有阶段是否都执行成功
        """
        if not stages:
            self.send_log("没有配置构建阶段")
            return False

        for stage in stages:
            if check_termination and check_termination():
                self.send_log("构建已被终止，跳过后续阶段", "Build Stages")
                return False

            stage_name = stage.get('name', '未命名阶段')
            self.send_log(f"开始执行阶段: {stage_name}", "Build Stages")

            # 执行当前阶段
            if not self.execute_stage(stage, check_termination):
                self.send_log(f"阶段 {stage_name} 执行失败", "Build Stages")
                return False

            self.send_log(f"阶段 {stage_name} 执行完成", "Build Stages")

        self.send_log("所有阶段执行完成", "Build Stages")
        return True