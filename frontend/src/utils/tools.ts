/**
 * Tool-related utility functions
 */

import type { ToolCall, LiveTool, ToolMeta } from '../types'
import { TOOL_META, DEFAULT_TOOL_META } from '../constants'

/**
 * Get tool metadata for a given tool name
 */
export const getToolMeta = (toolName: string): ToolMeta => {
  return TOOL_META[toolName] || DEFAULT_TOOL_META
}

/**
 * Summarize tool call result for display
 */
export const summarizeResult = (result: unknown): string | null => {
  try {
    if (result == null) return null
    const s = JSON.stringify(result)
    return s.length > 200 ? s.slice(0, 200) + '…' : s
  } catch {
    return String(result).slice(0, 200)
  }
}

/**
 * Group tool calls by name with counts and samples
 */
export const groupToolCalls = (toolCalls: ToolCall[]) => {
  const grouped = new Map<string, { name: string; count: number; sample?: unknown }>()
  
  for (const tool of toolCalls) {
    const key = tool.name || 'unknown'
    const existing = grouped.get(key)
    
    if (existing) {
      grouped.set(key, { 
        ...existing, 
        count: existing.count + 1, 
        sample: tool.result ?? existing.sample 
      })
    } else {
      grouped.set(key, { name: key, count: 1, sample: tool.result })
    }
  }
  
  // Sort by name for stable order
  return Array.from(grouped.values()).sort((a, b) => a.name.localeCompare(b.name))
}

/**
 * Get tool info for live tool activity display
 */
export const getToolActivityInfo = (toolName: string) => {
  const name = toolName.toLowerCase()
  
  if (name.includes('web_search') || name === 'web_search') {
    return { 
      label: 'Web Search',
      color: 'bg-green-50 text-green-700 border-green-100'
    }
  }
  
  if (name.includes('web_search_news')) {
    return { 
      label: 'News Search',
      color: 'bg-purple-50 text-purple-700 border-purple-100'
    }
  }
  
  if (name.includes('augmented_rag') || name.includes('financial_context')) {
    return { 
      label: 'Enhanced Search',
      color: 'bg-indigo-50 text-indigo-700 border-indigo-100'
    }
  }
  
  if (name.includes('rag_search')) {
    return { 
      label: 'Knowledge Base',
      color: 'bg-blue-50 text-blue-700 border-blue-100'
    }
  }
  
  if (name.includes('stock') || name.includes('market') || name.includes('financial')) {
    return { 
      label: 'Market Data',
      color: 'bg-orange-50 text-orange-700 border-orange-100'
    }
  }
  
  // Default
  return { 
    label: toolName,
    color: 'bg-gray-50 text-gray-700 border-gray-100'
  }
}

/**
 * Update live tools list with new tool information
 */
export const updateLiveTools = (
  currentTools: LiveTool[],
  toolName: string,
  status: 'running' | 'completed' | 'error',
  error?: string
): LiveTool[] => {
  const existing = currentTools.find(t => t.name === toolName)
  
  if (existing) {
    return currentTools.map(t => 
      t.name === toolName 
        ? { ...t, status, error } 
        : t
    )
  }
  
  return [...currentTools, { name: toolName, status, error }]
}

/**
 * Add multiple tools to live tools list
 */
export const addLiveTools = (
  currentTools: LiveTool[],
  toolNames: string[]
): LiveTool[] => {
  const existing = new Map(currentTools.map(t => [t.name, t]))
  
  toolNames.forEach(name => {
    if (!existing.has(name)) {
      existing.set(name, { name, status: 'running' })
    }
  })
  
  return Array.from(existing.values())
}