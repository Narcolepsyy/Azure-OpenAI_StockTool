import { useEffect, useRef } from 'react'

interface UseStickyOptions {
  onStickyStateChange?: (isStuck: boolean, messageId: string) => void
  messageId: string
}

export const useSticky = ({ onStickyStateChange, messageId }: UseStickyOptions) => {
  const headerRef = useRef<HTMLDivElement>(null)
  const observerRef = useRef<IntersectionObserver | null>(null)

  useEffect(() => {
    if (!headerRef.current) return

    // Clean up existing observer
    if (observerRef.current) {
      observerRef.current.disconnect()
    }

    // Use a ref to track the last known state to prevent rapid toggling
    let lastIsStuck = false
    let debounceTimeout: number | null = null

    // Create new observer for this specific header
    observerRef.current = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          const header = entry.target as HTMLElement
          const rect = entry.boundingClientRect
          
          // More stable stuck detection with better tolerance
          const isAtTop = rect.top <= 5 // Increased tolerance to prevent flickering
          const isNotFullyVisible = entry.intersectionRatio < 0.99 // More forgiving threshold
          const isStuck = isAtTop && isNotFullyVisible

          // Only update if the state actually changed to prevent rapid toggling
          if (isStuck !== lastIsStuck) {
            // Clear any existing debounce timeout
            if (debounceTimeout) {
              clearTimeout(debounceTimeout)
            }
            
            // Debounce the state change to prevent rapid toggling
            debounceTimeout = window.setTimeout(() => {
              header.classList.toggle('is-stuck', isStuck)
              lastIsStuck = isStuck
              // Notify parent about sticky state change
              onStickyStateChange?.(isStuck, messageId)
            }, 10) // Small debounce to smooth out rapid changes
          }
        })
      },
      {
        threshold: [0.99, 1], // Simplified thresholds - only care about nearly invisible and fully visible
        rootMargin: '-5px 0px -5px 0px' // Negative margins to delay trigger and reduce sensitivity
      }
    )

    observerRef.current.observe(headerRef.current)

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
      if (debounceTimeout) {
        clearTimeout(debounceTimeout)
      }
    }
  }, [messageId, onStickyStateChange])

  return headerRef
}