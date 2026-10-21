export const useApiUrl = (endpoint = '') => {
  const config = useRuntimeConfig()
  const base = config.public?.apiBase || 'http://127.0.0.1:8000'
  if (!endpoint) return base
  if (endpoint.startsWith('http://') || endpoint.startsWith('https://')) return endpoint
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  return `${base}${cleanEndpoint}`
}
