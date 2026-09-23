import axios from './axios'

export interface LoginData {
  email: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
  code: string
}

export interface User {
  id: number
  username: string
  email: string
  avatar: string | null
  ai_api_provider: string | null
  ai_api_key: string | null
  ai_api_model: string | null
  ai_api_base_url: string | null
  active_ai_config_id: number | null
  created_at: string
}

export interface AIConfig {
  ai_api_provider?: string
  ai_api_key?: string
  ai_api_base_url?: string
  ai_api_model?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function login(data: LoginData): Promise<TokenResponse> {
  return await axios.post('/auth/login', data)
}

export async function register(data: RegisterData): Promise<User> {
  return await axios.post('/auth/register', data)
}

export async function getMe(): Promise<User> {
  return await axios.get('/auth/me')
}

export async function updateAIConfig(config: AIConfig): Promise<User> {
  return await axios.put('/auth/ai-config', config)
}

export interface ForgotPasswordData {
  email: string
}

export interface ResetPasswordData {
  email: string
  code: string
  new_password: string
}

export async function forgotPassword(data: ForgotPasswordData): Promise<{ message: string }> {
  return await axios.post('/auth/forgot-password', data)
}

export async function sendRegisterCode(data: ForgotPasswordData): Promise<{ message: string }> {
  return await axios.post('/auth/send-verification-code', data)
}

export async function resetPassword(data: ResetPasswordData): Promise<{ message: string }> {
  return await axios.post('/auth/reset-password', data)
}