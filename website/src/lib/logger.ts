/** Structured logger — emits JSON in production, readable format in development. */

const isProd = process.env.NODE_ENV === "production";

type LogLevel = "info" | "warn" | "error";

function log(level: LogLevel, message: string, data?: Record<string, unknown>) {
  if (isProd) {
    const entry = {
      time: new Date().toISOString(),
      level,
      message,
      ...data,
    };
    // eslint-disable-next-line no-console
    console[level](JSON.stringify(entry));
  } else {
    const prefix = `[${level.toUpperCase()}]`;
    if (data) {
      // eslint-disable-next-line no-console
      console[level](prefix, message, data);
    } else {
      // eslint-disable-next-line no-console
      console[level](prefix, message);
    }
  }
}

export const logger = {
  info: (message: string, data?: Record<string, unknown>) =>
    log("info", message, data),
  warn: (message: string, data?: Record<string, unknown>) =>
    log("warn", message, data),
  error: (message: string, data?: Record<string, unknown>) =>
    log("error", message, data),
};
