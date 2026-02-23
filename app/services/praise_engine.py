"""Praise engine: LLM-generated encouragement with offline template fallback."""
import logging
import random
from typing import Optional

from app.services import llm_service

logger = logging.getLogger(__name__)

# Offline templates indexed by (mood_bucket, streak_bucket)
# mood_bucket: "low" (1-2), "mid" (3), "high" (4-5)
# streak_bucket: "start" (1-2), "building" (3-6), "fire" (7-13), "legend" (14+)

TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("low", "start"): [
        "Not every day feels great, but showing up matters. You did it! 💪",
        "Even on tough days, you pushed through. That's real strength!",
        "It's okay to not feel 100% — you still got it done. Well done!",
    ],
    ("low", "building"): [
        "Three days in and still going, even when it's hard. Respect! 🔥",
        "Feeling down but keeping your streak alive? That's willpower!",
        "Rough day, but you kept going. Your future self will thank you.",
    ],
    ("low", "fire"): [
        "A whole week of showing up, even on rough days. You're a warrior! 🦁",
        "Seven+ days and still here — that's the mark of a true scholar.",
        "Even when energy is low, your consistency is sky-high. Amazing!",
    ],
    ("low", "legend"): [
        "Two weeks of daily study — even feeling tired, you keep going. Legendary! 👑",
        "Your two-week streak through thick and thin is extraordinary!",
        "Fourteen+ days! Not even bad moods can stop you. You're unstoppable!",
    ],
    ("mid", "start"): [
        "Solid start! Keep this energy going — big things are ahead. ⭐",
        "Day by day, step by step. You're building something great!",
        "Nice work today! Every session counts toward your goal.",
    ],
    ("mid", "building"): [
        "Look at you, keeping the streak alive! Day {streak} — keep it up! 🔥",
        "You're building a study habit that'll stick. Keep going!",
        "Consistent effort leads to amazing results. You're on the right track!",
    ],
    ("mid", "fire"): [
        "A full week of study? That's seriously impressive! 🦁",
        "Seven days of showing up — your brain is leveling up big time!",
        "One week in — you've got momentum now. Don't stop!",
    ],
    ("mid", "legend"): [
        "Two weeks of daily study! You're in the zone now. Keep it rolling! 🏆",
        "Fourteen days strong — you're proof that habits change everything.",
        "You've hit the two-week mark! This is where learning really accelerates.",
    ],
    ("high", "start"): [
        "What a great start! Your enthusiasm is contagious. Keep shining! 🌟",
        "Look at that energy! Day one down, many more to come!",
        "Fantastic mood for studying — that kind of vibe leads to real results!",
    ],
    ("high", "building"): [
        "You're loving it AND staying consistent? Superstar energy! ⭐🔥",
        "Great mood + great streak = great learning. You're crushing it!",
        "Day {streak} and you're still fired up! That's the spirit we love to see!",
    ],
    ("high", "fire"): [
        "A week of study AND high spirits? You're on fire! 🦁🔥",
        "Seven days of amazing mood and consistent work. You're unstoppable!",
        "One week in, feeling great — this is what peak study mode looks like!",
    ],
    ("high", "legend"): [
        "Two weeks of joy and dedication. You're a true champion! 👑🏆",
        "Fourteen days of amazing work AND loving every bit of it? Incredible!",
        "Your two-week streak with top spirits is truly inspirational. Keep soaring!",
    ],
}


def _mood_bucket(mood: int) -> str:
    if mood <= 2:
        return "low"
    if mood == 3:
        return "mid"
    return "high"


def _streak_bucket(streak: int) -> str:
    if streak <= 2:
        return "start"
    if streak <= 6:
        return "building"
    if streak <= 13:
        return "fire"
    return "legend"


def get_offline_praise(mood_score: int, streak: int) -> str:
    mb = _mood_bucket(mood_score)
    sb = _streak_bucket(streak)
    templates = TEMPLATES.get((mb, sb), TEMPLATES[("mid", "start")])
    template = random.choice(templates)
    return template.format(streak=streak)


async def generate_praise(
    display_name: str,
    task_title: str,
    mood_score: int,
    streak: int,
    grade: str,
    badges_earned: Optional[list[str]] = None,
) -> str:
    """
    Generate an age-appropriate encouraging message.
    Falls back to offline templates if LLM is unavailable.
    """
    badge_text = ""
    if badges_earned:
        badge_text = f" They also just earned these badges: {', '.join(badges_earned)}!"

    system = (
        "You are an enthusiastic, age-appropriate study coach for children and teenagers. "
        "Write 2-3 sentences of warm, specific encouragement in a friendly, energetic tone. "
        "Use simple language appropriate for the grade level. No markdown formatting."
    )
    user = (
        f"Student name: {display_name}\n"
        f"Grade: {grade}\n"
        f"Task just completed: {task_title}\n"
        f"Mood score (1-5): {mood_score}\n"
        f"Current study streak: {streak} day(s)\n"
        f"{badge_text}\n\n"
        f"Write a short, enthusiastic encouragement message for this student."
    )

    try:
        content, _, _ = await llm_service.chat_complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.9,
            max_tokens=200,
        )
        return content.strip()
    except Exception as exc:
        logger.warning("LLM praise generation failed, using offline template: %s", exc)
        return get_offline_praise(mood_score, streak)
