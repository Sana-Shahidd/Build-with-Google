export const MAX_RECORD_S = 60
export const MIN_RECORD_S = 1

const MIME_CANDIDATES = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg']

export type Recording = { blob: Blob; seconds: number }

export type Recorder = {
  /** Stop and return the audio, or null when cancelled or shorter than MIN_RECORD_S. */
  stop: (cancel?: boolean) => Promise<Recording | null>
}

/** Start recording with MediaRecorder (docs/02 F-02). Throws if the microphone is unavailable. */
export async function startRecording(onTick: (seconds: number) => void): Promise<Recorder> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
  const mimeType = MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m))
  const media = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)
  const chunks: Blob[] = []
  const startedAt = Date.now()
  media.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data)
  }
  const timer = window.setInterval(() => {
    const s = Math.floor((Date.now() - startedAt) / 1000)
    onTick(s)
    if (s >= MAX_RECORD_S && media.state === 'recording') media.stop()
  }, 250)
  const finished = new Promise<void>((resolve) => {
    media.onstop = () => resolve()
  })
  media.start()

  return {
    stop: async (cancel = false) => {
      window.clearInterval(timer)
      if (media.state === 'recording') media.stop()
      await finished
      stream.getTracks().forEach((t) => t.stop())
      const seconds = (Date.now() - startedAt) / 1000
      if (cancel || seconds < MIN_RECORD_S) return null
      return { blob: new Blob(chunks, { type: media.mimeType }), seconds }
    },
  }
}

export function extensionFor(mime: string): string {
  if (mime.includes('mp4')) return 'mp4'
  if (mime.includes('ogg')) return 'ogg'
  return 'webm'
}
