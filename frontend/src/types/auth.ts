export interface CurrentUser {
  id: number
  username: string
  role: string
}

export interface AdminUser {
  id: number
  username: string
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login_at: string | null
}

export interface AdminUserCreateRequest {
  username: string
  password: string
  role: string
  is_active: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: CurrentUser
}
