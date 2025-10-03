// DOMPurify-based sanitizer wrapper.
// Provides stronger guarantees than the previous minimal regex approach.
// Adjust ALLOWED_TAGS / ALLOWED_ATTR if you need richer formatting.
import DOMPurify from 'dompurify'

// Narrow allowlist to reduce XSS risk while supporting expected formatting.
const ALLOWED_TAGS = [
  'strong','b','em','i','u','br','code','pre','sup','sub','a','p','span','ul','ol','li','blockquote'
]
const ALLOWED_ATTR = ['href','rel','target']

export function sanitizeHtml(input: string): string {
  if (!input) return ''
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['style','svg','math'],
    FORBID_ATTR: ['style','onerror','onclick','onload']
  })
}
