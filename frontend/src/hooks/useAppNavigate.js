import { useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { dashboardPath, MARKETING_PATHS } from '../constants/routes'

/**
 * Drop-in replacement for the legacy setPage(target, options) navigation API.
 */
export function useAppNavigate() {
  const navigate = useNavigate()

  return useCallback((target, options = {}) => {
    const { loginMode, dashboardSection, scrollTo, next, plan, enterprise, topic } = options

    if (target === 'dashboard') {
      navigate(scrollTo ? `${dashboardPath(dashboardSection)}#${scrollTo}` : dashboardPath(dashboardSection))
      if (!scrollTo) window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }

    if (target === 'login' || target === 'auth') {
      const params = new URLSearchParams()
      if (loginMode === 'signup') params.set('mode', 'signup')
      if (next && next.startsWith('/') && !next.startsWith('//')) params.set('next', next)
      const search = params.toString() ? `?${params.toString()}` : ''
      navigate(`/login${search}`)
      window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }

    if (target === 'subscription') {
      const selectedPlan = plan === 'growth' ? 'growth' : 'starter'
      navigate(`/subscribe/${selectedPlan}`)
      window.scrollTo({ top: 0, behavior: 'instant' })
      return
    }

    if (target === 'bookDemo' && (enterprise || plan === 'enterprise' || topic)) {
      const params = new URLSearchParams()
      const isEnterprise = enterprise || plan === 'enterprise'
      if (isEnterprise) params.set('plan', 'enterprise')
      if (topic) params.set('topic', topic)
      else if (isEnterprise) params.set('topic', 'Enterprise implementation')
      navigate(`/book-demo?${params.toString()}`)
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
