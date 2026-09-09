import asyncio
import logging

from app.core.config import settings
from app.database import SessionFactory
from app.services.notification_dispatcher import dispatch_due_notifications


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kaizen.notification_worker")


async def run_worker() -> None:
    logger.info("Worker de notificações iniciado")
    while True:
        try:
            async with SessionFactory() as db:
                sent = await dispatch_due_notifications(db)
                if sent:
                    logger.info("Notificações enviadas: %s", sent)
        except Exception:
            logger.exception("Falha no ciclo de notificações")
        await asyncio.sleep(max(15, settings.notification_worker_interval_seconds))


if __name__ == "__main__":
    asyncio.run(run_worker())
