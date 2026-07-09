import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardPath, MARKETING_PATHS } from '../constants/routes'

/**
 * Drop-in replacement for the legacy setPage(target, options) navigation API.
 */
export function useAppNavigate() {
  const navigate = useNavigate()

  return useCallback((target, options = {}) => {
    const { loginMode, dashboardSection, scrollTo } = options

    if (target === 'dashboard') {
      navigate(scrollTo ? `${dashboardPath(dashboardSection)}#${scrollTo}` : dashboardPath(dashboardSection))
      if (!scrollTo) window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }

    if (target === 'login') {
      const search = loginMode === 'signup' ? '?mode=signup' : ''
      navigate(`/login${search}`)
      window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }

    const base = MARKETING_PATHS[target] || '/'
    if (scrollTo) {
      navigate(`${base}#${scrollTo}`)
      return
    }

    navigate(base)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }, [navigate])
}
