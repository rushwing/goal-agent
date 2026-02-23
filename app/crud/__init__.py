from app.crud.pupils import crud_pupil
from app.crud.parents import crud_parent
from app.crud.targets import crud_target
from app.crud.plans import crud_plan
from app.crud.tasks import crud_task
from app.crud.check_ins import crud_check_in
from app.crud.reports import crud_report
from app.crud.achievements import crud_achievement

__all__ = [
    "crud_pupil",
    "crud_parent",
    "crud_target",
    "crud_plan",
    "crud_task",
    "crud_check_in",
    "crud_report",
    "crud_achievement",
]
