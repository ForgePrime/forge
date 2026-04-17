import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/client'
import { useAuthStore, AuthUser } from '../stores/authStore'

export const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((state) => state.setAuth)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const response = await apiClient.post<{ token: string; user: AuthUser }>('/auth/login', {
        email,
        password,
      })
      setAuth(response.data.token, response.data.user)
      navigate('/products')
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 401) {
        setError('Nieprawidłowy email lub hasło.')
      } else {
        setError('Wystąpił błąd serwera. Spróbuj ponownie.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Logowanie</h1>
      <form onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>
        <div>
          <label htmlFor="password">Hasło</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        {error && (
          <p role="alert" aria-live="assertive">
            {error}
          </p>
        )}
        <button type="submit" disabled={loading}>
          {loading ? 'Logowanie…' : 'Zaloguj'}
        </button>
      </form>
    </main>
  )
}
