from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.report import Report, ReportType
from app.schemas.report import ReportResponse, ReportSummary


class CRUDReport(CRUDBase[Report, ReportResponse, ReportSummary]):
    async def get_by_go_getter(
        self,
        db: AsyncSession,
        go_getter_id: int,
        report_type: Optional[ReportType] = None,
        limit: int = 20,
    ) -> Sequence[Report]:
        query = select(Report).where(Report.go_getter_id == go_getter_id)
        if report_type:
            query = query.where(Report.report_type == report_type)
        query = query.order_by(Report.period_start.desc()).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_existing(
        self, db: AsyncSession, go_getter_id: int, report_type: ReportType, period_start: date
    ) -> Optional[Report]:
        result = await db.execute(
            select(Report).where(
                Report.go_getter_id == go_getter_id,
                Report.report_type == report_type,
                Report.period_start == period_start,
            )
        )
        return result.scalar_one_or_none()


crud_report = CRUDReport(Report)
