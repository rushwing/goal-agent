from pydantic import BaseModel


class AchievementResponse(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    pupil_id: int
    badge_key: str
    badge_name: str
    badge_icon: str
    xp_bonus: int
