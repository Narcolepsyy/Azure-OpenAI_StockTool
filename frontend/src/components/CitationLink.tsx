import React from 'react'
import { createPortal } from 'react-dom'

interface CitationInfo {
  title?: string
  url?: string
  domain?: string
}

interface CitationLinkProps {
  citationNum: string
  sourceInfo?: CitationInfo
  onClick?: (citationNum: string) => void
}

export const CitationLink = React.memo(function CitationLink({
  citationNum,
  sourceInfo,
  onClick
}: CitationLinkProps) {
  const [open, setOpen] = React.useState(false)
  const triggerRef = React.useRef<HTMLSpanElement | null>(null)
  const popoverRef = React.useRef<HTMLDivElement | null>(null)
  const [popoverPosition, setPopoverPosition] = React.useState<{ top: number; left: number } | null>(null)
  const citationUrl = sourceInfo?.url?.trim()
  const hasUrl = Boolean(citationUrl)

  const updatePopoverPosition = React.useCallback(() => {
    if (!triggerRef.current) return
    const rect = triggerRef.current.getBoundingClientRect()
    setPopoverPosition({
      top: rect.bottom + 8,
      left: rect.left + rect.width / 2
    })
  }, [])

  // Close on outside click / escape
  React.useEffect(() => {
    if (!open) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    const handleClick = (e: MouseEvent) => {
      if (
        popoverRef.current && !popoverRef.current.contains(e.target as Node) &&
        triggerRef.current && !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('keydown', handleKey)
    document.addEventListener('mousedown', handleClick)
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.removeEventListener('mousedown', handleClick)
    }
  }, [open])

  React.useLayoutEffect(() => {
    if (!open) {
      setPopoverPosition(null)
      return
    }

    updatePopoverPosition()
    const handleWindowChange = () => updatePopoverPosition()

    window.addEventListener('resize', handleWindowChange)
    window.addEventListener('scroll', handleWindowChange, true)

    return () => {
      window.removeEventListener('resize', handleWindowChange)
      window.removeEventListener('scroll', handleWindowChange, true)
    }
  }, [open, updatePopoverPosition])

  const handleActivate = (e: React.MouseEvent | React.KeyboardEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (citationUrl) {
      const win = window.open(citationUrl, '_blank', 'noopener,noreferrer')
      // If popup blocked, fall back to showing the popover for context
      if (!win) {
        setOpen(o => !o)
      } else {
        setOpen(false)
      }
    } else {
      setOpen(o => !o)
    }
    if (onClick) onClick(citationNum)
  }

  const handleTriggerMouseLeave = (event: React.MouseEvent) => {
    const nextTarget = event.relatedTarget as Node | null
    if (nextTarget) {
      if (popoverRef.current && popoverRef.current.contains(nextTarget)) {
        return
      }
    }
    setOpen(false)
  }

  const handlePopoverMouseLeave = (event: React.MouseEvent) => {
    const nextTarget = event.relatedTarget as Node | null
    if (nextTarget) {
      if (triggerRef.current && triggerRef.current.contains(nextTarget)) {
        return
      }
      if (popoverRef.current && popoverRef.current.contains(nextTarget)) {
        return
      }
    }
    setOpen(false)
  }

  const title = sourceInfo?.title 
    ? `${sourceInfo.title} - ${sourceInfo.domain || 'Click to view source'}${hasUrl ? ' (opens source)' : ''}`
    : `Source ${citationNum}${hasUrl ? ' (opens source)' : ''}`

  return (
    <span className="relative inline-block mx-0.5 align-baseline">
      <span
        ref={triggerRef}
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={title}
        className="citation-link inline-flex items-center justify-center min-w-[1.25rem] h-[1.25rem] px-0.5 text-[0.7rem] font-medium text-blue-400 hover:text-blue-300 bg-slate-800/60 hover:bg-slate-700/80 border border-blue-500/30 hover:border-blue-400/50 rounded cursor-pointer transition-all duration-150 shadow-sm hover:shadow-md focus:outline-none focus-visible:ring-1 focus-visible:ring-blue-400 focus-visible:ring-offset-1 focus-visible:ring-offset-slate-900 leading-none align-baseline -top-[0.35em] relative"
        onClick={handleActivate}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleActivate(e) }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={handleTriggerMouseLeave}
      >
        {citationNum}
      </span>
      {open && sourceInfo?.title && popoverPosition &&
        createPortal(
          <div
            ref={popoverRef}
            role="dialog"
            className="citation-popover-modern fixed z-50"
            style={{
              top: popoverPosition.top,
              left: popoverPosition.left,
              transform: 'translateX(-50%)'
            }}
            onMouseEnter={() => setOpen(true)}
            onMouseLeave={handlePopoverMouseLeave}
          >
            <div className="flex items-start gap-2 mb-2">
              <span className="flex-shrink-0 flex items-center justify-center w-5 h-5 text-[0.65rem] font-semibold text-blue-300 bg-blue-500/20 border border-blue-400/30 rounded">
                {citationNum}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[0.8rem] text-slate-100 font-medium leading-tight line-clamp-2 mb-1">
                  {sourceInfo.title}
                </div>
                {sourceInfo.domain && (
                  <div className="text-[0.7rem] text-slate-400 truncate">
                    {sourceInfo.domain}
                  </div>
                )}
              </div>
            </div>
            {sourceInfo.url && (
              <a
                href={sourceInfo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[0.7rem] text-blue-400 hover:text-blue-300 transition-colors font-medium"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
                View source
              </a>
            )}
          </div>,
          document.body
        )}
    </span>
  )
})

CitationLink.displayName = 'CitationLink'