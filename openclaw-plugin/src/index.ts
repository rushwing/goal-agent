/**
 * OpenClaw plugin entrypoint for Vacation Study Planner.
 *
 * OpenClaw loads this as a CommonJS module and calls exported tool functions.
 * Each tool function receives its arguments and returns a result.
 *
 * Config is injected via PLUGIN_CONFIG environment variable (JSON):
 *   { "apiBaseUrl": "http://pi:8000/api/v1", "telegramChatId": "123456789" }
 */
import { createClient, PluginConfig } from "./client";
import { registerAdminTools } from "./tools/admin.tools";
import { registerPlanTools } from "./tools/plan.tools";
import { registerCheckinTools } from "./tools/checkin.tools";
import { registerReportTools } from "./tools/report.tools";

function loadConfig(): PluginConfig {
  const raw = process.env.PLUGIN_CONFIG;
  if (!raw) {
    throw new Error("PLUGIN_CONFIG environment variable is required");
  }
  try {
    return JSON.parse(raw) as PluginConfig;
  } catch {
    throw new Error("PLUGIN_CONFIG must be valid JSON");
  }
}

const config = loadConfig();
const client = createClient(config);

const adminTools = registerAdminTools(client);
const planTools = registerPlanTools(client);
const checkinTools = registerCheckinTools(client);
const reportTools = registerReportTools(client);

// Export all tools for OpenClaw to discover
module.exports = {
  ...adminTools,
  ...planTools,
  ...checkinTools,
  ...reportTools,
};
