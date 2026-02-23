from datetime import date
from typing import Optional
from pydantic import BaseModel
from app.models.report import ReportType


class ReportResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    pupil_id: int
    report_type: ReportType
    period_start: date
    period_end: date
    content_md: str
    tasks_total: int
    tasks_completed: int
    tasks_skipped: int
    xp_earned: int
    github_commit_sha: Optional[str]
    github_file_path: Optional[str]
    sent_to_telegram: bool


class ReportSummary(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    pupil_id: int
    report_type: ReportType
    period_start: date
    period_end: date
    tasks_total: int
    tasks_completed: int
    xp_earned: int
