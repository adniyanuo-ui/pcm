import { apiRequest } from './client'

export interface SpeechCredentials {
  token: string
  appkey: string
  gateway: string
  expires_at: string
}

export function getSpeechCredentials(): Promise<SpeechCredentials> {
  return apiRequest<SpeechCredentials>(
    '/api/cms/speech/token/',
    {
      method: 'POST',
      body: '{}',
    },
  )
}
