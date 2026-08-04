export const PAPER_ORDER_AUDIT_LOG_V1_VERSION =
  "paper-order-audit-log-v1";

const DEFAULT_STORAGE_KEY =
  "ark.paperOrderAuditLog.v1";

function storageAvailable(storage) {
  return Boolean(storage && typeof storage.getItem === "function" && typeof storage.setItem === "function");
}

export class PaperOrderAuditLogV1 {
  constructor({
    storage = globalThis.localStorage,
    storageKey = DEFAULT_STORAGE_KEY,
    maxRecords = 5000,
  } = {}) {
    this.storage = storage;
    this.storageKey = storageKey;
    this.maxRecords = Math.max(1, Number(maxRecords) || 5000);
    this.records = this.#load();
  }

  append({
    type,
    data = {},
    timestamp = new Date().toISOString(),
    mode = null,
  } = {}) {
    const record = {
      id: globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      version: PAPER_ORDER_AUDIT_LOG_V1_VERSION,
      type: String(type ?? "UNKNOWN"),
      mode,
      timestamp: new Date(timestamp).toISOString(),
      data: structuredClone(data),
    };

    this.records.push(record);
    this.records = this.records.slice(-this.maxRecords);
    this.#persist();
    return structuredClone(record);
  }

  getRecords() {
    return structuredClone(this.records);
  }

  clear() {
    this.records = [];
    this.#persist();
  }

  #load() {
    if (!storageAvailable(this.storage)) return [];

    try {
      const parsed = JSON.parse(this.storage.getItem(this.storageKey));
      return Array.isArray(parsed) ? parsed : [];
    }
    catch {
      return [];
    }
  }

  #persist() {
    if (!storageAvailable(this.storage)) return;
    this.storage.setItem(this.storageKey, JSON.stringify(this.records));
  }
}

export default PaperOrderAuditLogV1;
