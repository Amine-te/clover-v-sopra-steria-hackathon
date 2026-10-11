/**
 * In-memory holder for the last device recording. Audio is never persisted
 * and never leaves the device in the demo. Kept outside React state so a
 * Blob does not end up in localStorage.
 */
export interface DeviceRecording {
  blob: Blob;
  url: string;
  durationS: number;
}

let current: DeviceRecording | null = null;

export function setDeviceRecording(r: DeviceRecording | null) {
  if (current && current.url !== r?.url) URL.revokeObjectURL(current.url);
  current = r;
}

export function getDeviceRecording(): DeviceRecording | null {
  return current;
}
