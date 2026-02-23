/**
 * Typed axios HTTP client for the Study Planner API.
 * Injects X-Telegram-Chat-Id from plugin config on every request.
 */
import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

export interface PluginConfig {
  apiBaseUrl: string;
  telegramChatId: string;
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
