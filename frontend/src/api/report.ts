import axios from './axios'

export interface StudyReport {
  period: string
  start_date: string
  end_date: string
  word_stats: {
    total_words: number
    mastered_count: number
    learned_this_period: number
    today_review: number
    mastery_rate: number
  }
  mistake_stats: {
    total_mistakes: number
    added_this_period: number
    mastered_mistakes: number
    today_review: number
    mastery_rate: number
    by_subject: { subject: string; count: number }[]
  }
  recommendation_stats: {
    total_recommendations: number
    completed_this_period: number
    total_completed: number
    completion_rate: number
    success_rate: number
  }
  overall_stats: {
    total_study_days: number
    avg_daily_time: number
  }
}

export interface DailyStats {
  date: string
  total_time: number
  words_studied: number
  mistakes_added: number
  questions_completed: number
}

export async function getStudyReport(period: string = 'week'): Promise<StudyReport> {
  return await axios.get('/report/study', { params: { period } })
}

export async function getWeeklyTrend(): Promise<DailyStats[]> {
  return await axios.get('/report/weekly-trend')
}