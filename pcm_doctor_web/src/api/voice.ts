import { apiRequest, apiBlob } from './client'

export interface VoiceSegment { index: number; start_ms: number; end_ms: number; text: string }
export interface Symptom { label: string; source_ids: string[] }
export interface VoiceSummary { summary: string; symptoms: Symptom[]; uncertainty: string }
export interface AudioChunk { id: number; index: number; start_ms: number; duration_ms: number; available: boolean }
export interface Recording {
  id: string; sequence: number; created_at: string; expires_at: string; expired: boolean; closed: boolean
  segments: VoiceSegment[]; chunks: AudioChunk[]
}
const base = (id: number) => `/api/cms/llm/encounters/${id}/`
const post = <T>(id: number, action: string, data: object, timeout = 20000) => apiRequest<T>(base(id) + action + '/', {
  method: 'POST', body: JSON.stringify(data),
}, timeout)
export const recordings = (id: number) => apiRequest<Recording[]>(base(id) + 'recordings/')
export const createRecording = (id: number) => post<Recording>(id, 'recordings', { consent: true })
export const recoverRecording = (id: number, recordingId: string) => post(id, 'recover_recording', { recording_id: recordingId })
export const uploadChunk = (id: number, recordingId: string, index: number, audio: string) => post(id, 'audio_chunk', { recording_id: recordingId, index, audio })
export const snapshot = (id: number, recordingId: string, sequence: number, segments: VoiceSegment[], closed = false) => post(id, 'voice_snapshot', { recording_id: recordingId, sequence, segments, closed })
export const previewVoice = (id: number) => post<VoiceSummary>(id, 'voice_preview', {}, 110000)
export const audioBlob = (id: number, chunkId: number) => apiBlob(base(id) + 'audio/' + chunkId + '/')
