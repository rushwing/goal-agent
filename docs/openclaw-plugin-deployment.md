# OpenClaw 插件部署指南

本文档记录 Goal Agent OpenClaw 插件的完整部署步骤，包括手动修改的内容。

## 前提条件

- Node.js >= 18
- OpenClaw 已安装并配置
- Goal Agent API 可访问

## 快速安装

```bash
cd /path/to/goal-agent
./scripts/install-openclaw-plugin.sh [API_BASE_URL] [TELEGRAM_CHAT_ID]
```

## 手动部署步骤

### 1. 构建插件

```bash
cd openclaw-plugin
npm install
npm run build
```

### 2. 复制到 OpenClaw 扩展目录

```bash
mkdir -p ~/.openclaw/extensions/goal-agent
cp -r openclaw-plugin/dist ~/.openclaw/extensions/goal-agent/
cp openclaw-plugin/openclaw.plugin.json ~/.openclaw/extensions/goal-agent/
cp openclaw-plugin/package.json ~/.openclaw/extensions/goal-agent/
```

### 3. 安装依赖

```bash
cd ~/.openclaw/extensions/goal-agent
npm install axios
```

### 4. 创建插件配置文件

创建 `~/.openclaw/extensions/goal-agent/config.json`:

```json
{
  "apiBaseUrl": "http://192.168.1.100:8000/api/v1",
  "telegramChatId": "YOUR_TELEGRAM_CHAT_ID"
}
```

### 5. 更新 OpenClaw 配置

编辑 `~/.openclaw/openclaw.json`，添加插件配置：

```json
{
  "plugins": {
    "allow": [
      "telegram",
      "whatsapp",
      "openclaw-goal-agent"
    ],
    "entries": {
      "telegram": {
        "enabled": true
      },
      "whatsapp": {
        "enabled": true
      },
      "openclaw-goal-agent": {
        "enabled": true,
        "config": {
          "apiBaseUrl": "http://192.168.1.100:8000/api/v1",
          "telegramChatId": "YOUR_TELEGRAM_CHAT_ID"
        }
      }
    }
  }
}
```

### 6. 重启 OpenClaw

```bash
openclaw gateway restart
```

### 7. 验证安装

```bash
openclaw plugins list | grep goal-agent
```

应显示：`Goal Agent | openclaw-goal-agent | loaded`

## 关键修改记录

### 1. openclaw.plugin.json 修改

- **`config` → `configSchema`**: OpenClaw 要求使用 `configSchema` 字段
- **添加 `id` 字段**: 设置为 `openclaw-goal-agent`
- **使用标准 JSON Schema 格式**:
  ```json
  {
    "type": "object",
    "additionalProperties": false,
    "required": ["apiBaseUrl", "telegramChatId"],
    "properties": { ... }
  }
  ```

### 2. package.json 修改

- **添加 `openclaw` 字段**:
  ```json
  {
    "openclaw": {
      "id": "openclaw-goal-agent",
      "extensions": ["./dist/index.js"]
    }
  }
  ```

### 3. dist/index.js 修改

原代码在模块加载时立即读取 `PLUGIN_CONFIG` 环境变量，但 OpenClaw 在加载时没有注入该变量。修改为：

1. 优先尝试 `PLUGIN_CONFIG` 环境变量
2. 回退到读取 `config.json` 文件
3. 导出符合 OpenClaw 插件接口的对象：
   ```javascript
   const plugin = {
     id: "openclaw-goal-agent",
     name: "Goal Agent",
     description: "...",
     register(api) {
       for (const [name, handler] of Object.entries(allTools)) {
         api.registerTool(handler, { name });
       }
     }
   };
   module.exports = plugin;
   ```

### 4. pyproject.toml 修改

添加 uv 依赖组：
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
]
```

## 故障排除

### 错误: "PLUGIN_CONFIG environment variable is required"

**原因**: OpenClaw 未注入配置环境变量

**解决**: 创建 `~/.openclaw/extensions/goal-agent/config.json` 文件

### 错误: "plugin manifest requires id"

**原因**: `openclaw.plugin.json` 缺少 `id` 字段

**解决**: 添加 `"id": "openclaw-goal-agent"`

### 错误: "plugin manifest requires configSchema"

**原因**: 使用了 `config` 而不是 `configSchema`

**解决**: 将 `config` 重命名为 `configSchema`

### 错误: "missing register/activate export"

**原因**: 插件未导出正确的接口

**解决**: 确保 `index.js` 导出包含 `register(api)` 方法的对象

## 相关文件

- `openclaw-plugin/openclaw.plugin.json` - 插件清单
- `openclaw-plugin/package.json` - NPM 包配置
- `scripts/install-openclaw-plugin.sh` - 安装脚本
- `docs/openclaw-plugin-deployment.md` - 本文档
