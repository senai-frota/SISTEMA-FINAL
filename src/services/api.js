import axios from 'axios'
import { clientFormFactor } from '../utils/device'

/**
 * Resolve a URL base da API conforme o ambiente de execução.
 *
 * Prioridade:
 * 1. VITE_API_URL (produção / override explícito)
 * 2. localhost / 127.0.0.1 → http://localhost:8000/api
 * 3. acesso pela rede (IP/hostname) → mesmo host da página, porta 8000 + /api
 */
export function resolveApiBaseUrl() {
  const fromEnv = (import.meta.env.VITE_API_URL || '').trim()
  if (fromEnv) {
    return fromEnv.replace(/\/$/, '')
  }

  if (typeof window === 'undefined') {
    return 'http://localhost:8000/api'
  }

  const { protocol, hostname } = window.location
  const isLocalHost =
    hostname === 'localhost' ||
    hostname === '127.0.0.1' ||
    hostname === '[::1]'

  if (isLocalHost) {
    return 'http://localhost:8000/api'
  }

  return `${protocol}//${hostname}:8000/api`
}

export const API_BASE_URL = resolveApiBaseUrl()
export const MEDIA_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '')

const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const access = localStorage.getItem('access_token')
  if (access) {
    config.headers.Authorization = `Bearer ${access}`
  }
  config.headers['X-Client-Form-Factor'] = clientFormFactor()
  return config
})

let isRefreshing = false
let queue = []

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  queue = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthRoute = originalRequest?.url?.includes('/usuarios/login/')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthRoute) {
      const refresh = localStorage.getItem('refresh_token')
      if (!refresh) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject })
        }).then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`
          return api(originalRequest)
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(`${API_BASE_URL}/usuarios/refresh/`, { refresh })
        localStorage.setItem('access_token', data.access)
        processQueue(null, data.access)
        originalRequest.headers.Authorization = `Bearer ${data.access}`
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export default api
