/**
 * Typed axios HTTP client for the Goal Agent API.
 * Injects X-Telegram-Chat-Id from plugin config on every request.
 *
 * HMAC signing (Issue #3):
 * When `hmacSecret` is present in PluginConfig the client automatically adds
 * three extra headers to every outgoing request:
 *   X-Request-Timestamp  – unix epoch seconds
 *   X-Nonce              – cryptographically random UUID v4
 *   X-Signature          – HMAC-SHA256(secret, "{ts}:{nonce}:{chat_id}") hex
 *
 * Old deployments that do not set `hmacSecret` continue to work in dev mode
 * (the server checks HMAC_SECRET and skips verification when it is empty).
 */
import { createHmac, randomUUID } from "crypto";
import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";

export interface PluginConfig {
  apiBaseUrl: string;
  telegramChatId: string;
  /** Optional shared secret for HMAC-signed requests (Issue #3). */
  hmacSecret?: string;
  /**
   * Optional Telegram Chat ID of the go_getter (child/student).
   * When set, go_getter-facing tools (check-ins, progress) will use this
   * chat ID instead of telegramChatId so role-based auth resolves correctly.
   * Register the go_getter in the DB first via add_go_getter with this chat ID.
   */
  goGetterChatId?: string;
}

function buildHmacHeaders(
  secret: string,
  chatId: string
): Record<string, string> {
  const timestamp = String(Math.floor(Date.now() / 1000));
  const nonce = randomUUID();
  const message = `${timestamp}:${nonce}:${chatId}`;
  const signature = createHmac("sha256", secret)
    .update(message)
    .digest("hex");
  return {
    "X-Request-Timestamp": timestamp,
    "X-Nonce": nonce,
    "X-Signature": signature,
  };
}

export function createClient(config: PluginConfig): AxiosInstance {
  const instance = axios.create({
    baseURL: config.apiBaseUrl,
    timeout: 60_000, // 60s for LLM-heavy calls
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Chat-Id": config.telegramChatId,
    },
  });

  // When hmacSecret is configured, inject signature headers on every request
  if (config.hmacSecret) {
    const secret = config.hmacSecret;
    const chatId = config.telegramChatId;
    instance.interceptors.request.use(
      (cfg: InternalAxiosRequestConfig) => {
        const hmacHeaders = buildHmacHeaders(secret, chatId);
        cfg.headers = cfg.headers ?? {};
        Object.assign(cfg.headers, hmacHeaders);
        return cfg;
      }
    );
  }

  // Log errors but don't throw – let callers handle HTTP status codes
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail ?? error.message;
      const msg = `API error ${status}: ${detail}`;
      return Promise.reject(new Error(msg));
    }
  );

  return instance;
}

/**
 * Create an axios client scoped to the go_getter's chat ID.
 *
 * Uses `config.goGetterChatId` when present, falling back to `telegramChatId`.
 * HMAC headers are signed with whichever chat ID is used so server-side
 * verification passes correctly.
 */
export function createGoGetterClient(config: PluginConfig): AxiosInstance {
  const chatId = config.goGetterChatId ?? config.telegramChatId;

  const instance = axios.create({
    baseURL: config.apiBaseUrl,
    timeout: 60_000,
    headers: {
      "Content-Type": "application/json",
      "X-Telegram-Chat-Id": chatId,
    },
  });

  if (config.hmacSecret) {
    const secret = config.hmacSecret;
    instance.interceptors.request.use(
      (cfg: InternalAxiosRequestConfig) => {
        const hmacHeaders = buildHmacHeaders(secret, chatId);
        cfg.headers = cfg.headers ?? {};
        Object.assign(cfg.headers, hmacHeaders);
        return cfg;
      }
    );
  }

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const status = error?.response?.status;
      const detail = error?.response?.data?.detail ?? error.message;
      return Promise.reject(new Error(`API error ${status}: ${detail}`));
    }
  );

  return instance;
}
