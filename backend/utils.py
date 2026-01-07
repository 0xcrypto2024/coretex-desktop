import asyncio
import logging
import functools

logger = logging.getLogger(__name__)

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    """
    Decorator to retry an async function with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        logger.error(f"Function {func.__name__} failed after {retries} retries. Error: {e}")
                        raise e
                    
                    wait = (backoff_in_seconds * 2 ** x)
                    logger.warning(f"Function {func.__name__} failed with {e}. Retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    x += 1
        return wrapper
    return decorator
