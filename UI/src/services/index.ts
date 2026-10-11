/**
 * The service used by the whole UI. Swap `mockService` for a real backend
 * implementation of `KarisService` during integration.
 */
export { mockService as karis, mockControls } from "./mock-service";
export type { KarisService, PipelineStep } from "./karis-service";
export { TranscriptionError } from "./karis-service";
