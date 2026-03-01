# OpenClaw Plugin — Lessons Learned

A record of non-obvious bugs encountered while integrating the Goal Agent OpenClaw plugin, with root causes and fixes. Reference this before debugging a new plugin issue.

---

## 1. Double-load → 36 tool-name conflicts → gateway crash

**Symptom**: Gateway crashes whenever a Telegram message is sent. Log shows 36 lines of:
```
[plugins] plugin tool name conflict (openclaw-goal-agent): <tool_name>
```

**Root cause**: OpenClaw scans **two** paths for plugins at startup:
- `plugins.load.paths` in `openclaw.json` (our configured source)
- `~/.openclaw/extensions/<id>/` (global extensions directory)

If the plugin is present in both (e.g. after `plugins install --link` creates a symlink/copy in `extensions/`), it loads **twice**. 36 tools registered twice → name conflicts → crash.

**Fix**: Before patching `openclaw.json`, remove both possible extension paths:
```bash
rm -rf "$HOME/.openclaw/extensions/goal-agent"           # legacy name
rm -rf "$HOME/.openclaw/extensions/openclaw-goal-agent"  # copy or --link symlink
```

**Key rule**: A plugin should appear in exactly one of the two scan paths.

---

## 2. `api.registerTool(fn)` → all tools resolve with `name=undefined`

**Symptom**: After restarting, the same 36 conflicts reappear but the tool names are all `undefined`:
```
plugin tool name conflict (openclaw-goal-agent): undefined
```

**Root cause**: `api.registerTool` has two code paths:
- **Function path**: `typeof tool === "function"` → stored as factory, called per-request as `factory(context)`. Our async handler returns a `Promise` (which has `.name = ""` not the tool name). Every tool resolves as `name=undefined`.
- **Object path**: object → stored as `(_ctx) => tool`, so `tool.name` is always correct.

**Fix**: Register as objects, not functions:
```typescript
// WRONG — function path, name becomes undefined at runtime
api.registerTool(async (params) => { ... }, { name: "generate_plan" });

// CORRECT — object path, name is always the string key
api.registerTool({
  name: "generate_plan",
  execute: async (_id, params) => { ... },
});
```

---

## 3. Missing `description` / `parameters` → crash in `pi-coding-agent`

**Symptom**: After fixing the name issue, gateway crashes with:
```
Cannot read properties of undefined (reading 'properties')
```

**Root cause**: `pi-coding-agent` (OpenClaw's embedded LLM layer) accesses `tool.description.trim()` and `tool.parameters.properties` when building the API request. Registering `{ name, execute }` without those fields → `undefined.properties` → crash.

**Fix**: Always include all required fields on the tool object:
```typescript
const EMPTY_SCHEMA = { type: "object" as const, properties: {} };

api.registerTool({
  name:        "generate_plan",
  label:       "generate_plan",        // human-readable; required
  description: "",                     // empty string is valid; undefined is not
  parameters:  EMPTY_SCHEMA,           // must have type + properties; never undefined
  execute:     async (_id, params) => { ... },
});
```

---

## 4. `localhost` resolves to IPv6 `::1` on Linux → ECONNREFUSED

**Symptom**: Tool calls fail with:
```
[tools] generate_plan failed: API error undefined: connect ECONNREFUSED ::1:8000
```

**Root cause**: On Linux (including Raspberry Pi OS), `localhost` resolves to `::1` (IPv6 loopback) first. The goal-agent service listens only on IPv4 (`0.0.0.0`). The connection is refused because nothing is listening on `[::1]:8000`.

**Fix**: Always use `127.0.0.1` (explicit IPv4) instead of `localhost` in `apiBaseUrl`:
```json
{ "apiBaseUrl": "http://127.0.0.1:8000/api/v1" }
```

This applies to `config.json`, `openclaw.json` entry config, and all example URLs in documentation.

---

## 5. Plugin config lives in `api.pluginConfig`, not `process.env.PLUGIN_CONFIG`

**Symptom**: Despite `deploy.sh` patching `apiBaseUrl` in `openclaw.json`, the plugin still uses `localhost` (from the stale fallback `config.json`). Or tools continue failing even after updating `openclaw.json`.

**Root cause**: OpenClaw **does not** inject plugin config as `process.env.PLUGIN_CONFIG`. It passes the entry config (`plugins.entries.<id>.config` from `openclaw.json`) as the `api.pluginConfig` property on the object passed to `plugin.register(api)`. Loading config at module level from `process.env` reads nothing.

All openclaw extension examples confirm this:
```typescript
// extensions/memory-lancedb/index.ts
const cfg = memoryConfigSchema.parse(api.pluginConfig);

// extensions/device-pair/index.ts
const pluginCfg = (api.pluginConfig ?? {}) as DevicePairPluginConfig;
```

**Fix**: Load config **inside** `register(api)`, using `api.pluginConfig` as the primary source:
```typescript
const plugin = {
  register(api) {
    // api.pluginConfig is only available here, not at module load time
    const config = loadConfig(api.pluginConfig);
    const client = createClient(config);
    // ... register tools
  },
};
```

---

## 6. `hmacSecret` must be in the plugin config when `HMAC_SECRET` is set

**Symptom**: Tools reach the server but return 401:
```
[tools] generate_plan failed: API error 401: Invalid request signature
```

**Root cause**: The server enforces HMAC-SHA256 request signing when `HMAC_SECRET` is non-empty in `.env`. The plugin's `client.ts` only signs requests when `config.hmacSecret` is present — but `deploy.sh` wasn't writing `hmacSecret` into `config.json` or `openclaw.json`.

**Fix**: `deploy.sh` reads `HMAC_SECRET` from `.env` (already `source`d) and includes it in both outputs:
```bash
HMAC_SECRET="${HMAC_SECRET:-}"

# config.json
if [[ -n "$HMAC_SECRET" ]]; then
  echo '{ ..., "hmacSecret": "'"${HMAC_SECRET}"'" }' > "$CONFIG_FILE"
fi

# openclaw.json patcher (Python)
if hmac_secret:
    plugin_cfg["hmacSecret"] = hmac_secret
```

The `hmacSecret` in the plugin config must be **identical** to the server's `HMAC_SECRET`. See `app/auth/hmac_auth.py` for the signing algorithm (`{timestamp}:{nonce}:{chat_id}`).

---

## 7. `configSchema` must be in `openclaw.plugin.json`, not the JS export

**Symptom**: OpenClaw refuses to start, logging:
```
Invalid config at ~/.openclaw/openclaw.json:
- plugins.entries.openclaw-goal-agent.config: invalid config: <root>: must NOT have additional properties
Config invalid
```

**Root cause**: OpenClaw validates the entry config (`plugins.entries.<id>.config` in `openclaw.json`) against the `configSchema` field in **`openclaw.plugin.json`** (the manifest JSON file) — not from the JS module export. The validation happens in `loader.ts` at line 624 using `manifestRecord.configSchema`, which is populated by `manifest-registry.ts` reading the manifest file. The JS module isn't even loaded yet at this point.

The load order is:
1. `openclaw.plugin.json` is read → `configSchema` extracted
2. `configSchema` used to validate the entry config in `openclaw.json` → **error raised here**
3. JS module is `require()`d only if step 2 passes

Any field in `openclaw.json` entry config that isn't listed in `openclaw.plugin.json`'s `configSchema.properties` will be rejected.

**Fix**: Add all allowed fields to `openclaw.plugin.json`'s `configSchema`:
```json
{
  "id": "openclaw-goal-agent",
  "configSchema": {
    "type": "object",
    "additionalProperties": false,
    "required": ["apiBaseUrl", "telegramChatId"],
    "properties": {
      "apiBaseUrl":     { "type": "string" },
      "telegramChatId": { "type": "string" },
      "hmacSecret":     { "type": "string" }
    }
  }
}
```

**Note**: Adding `configSchema` to the JS module export (`module.exports = { configSchema, register }`) has no effect on this validation — OpenClaw never reads it from there.

---

## Summary table

| # | Symptom | Root cause | Fix |
|---|---------|-----------|-----|
| 1 | 36 tool-name conflicts on message | Plugin in both `load.paths` AND `extensions/` | `rm -rf extensions/<id>` before patching |
| 2 | 36 conflicts, all names `undefined` | `registerTool(asyncFn)` → function path, name lost | Register as object `{name, execute, ...}` |
| 3 | `Cannot read properties of undefined ('properties')` | Missing `description`/`parameters` on tool object | Add `description: ""`, `parameters: EMPTY_SCHEMA`, `label` |
| 4 | `ECONNREFUSED ::1:8000` | `localhost` → IPv6 on Linux | Use `127.0.0.1` explicitly |
| 5 | Config changes in `openclaw.json` not picked up | Config read from `process.env` (never set) instead of `api.pluginConfig` | Load config inside `register(api)` from `api.pluginConfig` |
| 6 | `401 Invalid request signature` | `hmacSecret` missing from plugin config | Add `HMAC_SECRET` from `.env` to both `config.json` and `openclaw.json` patcher |
| 7 | `Config invalid: must NOT have additional properties` | Field missing from `openclaw.plugin.json` `configSchema` | Add field to `configSchema.properties` in `openclaw.plugin.json` (JS export ignored) |
