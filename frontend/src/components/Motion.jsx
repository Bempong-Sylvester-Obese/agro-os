import React from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'

const easeOut = [0.22, 1, 0.36, 1]

export function PageMotion({ children, pageKey, className = '' }) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      key={pageKey}
      className={`page-motion ${className}`.trim()}
      initial={reduceMotion ? false : { opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={reduceMotion ? { opacity: 0 } : { opacity: 0, y: -6 }}
      transition={{ duration: reduceMotion ? 0 : 0.28, ease: easeOut }}
    >
      {children}
    </motion.div>
  )
}

export function Reveal({ children, className = '', delay = 0, ...props }) {
  const reduceMotion = useReducedMotion()

  return (
    <motion.div
      {...props}
      className={className}
      initial={reduceMotion ? false : { opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{ duration: reduceMotion ? 0 : 0.45, delay: reduceMotion ? 0 : delay, ease: easeOut }}
    >
      {children}
    </motion.div>
  )
}

export function ModalPresence({ show, children }) {
  const reduceMotion = useReducedMotion()

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          className="motion-modal-presence"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0 : 0.16 }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
