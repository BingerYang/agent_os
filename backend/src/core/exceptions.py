class AgentOSError(Exception):
    """平台基础异常"""
    status_code: int = 500
    error_code: int = 50001
    message: str = "服务器内部错误"

    def __init__(self, message: str | None = None):
        super().__init__(message or self.message)
        self.message = message or self.message


class PreCheckRejected(AgentOSError):
    """前置检测拦截"""
    status_code = 403
    error_code = 40301
    message = "您的请求包含不当内容，已被系统拦截"


class PostCheckRejected(AgentOSError):
    """后置检测拦截"""
    status_code = 403
    error_code = 40302
    message = "系统检测到输出内容不合规，已拦截"


class SubAgentTimeout(AgentOSError):
    """子 Agent 响应超时"""
    status_code = 508
    error_code = 50801
    message = "子 Agent 响应超时，部分功能不可用"


class ToolNotReachable(AgentOSError):
    """工具服务不可达"""
    status_code = 502
    error_code = 50201
    message = "工具服务不可达，请检查工具配置"


class ResourceConflict(AgentOSError):
    """资源冲突（如名称重复）"""
    status_code = 409
    error_code = 40901
    message = "资源冲突，请检查是否存在重名资源"


class ResourceNotFound(AgentOSError):
    """资源不存在"""
    status_code = 404
    error_code = 40401
    message = "资源不存在"


class BusinessValidationError(AgentOSError):
    """业务逻辑校验失败"""
    status_code = 422
    error_code = 42201
    message = "业务逻辑校验失败"
