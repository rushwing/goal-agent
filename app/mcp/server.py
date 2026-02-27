"""FastMCP server instance – mounted inside FastAPI."""

from fastmcp import FastMCP

mcp = FastMCP(
    name="GoalAgent",
    instructions=(
        "Goal Agent tools for managing go getters, generating AI study plans, "
        "tracking daily task check-ins, and producing progress reports. "
        "All tools require X-Telegram-Chat-Id header for role-based access control."
    ),
)

# Import tool modules to register @mcp.tool decorators
from app.mcp.tools import (
    admin_tools,
    plan_tools,
    checkin_tools,
    report_tools,
    wizard_tools,
    tracks_tools,
)  # noqa: E402, F401
