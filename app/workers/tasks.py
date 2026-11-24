import asyncio
from uuid import UUID
from app.db.database import connect, disconnect, init_db, pool
from app.ingestion.pipeline import ingest
from app.core.config import settings
from app.core.logging import configure_logging, logger

async def process_one():
    async with pool().acquire() as conn:
        async with conn.transaction():
            job = await conn.fetchrow("""SELECT id,document_id,version FROM ingestion_jobs
                WHERE status='queued' ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1""")
            if not job:
                return False
            await conn.execute("""UPDATE ingestion_jobs SET status='running',attempts=attempts+1,
                updated_at=now() WHERE id=$1""", job["id"])
    try:
        await ingest(str(job["document_id"]), job["version"])
        async with pool().acquire() as conn:
            await conn.execute("UPDATE ingestion_jobs SET status='done',updated_at=now() WHERE id=$1", job["id"])
    except Exception as exc:
        logger.exception("ingestion_failed", job_id=job["id"])
        async with pool().acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE ingestion_jobs SET status='failed',error=$2,updated_at=now() WHERE id=$1",
                                   job["id"], str(exc)[:1000])
                await conn.execute("""UPDATE documents SET status='failed',error=$3,updated_at=now()
                    WHERE id=$1 AND version=$2""", job["document_id"], job["version"], str(exc)[:1000])
    return True

async def main():
    configure_logging()
    await connect()
    try:
        await init_db()
        logger.info("worker_started")
        while True:
            if not await process_one():
                await asyncio.sleep(settings.worker_poll_seconds)
    finally:
        await disconnect()

if __name__ == "__main__":
    asyncio.run(main())
