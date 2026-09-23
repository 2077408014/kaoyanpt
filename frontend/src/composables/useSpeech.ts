import { ref } from 'vue'

const speechRate = ref(1)
const speechVolume = ref(1)
const speechPitch = ref(1)
const isSpeaking = ref(false)
const currentUtterance = ref<SpeechSynthesisUtterance | null>(null)

let voices: SpeechSynthesisVoice[] = []

function loadVoices() {
  if ('speechSynthesis' in window) {
    voices = window.speechSynthesis.getVoices()
    window.speechSynthesis.onvoiceschanged = () => {
      voices = window.speechSynthesis.getVoices()
    }
  }
}

loadVoices()

function getChineseVoice(): SpeechSynthesisVoice | null {
  const zhVoices = voices.filter(v => v.lang.startsWith('zh'))
  if (zhVoices.length > 0) return zhVoices[0]
  const enVoices = voices.filter(v => v.lang.startsWith('en'))
  if (enVoices.length > 0) return enVoices[0]
  return voices[0] || null
}

export function useSpeech() {
  function speak(text: string, options?: {
    rate?: number
    volume?: number
    pitch?: number
    lang?: string
  }) {
    if (!('speechSynthesis' in window)) {
      console.warn('浏览器不支持语音合成')
      return
    }

    stop()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.rate = options?.rate ?? speechRate.value
    utterance.volume = options?.volume ?? speechVolume.value
    utterance.pitch = options?.pitch ?? speechPitch.value

    const voice = getChineseVoice()
    if (voice) {
      utterance.voice = voice
      utterance.lang = voice.lang
    } else if (options?.lang) {
      utterance.lang = options.lang
    }

    utterance.onstart = () => {
      isSpeaking.value = true
    }
    utterance.onend = () => {
      isSpeaking.value = false
      currentUtterance.value = null
    }
    utterance.onerror = () => {
      isSpeaking.value = false
      currentUtterance.value = null
    }

    currentUtterance.value = utterance
    window.speechSynthesis.speak(utterance)
  }

  function stop() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel()
      isSpeaking.value = false
      currentUtterance.value = null
    }
  }

  function pause() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.pause()
    }
  }

  function resume() {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.resume()
    }
  }

  function setRate(rate: number) {
    speechRate.value = Math.max(0.5, Math.min(2, rate))
  }

  function setVolume(volume: number) {
    speechVolume.value = Math.max(0, Math.min(1, volume))
  }

  function setPitch(pitch: number) {
    speechPitch.value = Math.max(0, Math.min(2, pitch))
  }

  return {
    speak,
    stop,
    pause,
    resume,
    setRate,
    setVolume,
    setPitch,
    speechRate,
    speechVolume,
    speechPitch,
    isSpeaking,
    voices
  }
}
