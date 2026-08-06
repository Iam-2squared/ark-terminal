import {
  saveCloudRecord,
} from "./cloud-sync-client.js";

import {
  OfflineSyncQueue,
} from "./offline-sync-queue.js";

export const QUEUED_CLOUD_WRITER_VERSION = "queued-cloud-writer-v1";

let sharedQueue = null;

export function getSharedOfflineQueue({
  storage = globalThis.localStorage ?? null,
  sender = saveCloudRecord,
} = {}) {
  if (!sharedQueue) {
    sharedQueue = new OfflineSyncQueue({ storage, sender });
  }
  return sharedQueue;
}

export async function saveCloudRecordOrQueue(
  payload,
  {
    writer = saveCloudRecord,
    queue = getSharedOfflineQueue(),
  } = {},
) {
  try {
    const response = await writer(payload);
    return {
      saved: response?.saved !== false,
      queued: false,
      response,
    };
  } catch (error) {
    const queued = queue.enqueue(payload);
    return {
      saved: false,
      queued: true,
      reason: String(error?.code ?? error?.message ?? "CLOUD_WRITE_FAILED"),
      queueId: queued.queueId,
    };
  }
}

export async function flushSharedOfflineQueue(options = {}) {
  return getSharedOfflineQueue(options).flush();
}

export function resetSharedOfflineQueueForTests() {
  sharedQueue = null;
}

export default saveCloudRecordOrQueue;
