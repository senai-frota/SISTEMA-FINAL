/**
 * Detecção de cliente móvel para UX e cabeçalho X-Client-Form-Factor.
 * Não usa apenas User-Agent: combina touch, pointer coarse e viewport.
 */
export function isMobileClient() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return false
  }

  const ua = navigator.userAgent || ''
  const uaMobile = /Android|iPhone|iPod|iPad|Mobile|webOS|BlackBerry|IEMobile|Opera Mini/i.test(
    ua
  )

  const touchPoints = Number(navigator.maxTouchPoints || 0)
  const coarse =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(pointer: coarse)').matches
  const narrow =
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(max-width: 900px)').matches

  // Smartphone/tablet típico
  if (touchPoints > 0 && (coarse || narrow || uaMobile)) return true
  if (uaMobile && narrow) return true

  return false
}

export function clientFormFactor() {
  return isMobileClient() ? 'mobile' : 'desktop'
}
