import asyncio
import logging
import uvicorn
# Load Config & Env FIRST
from config import API_ID, API_HASH

# Fix for Pyrogram import in Python 3.14+ (requires event loop for sync wrapper)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from listener import start_listener, tm, app as client_app, intelligence_agent, memory_manager
import server
import pyrogram

from config import CONFIG_DIR
LOG_FILE = CONFIG_DIR / "cortex.log"

# Configure Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logging.getLogger("uvicorn.access").setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Logging initialized. Writing to: {LOG_FILE}")

async def on_task_done(summary: str):
    """Callback when a task is marked done via the Web UI."""
    try:
        if client_app.is_connected:
            await client_app.send_message("me", f"✅ **Task Completed**\n_{summary}_")
    except Exception as e:
        logger.error(f"Failed to send completion notification: {e}")

async def run_server():
    """Runs the FastAPI server."""
    # Install handlers=False to let asyncio handling signals
    config = uvicorn.Config(server.app, host="0.0.0.0", port=8000, log_level="warning")
    server_instance = uvicorn.Server(config)
    # Hack to allow uvicorn to be cancelled quickly
    server_instance.install_signal_handlers = lambda: None
    await server_instance.serve()

async def main():
    is_setup_mode = not (API_ID and API_HASH)
    
    # Dependency Injection
    server.task_manager = tm
    server.notification_callback = on_task_done

    if is_setup_mode:
        logger.warning("Agent not configured. Starting in SETUP MODE.")
        # Only run server
        server_task = asyncio.create_task(run_server())
        try:
            while True: await asyncio.sleep(3600)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            server_task.cancel()
            return

    logger.info("Starting Telegram Intelligence Agent (Full Mode)...")
    
    # 1. Start Telegram Client FIRST
    await start_listener()
    
    logger.info("Telegram Client Connected.")
    logger.info("Starting Web Dashboard at http://localhost:8000...")

    # 2. Run Server as background task
    server_task = asyncio.create_task(run_server())

    # 3. Start Learning Service (Background)
    from learning_service import LearningService
    rec_service = LearningService(intelligence_agent, memory_manager, tm)
    learning_task = asyncio.create_task(rec_service.start_scheduler())

    # 3. Idle until signal
    import signal
    stop_event = asyncio.Event()

    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}. Stopping...")
        # Schedule the stop event in the loop
        asyncio.create_task(set_stop())

    async def set_stop():
        stop_event.set()

    # Register signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(set_stop()))
        except NotImplementedError:
            # Windows or fallback
            signal.signal(sig, handle_signal)

    logger.info("Service is RUNNING. Waiting for stop signal...")
    try:
        await stop_event.wait()
    except asyncio.CancelledError:
        logger.info("Main task cancelled.")
    finally:
        logger.info("Shutting down services...")
        
        # Stop Server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        # Stop Learning Service
        learning_task.cancel()
        try:
            await learning_task
        except asyncio.CancelledError:
            pass
            
        logger.info("Stopping Telegram Client...")
        if client_app.is_connected:
            try:
                # Force timeout on stop to prevent hanging
                await asyncio.wait_for(client_app.stop(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Telegram Client stop timed out. Forcing exit.")
        logger.info("Telegram Client Stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fatal error: {e}")
