#!/bin/bash
# 安装 Goal-Agent 插件到 OpenClaw
# 用法: ./scripts/install-openclaw-plugin.sh [API_BASE_URL] [TELEGRAM_CHAT_ID]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOAL_AGENT_DIR="$(dirname "$SCRIPT_DIR")"
PLUGIN_DIR="$GOAL_AGENT_DIR/openclaw-plugin"
OPENCLAW_EXT_DIR="$HOME/.openclaw/extensions/goal-agent"
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"

# 默认配置值
DEFAULT_API_URL="http://192.168.1.100:8000/api/v1"
DEFAULT_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

# 从命令行参数或环境变量读取
API_BASE_URL="${1:-${GOAL_AGENT_API_URL:-$DEFAULT_API_URL}}"
TELEGRAM_CHAT_ID="${2:-${GOAL_AGENT_CHAT_ID:-$DEFAULT_CHAT_ID}}"

echo "🔧 构建插件..."
cd "$PLUGIN_DIR"
npm install
npm run build

echo ""
echo "📦 安装到 OpenClaw..."
mkdir -p "$OPENCLAW_EXT_DIR"

# 复制必要文件
cp -r dist "$OPENCLAW_EXT_DIR/"
cp openclaw.plugin.json "$OPENCLAW_EXT_DIR/"
cp package.json "$OPENCLAW_EXT_DIR/"

# 创建配置文件
cat > "$OPENCLAW_EXT_DIR/config.json" <<EOF
{
  "apiBaseUrl": "$API_BASE_URL",
  "telegramChatId": "$TELEGRAM_CHAT_ID"
}
EOF

echo ""
echo "⚙️  更新 OpenClaw 配置..."

# 检查并更新 openclaw.json
if [[ -f "$OPENCLAW_CONFIG" ]]; then
    # 使用 Node.js 来安全地更新 JSON
    node <<NODE_SCRIPT
const fs = require('fs');
const path = '$OPENCLAW_CONFIG';
const config = JSON.parse(fs.readFileSync(path, 'utf-8'));

// 确保 plugins 部分存在
if (!config.plugins) {
    config.plugins = { allow: [], entries: {} };
}
if (!config.plugins.allow) {
    config.plugins.allow = [];
}
if (!config.plugins.entries) {
    config.plugins.entries = {};
}

// 添加 goal-agent 到 allow 列表（如果不存在）
if (!config.plugins.allow.includes('openclaw-goal-agent')) {
    config.plugins.allow.push('openclaw-goal-agent');
}

// 添加/更新插件配置
config.plugins.entries['openclaw-goal-agent'] = {
    enabled: true,
    config: {
        apiBaseUrl: '$API_BASE_URL',
        telegramChatId: '$TELEGRAM_CHAT_ID'
    }
};

fs.writeFileSync(path, JSON.stringify(config, null, 2));
console.log('✅ OpenClaw 配置已更新');
NODE_SCRIPT
else
    echo "⚠️  OpenClaw 配置文件不存在: $OPENCLAW_CONFIG"
    echo "   请手动添加以下配置到 openclaw.json:"
    cat <<EOF

  "plugins": {
    "allow": ["openclaw-goal-agent"],
    "entries": {
      "openclaw-goal-agent": {
        "enabled": true,
        "config": {
          "apiBaseUrl": "$API_BASE_URL",
          "telegramChatId": "$TELEGRAM_CHAT_ID"
        }
      }
    }
  }
EOF
fi

echo ""
echo "✅ 安装完成!"
echo ""
echo "📋 配置文件位置:"
echo "   插件配置: $OPENCLAW_EXT_DIR/config.json"
echo "   OpenClaw配置: $OPENCLAW_CONFIG"
echo ""
echo "🚀 请重启 OpenClaw 以加载插件:"
echo "   openclaw gateway restart"
echo ""
echo "📖 验证安装:"
echo "   openclaw plugins list | grep goal-agent"
