// Citation utilities: extract inline [n] references, decorate HTML, and basic verification.
// Security: All source snippets and answer HTML must be sanitized BEFORE passing into decorateAnswerWithCitations.
// The decorator only injects a constrained set of <sup><button><span> elements with data-* attributes.

export interface SourceSummary {
  citationId: number | string
  title: string
  url?: string
  text?: string // sanitized snippet (may contain basic inline HTML)
  citationLabel?: string
}

export interface CitationRef {
  index: number
  id: string // numeric id as string
  match: string // original matched token like [3]
  start: number
  end: number
}

export interface VerificationResult {
  citationId: string
  overlapRatio: number // 0..1 token overlap with chosen sentence
  flagged: boolean // true if below threshold
}

const CITATION_REGEX = /\[(\d{1,3})\]/g

export function extractCitationRefs(answer: string): CitationRef[] {
  const refs: CitationRef[] = []
  let m: RegExpExecArray | null
  let idx = 0
  while ((m = CITATION_REGEX.exec(answer)) !== null) {
    refs.push({
      index: idx++,
      id: m[1]!,
      match: m[0],
      start: m.index,
      end: m.index + m[0].length
    })
  }
  return refs
}

// Very lightweight sentence splitter for verification: splits on period, exclamation, question marks.
function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(Boolean)
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s]/gi, ' ')
    .split(/\s+/)
    .filter(Boolean)
}

function jaccard(a: string[], b: string[]): number {
  if (!a.length || !b.length) return 0
  const setA = new Set(a)
  const setB = new Set(b)
  let intersection = 0
  for (const t of setA) if (setB.has(t)) intersection++
  return intersection / (setA.size + setB.size - intersection)
}

export function verifyCitations(answer: string, sources: SourceSummary[], threshold = 0.08): VerificationResult[] {
  const refs = extractCitationRefs(answer)
  if (!refs.length) return []
  const sentences = splitSentences(answer)
  return refs.map(ref => {
    const source = sources.find(s => String(s.citationId) === ref.id)
    if (!source || !source.text) return { citationId: ref.id, overlapRatio: 0, flagged: true }
    const sourceTokens = tokenize(source.text)
    // find sentence that contains this ref
    const sentence = sentences.find(s => s.includes(`[${ref.id}]`)) || ''
    const sentenceTokens = tokenize(sentence)
    const overlap = jaccard(sourceTokens, sentenceTokens)
    return { citationId: ref.id, overlapRatio: overlap, flagged: overlap < threshold }
  })
}

export interface DecoratedCitationData {
  html: string
  verification: VerificationResult[]
}

// Decorate sanitized answer HTML by replacing [n] with a <sup><button> allowing hover preview.
// Provide tooltip container spans appended inline; rely on CSS (Tailwind) for hover reveal.
export function decorateAnswerWithCitations(sanitizedAnswerHtml: string, sources: SourceSummary[]): DecoratedCitationData {
  const refs = extractCitationRefs(sanitizedAnswerHtml)
  if (!refs.length) return { html: sanitizedAnswerHtml, verification: [] }
  const verification = verifyCitations(sanitizedAnswerHtml, sources)

  // Build a map for quick source lookup
  const sourceMap = new Map<string, SourceSummary>()
  for (const s of sources) sourceMap.set(String(s.citationId), s)

  let result = ''
  let lastIndex = 0
  for (const ref of refs) {
    result += sanitizedAnswerHtml.slice(lastIndex, ref.start)
    const src = sourceMap.get(ref.id)
    if (!src) {
      // Keep plain if missing
      result += ref.match
    } else {
      const ver = verification.find(v => v.citationId === ref.id)
      const flaggedAttr = ver?.flagged ? ' data-flagged="true"' : ''
      // Tooltip content (already sanitized src.text)
      const preview = src.text ? src.text : ''
      const title = src.title ? src.title : ''
      // Use button for accessibility; tooltip span hidden by default
      result += `<sup class="inline citation-ref" data-cite="${ref.id}"><button type="button" class="align-super text-[10px] text-blue-300 hover:text-blue-200 focus:outline-none" data-citation-id="${ref.id}" aria-label="Citation ${ref.id}"${flaggedAttr}>[${ref.id}]</button><span class="citation-tooltip hidden absolute z-40 max-w-sm p-2 mt-1 rounded-md bg-gray-900/95 border border-gray-700 shadow-lg text-[11px] leading-snug text-gray-200" role="tooltip" data-citation-ref="${ref.id}"><span class="block font-medium text-blue-300 mb-1 line-clamp-2">${title}</span><span class="block text-gray-300">${preview}</span>${ver?.flagged ? '<span class="mt-1 block text-yellow-400 text-[10px]">Low citation confidence</span>' : ''}</span></sup>`
    }
    lastIndex = ref.end
  }
  result += sanitizedAnswerHtml.slice(lastIndex)
  return { html: result, verification }
}
