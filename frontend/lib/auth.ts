"use client"

const TOKEN_KEY = "ai_novel_token"
const USER_KEY = "ai_novel_user"

let _token: string | null = null
let _user: { user_id: string; username: string } | null = null

export function getToken(): string | null {
  if (_token) return _token
  if (typeof window !== "undefined") {
    _token = localStorage.getItem(TOKEN_KEY)
  }
  return _token
}

export function setToken(token: string) {
  _token = token
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token)
  }
}

export function clearToken() {
  _token = null
  _user = null
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }
}

export function getUser(): { user_id: string; username: string } | null {
  if (_user) return _user
  if (typeof window !== "undefined") {
    const raw = localStorage.getItem(USER_KEY)
    if (raw) {
      try { _user = JSON.parse(raw) } catch { return null }
    }
  }
  return _user
}

export function setUser(user: { user_id: string; username: string }) {
  _user = user
  if (typeof window !== "undefined") {
    localStorage.setItem(USER_KEY, JSON.stringify(user))
  }
}

export function isAuthenticated(): boolean {
  return getToken() !== null
}

export async function login(username: string, password: string) {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
  const res = await fetch(`${BASE_URL}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const body = await res.json()
    throw new Error(body.detail || "登录失败")
  }
  return res.json()
}

export async function register(username: string, password: string) {
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
  const res = await fetch(`${BASE_URL}/api/v1/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  if (!res.ok) {
    const body = await res.json()
    throw new Error(body.detail || "注册失败")
  }
  return res.json()
}

export async function fetchMe(): Promise<{ user_id: string; username: string } | null> {
  const token = getToken()
  if (!token) return null
  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!res.ok) {
      clearToken()
      return null
    }
    return res.json()
  } catch {
    return null
  }
}
