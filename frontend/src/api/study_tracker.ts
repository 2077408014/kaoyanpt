import axios from './axios'

/**
 * 学习时长跟踪相关 API（独立模块）
 * - heartbeat: 心跳累计学习时长
 * - trackEvent: 记录学习事件（错题/单词/题目）
 * - getTodayStats: 获取今日统计
 */

export interface TodayStudyStats {
  study_date: string
  total_time: number
  words_studied: number
  mistakes_added: number
  questions_completed: number
}

export type StudyEventType = 'mistake_added' | 'word_learned' | 'question_completed'

export async function sendHeartbeat(seconds: number): Promise<TodayStudyStats> {
  return await axios.post('/study/heartbeat', { seconds })
}

export async function trackStudyEvent(
  eventType: StudyEventType,
  count: number = 1
): Promise<TodayStudyStats> {
  return await axios.post('/study/event', { event_type: eventType, count })
}

export async function getTodayStats(): Promise<TodayStudyStats> {
  return await axios.get('/study/today')
}
