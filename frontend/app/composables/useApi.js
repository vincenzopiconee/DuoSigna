export const useApiUrl = (endpoint = '') => {
  const config = useRuntimeConfig()
  const base = (config.public?.apiBase || 'http://127.0.0.1:8000').replace(/\/+$/, '')
  if (!endpoint) return base

  let cleanEndpoint = endpoint
  // Normalize localhost / 127.0.0.1 URLs to use the configured API base in production
  if (cleanEndpoint.startsWith('http://localhost') || cleanEndpoint.startsWith('http://127.0.0.1')) {
    cleanEndpoint = cleanEndpoint.replace(/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?/, '')
  } else if (cleanEndpoint.startsWith('http://') || cleanEndpoint.startsWith('https://')) {
    return cleanEndpoint
  }

  const normalizedPath = cleanEndpoint.startsWith('/') ? cleanEndpoint : `/${cleanEndpoint}`
  return `${base}${normalizedPath}`
}

