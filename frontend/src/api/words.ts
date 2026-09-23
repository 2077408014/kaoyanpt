import axios from './axios'

export interface Word {
  id: number
  word: string
  phonetic: string | null
  meaning: string
  example_sentence: string | null
  difficulty: number
  frequency: number
  exam_requirement: string
  category?: string
  type?: string
}

export interface UserWord {
  id: number
  word_id: number
  word: string
  phonetic?: string
  meaning?: string
  example_sentence?: string
  mastery_level: string
  next_review_date: string | null
  review_count: number
  correct_count: number
  last_study_date: string | null
  first_study_date: string | null
  last_rating: string | null
  srs_stage: number
}

export interface WordStats {
  total: number
  studied: number
  mastered: number
  today: number
  has_wordbook?: boolean
  review_due?: number
}

export interface StudyPlan {
  daily_word_count: number
  word_category: string | null
  batch_size: number
  study_mode: string
}

export interface TodayWordsResponse {
  review: Word[]
  new: Word[]
  review_count: number
  new_count: number
  total_today: number
}

export interface StudySession {
  current_round: number
  total_rounds: number
  round_queue: RoundQueueItem[]
  round_stats: { known: number; vague: number; unknown: number }
  global_index: number
  total_words_today: number
  study_mode: string
  batch_size: number
  all_word_ids: number[]
  completed_rounds: number
  category: string | null
}

export interface RoundQueueItem {
  wordId: number
  word: string
  phonetic: string | null
  meaning: string
  example_sentence: string | null
  exam_requirement: string
  type: string
  repeatCount: number
}

export async function getWordStats(category?: string): Promise<WordStats> {
  return await axios.get('/words/stats', { params: category ? { category } : {} })
}

export async function getTodayWords(count: number = 20, category?: string): Promise<TodayWordsResponse> {
  return await axios.get('/words/today', { params: { count, category } })
}

export async function getDailyReviewWords(category?: string): Promise<{ words: Word[]; count: number }> {
  return await axios.get('/words/daily-review', { params: { category } })
}

export async function getReviewWordsByRange(timeRange: string = 'today'): Promise<{ words: Word[]; count: number }> {
  return await axios.get('/words/review-words', { params: { time_range: timeRange } })
}

export async function getWordCategories(): Promise<{ categories: string[] }> {
  return await axios.get('/words/categories')
}

export async function getReviewWords(): Promise<UserWord[]> {
  return await axios.get('/words/review')
}

export async function getWordList(params?: {
  page?: number
  page_size?: number
  mastery_level?: string
  keyword?: string
  category?: string
}): Promise<{ total: number; items: UserWord[] }> {
  return await axios.get('/words/list', { params })
}

export async function studyWord(wordId: number, result: string): Promise<UserWord> {
  return await axios.post('/words/study', { word_id: wordId, result })
}

export async function getStudyPlan(): Promise<StudyPlan> {
  return await axios.get('/words/plan')
}

export async function saveStudyPlan(
  dailyWordCount: number,
  wordCategory?: string,
  batchSize?: number,
  studyMode?: string
): Promise<StudyPlan> {
  return await axios.post('/words/plan', {
    daily_word_count: dailyWordCount,
    word_category: wordCategory,
    batch_size: batchSize ?? 20,
    study_mode: studyMode ?? 'mixed'
  })
}

export async function getStudySession(): Promise<StudySession | null> {
  const res: any = await axios.get('/words/session')
  return res && Object.keys(res).length > 0 ? (res as StudySession) : null
}

export async function saveStudySession(session: StudySession): Promise<StudySession> {
  return await axios.post('/words/session', session)
}

export async function clearStudySession(): Promise<{ success: boolean }> {
  return await axios.delete('/words/session')
}

export interface UploadWordbookResult {
  success: boolean
  message: string
  imported_count?: number
  category?: string
}

export async function uploadWordbook(file: File, category?: string): Promise<UploadWordbookResult> {
  const formData = new FormData()
  formData.append('file', file)
  if (category) {
    formData.append('category', category)
  }
  return await axios.post('/words/upload-wordbook', formData)
}
