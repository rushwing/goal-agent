/**
 * OpenClaw plugin entrypoint for Goal Agent.
 *
 * OpenClaw loads this as a CommonJS module and calls exported tool functions.
 * Each tool function receives its arguments and returns a result.
 *
 * Config is injected via PLUGIN_CONFIG environment variable (JSON):
 *   { "apiBaseUrl": "http://pi:8000/api/v1", "telegramChatId": "123456789" }
 *
 * If PLUGIN_CONFIG is not set, falls back to reading config.json from the
 * plugin directory.
 */
import * as fs from "fs";
import * as path from "path";
import { createClient, PluginConfig } from "./client";
import { registerAdminTools } from "./tools/admin.tools";
import { registerPlanTools } from "./tools/plan.tools";
import { registerCheckinTools } from "./tools/checkin.tools";
import { registerReportTools } from "./tools/report.tools";
import { registerWizardTools } from "./tools/wizard.tools";
import { registerTracksTools } from "./tools/tracks.tools";

function loadConfig(): PluginConfig {
  // First try PLUGIN_CONFIG env var (injected by OpenClaw)
  const raw = process.env.PLUGIN_CONFIG;
  if (raw) {
    try {
      return JSON.parse(raw) as PluginConfig;
    } catch {
      throw new Error("PLUGIN_CONFIG must be valid JSON");
    }
  }

  // Fallback: try to read from config.json in plugin directory
  const configPath = path.join(__dirname, "..", "config.json");
  if (fs.existsSync(configPath)) {
    try {
      const configData = fs.readFileSync(configPath, "utf-8");
      return JSON.parse(configData) as PluginConfig;
    } catch (e) {
      throw new Error(`Failed to read config.json: ${e}`);
    }
  }

  throw new Error(
    "PLUGIN_CONFIG environment variable is required or config.json must exist"
  );
}

const config = loadConfig();
const client = createClient(config);

const adminTools = registerAdminTools(client);
const planTools = registerPlanTools(client);
const checkinTools = registerCheckinTools(client);
const reportTools = registerReportTools(client);
const wizardTools = registerWizardTools(client);
const tracksTools = registerTracksTools(client);

// Combine all tools
const allTools = {
  ...adminTools,
  ...planTools,
  ...checkinTools,
  ...reportTools,
  ...wizardTools,
  ...tracksTools,
};

// OpenClaw plugin interface
interface OpenClawPluginApi {
  registerTool: (handler: Function, options: { name: string }) => void;
}

const plugin = {
  id: "openclaw-goal-agent",
  name: "Goal Agent",
  description: "AI-powered goal and habit tracking agent tools",
  register(api: OpenClawPluginApi) {
    // Register all tools
    for (const [name, handler] of Object.entries(allTools)) {
      api.registerTool(handler as Function, { name });
    }
  },
};

// tsconfig uses module:commonjs — use module.exports so the top-level
// `register` key is directly accessible when OpenClaw does require(entry).
// `export default` would compile to exports.default which OpenClaw won't find.
module.exports = plugin;
