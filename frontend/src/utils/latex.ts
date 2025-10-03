export const normalizeLatexDelimiters = (text: string): string => {
  if (!text) return text

  const convertBracketMath = (input: string): string => {
    const bracketPattern = /\[\s*\\[a-zA-Z]+[\s\S]*?\]/g
    return input.replace(bracketPattern, match => {
      const inner = match.slice(1, -1).trim()
      return `\\(${inner}\\)`
    })
  }

  const convertDollars = (input: string): string => {
    let result = ''
    let index = 0
    const length = input.length

    while (index < length) {
      const current = input[index]
      const next = input[index + 1]

      if (current === '\\') {
        // Preserve escaped characters
        result += current
        index += 1
        if (index < length) {
          result += input[index]
          index += 1
        }
        continue
      }

      // Handle block math: $$ ... $$
      if (current === '$' && next === '$') {
        const end = input.indexOf('$$', index + 2)
        if (end !== -1) {
          const inner = input.slice(index + 2, end).trim()
          result += `\\[${inner}\\]`
          index = end + 2
          continue
        }
      }

      // Handle inline math: $ ... $
      if (current === '$' && next !== '$') {
        let end = input.indexOf('$', index + 1)
        while (end !== -1 && input[end - 1] === '\\') {
          // Skip escaped dollar signs
          end = input.indexOf('$', end + 1)
        }
        if (end !== -1) {
          const inner = input.slice(index + 1, end).trim()
          result += `\\(${inner}\\)`
          index = end + 1
          continue
        }
      }

      result += current
      index += 1
    }

    return result
  }

  const bracketNormalized = convertBracketMath(text)
  return convertDollars(bracketNormalized)
}
