import json
import logging
import gitlab
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from ..models import Project, BuildTask, GitlabTokenCredential
from ..utils.auth import jwt_auth_required

logger = logging.getLogger('apps')

def get_gitlab_client(repository, git_token=None):
    """获取GitLab客户端"""
    try:
        if not git_token:
            # 获取第一个可用的GitLab Token凭证
            credential = GitlabTokenCredential.objects.first()
            if not credential:
                raise ValueError('未找到GitLab Token凭证')
            git_token = credential.token

        # 从仓库地址中提取GitLab实例URL
        repository_parts = repository.split('/')
        gitlab_url = '/'.join(repository_parts[:3])  # 获取到域名部分
        if not gitlab_url.startswith('http'):
            gitlab_url = f'http://{gitlab_url}'

        # 创建GitLab客户端
        gl = gitlab.Gitlab(
            url=gitlab_url,
            private_token=git_token
        )
        gl.auth()
        return gl
    except Exception as e:
        logger.error(f'获取GitLab客户端失败: {str(e)}', exc_info=True)
        raise

def get_gitlab_project(repository, git_token=None):
    """获取GitLab项目"""
    try:
        gl = get_gitlab_client(repository, git_token)
        repository_parts = repository.split('/')
        project_path = '/'.join(repository_parts[3:])  # 获取group/project部分
        project_path = project_path.replace('.git', '')
        
        # 对项目路径进行URL编码
        import urllib.parse
        encoded_path = urllib.parse.quote(project_path, safe='')
        
        try:
            # 使用URL编码的路径
            return gl.projects.get(encoded_path)
        except gitlab.exceptions.GitlabGetError:
            # 失败，通过搜索项目名称获取项目id
            projects = gl.projects.list(search=project_path.split('/')[-1])
            for project in projects:
                if project.path_with_namespace == project_path:
                    return gl.projects.get(project.id)
            raise gitlab.exceptions.GitlabGetError(f"Project {project_path} not found")
    except Exception as e:
        logger.error(f'获取GitLab项目失败: {str(e)}', exc_info=True)
        raise

@method_decorator(csrf_exempt, name='dispatch')
class GitlabBranchView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取Git分支列表"""
        try:
            task_id = request.GET.get('task_id')
            if not task_id:
                return JsonResponse({
                    'code': 400,
                    'message': '缺少任务ID'
                })

            # 获取任务信息
            try:
                task = BuildTask.objects.select_related('project', 'git_token').get(task_id=task_id)
            except BuildTask.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '任务不存在'
                })

            if not task.project or not task.project.repository:
                return JsonResponse({
                    'code': 400,
                    'message': '任务未配置Git仓库'
                })

            # 获取GitLab项目
            gitlab_project = get_gitlab_project(
                task.project.repository,
                task.git_token.token if task.git_token else None
            )
            
            # 获取分支列表
            branches = gitlab_project.branches.list(all=True)
            branch_list = []
            for branch in branches:
                branch_list.append({
                    'name': branch.name,
                    'protected': branch.protected,
                    'merged': branch.merged,
                    'default': branch.default,
                    'commit': {
                        'id': branch.commit['id'],
                        'title': branch.commit['title'],
                        'author_name': branch.commit['author_name'],
                        'authored_date': branch.commit['authored_date'],
                    }
                })

            return JsonResponse({
                'code': 200,
                'message': '获取分支列表成功',
                'data': branch_list
            })
        except Exception as e:
            logger.error(f'获取分支列表失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class GitlabCommitView(View):
    @method_decorator(jwt_auth_required)
    def get(self, request):
        """获取Git提交记录"""
        try:
            task_id = request.GET.get('task_id')
            branch = request.GET.get('branch')

            if not all([task_id, branch]):
                return JsonResponse({
                    'code': 400,
                    'message': '缺少必要参数'
                })

            # 获取任务信息
            try:
                task = BuildTask.objects.select_related('project', 'git_token').get(task_id=task_id)
            except BuildTask.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '任务不存在'
                })

            if not task.project or not task.project.repository:
                return JsonResponse({
                    'code': 400,
                    'message': '任务未配置Git仓库'
                })

            # 获取GitLab项目
            gitlab_project = get_gitlab_project(
                task.project.repository,
                task.git_token.token if task.git_token else None
            )
            
            # 获取最近的提交记录
            commits = gitlab_project.commits.list(
                ref_name=branch,
                all=False,
                per_page=20,  # 增加返回数量
                order_by='created_at'
            )

            commit_list = []
            for commit in commits:
                commit_list.append({
                    'id': commit.id,
                    'short_id': commit.short_id,
                    'title': commit.title,
                    'message': commit.message,
                    'author_name': commit.author_name,
                    'author_email': commit.author_email,
                    'authored_date': commit.authored_date,
                    'created_at': commit.created_at,
                    'web_url': commit.web_url
                })

            return JsonResponse({
                'code': 200,
                'message': '获取提交记录成功',
                'data': commit_list
            })
        except Exception as e:
            logger.error(f'获取提交记录失败: {str(e)}', exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'服务器错误: {str(e)}'
            }) 