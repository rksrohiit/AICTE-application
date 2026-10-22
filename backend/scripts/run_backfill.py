import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.application import Application
from app.services.audit_chain import backfill_existing_audit_logs, verify_audit_chain

async def main():
    async with AsyncSessionLocal() as session:
        updated = await backfill_existing_audit_logs(session)
        print(f"Backfilled {updated} audit records with cryptographic SHA-256 hashes!")

        res = await session.execute(select(Application))
        apps = res.scalars().all()
        for app in apps:
            v = await verify_audit_chain(session, app.id)
            print(f"App {app.id}: Valid={v['is_valid']}, Records={v['total_records']}, Head={v['head_hash'][:12]}...")

if __name__ == "__main__":
    asyncio.run(main())
