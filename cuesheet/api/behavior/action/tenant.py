from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from cuesheet.api.infrastructure.database.postgresql.rls import TENANT_SETTING


# #
# action

class Tenant:

    @staticmethod
    async def set_tenant_scope(
        session: AsyncSession,
        *,
        cuesheet_id: UUID
    ):
        await session.execute(
            text(f"SELECT set_config('{TENANT_SETTING}', :cuesheet, true)"),
            {"cuesheet": str(cuesheet_id)},
        )
