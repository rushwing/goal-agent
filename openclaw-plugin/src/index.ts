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

// Minimal OpenClaw plugin API shape needed for tool registration.
// registerTool accepts either:
//   - An AnyAgentTool object  → stored as factory = (_ctx) => tool  (OBJECT path)
//   - An OpenClawPluginToolFactory function → stored as-is           (FUNCTION path)
//
// We must use the OBJECT path. When the function path is used, OpenClaw calls
// factory(context) per-request (embedded agent) with OpenClawPluginToolContext
// instead of tool args. Our async handlers then return a Promise (no .name),
// causing all 36 tools to resolve with name=undefined → "tool name conflict"
// spam → gateway crash. Using the object path makes factory = (_ctx) => tool,
// so tool.name is always the correct string.
// Minimal JSON Schema object that satisfies pi-coding-agent's ToolDefinition.
// pi-coding-agent accesses tool.parameters.properties when building the LLM
// API request body, so parameters must never be undefined.
const EMPTY_SCHEMA = { type: "object" as const, properties: {} };

// AnyAgentTool shape expected by OpenClaw's registerTool (object path):
//   name        → tool identifier (no spaces)
//   label       → human-readable label shown in UI
//   description → shown to LLM; empty string is valid
//   parameters  → JSON Schema for the tool's input; MUST have type+properties
//   execute     → (id, params, signal?) => AgentToolResult
interface PluginTool {
  name: string;
  label: string;
  description: string;
  parameters: { type: "object"; properties: Record<string, unknown> };
  execute: (
    _id: string,
    params: Record<string, unknown>
  ) => Promise<{ content: Array<{ type: "text"; text: string }> }>;
}
interface OpenClawPluginApi {
  registerTool: (tool: PluginTool, options?: { name?: string }) => void;
}

const plugin = {
  id: "openclaw-goal-agent",
  name: "Goal Agent",
  description: "AI-powered goal and habit tracking agent tools",
  register(api: OpenClawPluginApi) {
    for (const [name, handler] of Object.entries(allTools)) {
      api.registerTool({
        name,
        label: name,
        description: "",   // empty is valid; avoids undefined.trim() crash
        parameters: EMPTY_SCHEMA,
        execute: async (
          _id: string,
          params: Record<string, unknown>
        ) => {
          const result = await (
            handler as (args: Record<string, unknown>) => Promise<unknown>
          )(params);
          return {
            content: [
              {
                type: "text" as const,
                text:
                  typeof result === "string"
                    ? result
                    : JSON.stringify(result),
              },
            ],
          };
        },
      });
    }
  },
};

// tsconfig uses module:commonjs — use module.exports so the top-level
// `register` key is directly accessible when OpenClaw does require(entry).
// `export default` would compile to exports.default which OpenClaw won't find.
module.exports = plugin;
