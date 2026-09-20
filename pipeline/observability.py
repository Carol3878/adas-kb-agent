"""
先不接LangSmith,用一个简单的装饰器记录每一步耗时和成功/失败,
写进本地log文件。以后真的需要更专业的追踪,再考虑接LangSmith,
接口不用大改,因为这里记录的信息本来就是LangSmith需要的那几项。
"""

import time
import logging
import functools

logging.basicConfig(
    filename="pipeline_observability.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("pipeline")


def track_step(step_name: str):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start
                logger.info(f"step={step_name} status=success elapsed={elapsed:.2f}s")
                return result
            except Exception as e:
                elapsed = time.time() - start
                logger.error(f"step={step_name} status=failed elapsed={elapsed:.2f}s error={e}")
                raise
        return wrapper
    return decorator
