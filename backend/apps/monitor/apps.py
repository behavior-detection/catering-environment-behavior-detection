# 文件: apps/monitor/apps.py

from django.apps import AppConfig
import logging
import threading

logger = logging.getLogger(__name__)

# --- 最终单例模式：一个线程安全的、按需初始化的全局实例 ---

# 1. 定义一个全局变量来持有我们的路由器实例，初始为 None
_shared_router = None

# 2. 定义一个线程锁。这能确保即使有多个请求在同一时刻到达，
#    也只有一个请求能执行创建路由器的代码块。
_router_lock = threading.Lock()


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monitor'

    def ready(self):
        # ready() 方法现在被有意地保持简洁。
        # 事实证明，它不是一个可靠的初始化位置。
        # 我们将在第一个API请求到达时，懒加载路由器。
        logger.info("MonitorConfig 已就绪。智能查询路由器将在第一次API请求时初始化。")
        pass


def get_shared_router():
    """
    获取全局共享的路由器实例，如果它不存在，则创建它。
    这个函数现在是单例的唯一管理者，并且是线程安全的。
    """
    global _shared_router

    # 快速路径：如果路由器已经被创建，立即返回它。
    # 99.9% 的请求都会走这条路径。
    if _shared_router is not None:
        return _shared_router

    # 慢速路径（只会发生一次）：路由器还不存在。
    # 我们获取锁，以确保只有一个线程可以创建它。
    with _router_lock:
        # 必须在锁内再次检查，因为可能在等待锁的时候，
        # 另一个线程已经创建了实例。
        if _shared_router is None:
            logger.info("--- 触发全局路由器的按需初始化 ---")
            from .integrated_smart_router import IntelligentQueryRouter

            # 这里的初始化非常快，因为真正的AI模型仍然是由
            # LanguageModelService 懒加载的。
            _shared_router = IntelligentQueryRouter()
            logger.info("✅ 全局智能查询路由器实例已创建。")

    return _shared_router