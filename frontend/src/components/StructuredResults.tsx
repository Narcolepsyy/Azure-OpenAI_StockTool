import React from 'react'

interface StructuredResultsProps {
  toolName: string
  result: unknown
}

export const StructuredResults = React.memo(function StructuredResults({ 
  toolName, 
  result 
}: StructuredResultsProps) {
  // Custom structured display for different tool types
  const renderStructuredResult = (toolName: string, result: unknown): React.ReactNode => {
    if (!result || typeof result !== 'object') return null
    
    const resultObj = result as any
    
    switch (toolName) {
      case 'get_company_profile':
        return (
          <div className="bg-gradient-to-br from-purple-900/30 to-purple-800/20 border border-purple-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-purple-300 font-medium text-sm">
              <span>📄</span>
              <span>Company Profile</span>
            </div>
            {resultObj.symbol && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-gray-400">Symbol:</span> <span className="text-white font-mono">{resultObj.symbol}</span></div>
                <div><span className="text-gray-400">Name:</span> <span className="text-white">{resultObj.companyName || resultObj.name}</span></div>
                <div><span className="text-gray-400">Industry:</span> <span className="text-white">{resultObj.industry}</span></div>
                <div><span className="text-gray-400">Sector:</span> <span className="text-white">{resultObj.sector}</span></div>
              </div>
            )}
          </div>
        )
      
      case 'get_stock_quote':
        return (
          <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-green-300 font-medium text-sm">
              <span>💲</span>
              <span>Live Stock Quote</span>
            </div>
            {resultObj.symbol && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-gray-400">Symbol:</span> <span className="text-white font-mono">{resultObj.symbol}</span></div>
                <div><span className="text-gray-400">Price:</span> <span className="text-green-400 font-semibold">${resultObj.currentPrice || resultObj.price}</span></div>
                <div><span className="text-gray-400">Change:</span> 
                  <span className={`font-semibold ${(resultObj.change || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {resultObj.change > 0 ? '+' : ''}{resultObj.change}
                  </span>
                </div>
                <div><span className="text-gray-400">Volume:</span> <span className="text-white">{resultObj.volume?.toLocaleString()}</span></div>
              </div>
            )}
          </div>
        )
      
      case 'get_historical_prices':
        return (
          <div className="bg-gradient-to-br from-amber-900/30 to-amber-800/20 border border-amber-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-amber-300 font-medium text-sm">
              <span>📈</span>
              <span>Historical Data</span>
            </div>
            {(resultObj.data || resultObj.prices) && (
              <div className="text-xs space-y-2">
                <div className="text-gray-400">
                  Retrieved {(resultObj.data?.length || resultObj.prices?.length || 0)} data points
                </div>
                {resultObj.period && (
                  <div><span className="text-gray-400">Period:</span> <span className="text-white">{resultObj.period}</span></div>
                )}
              </div>
            )}
          </div>
        )
      
      case 'get_stock_news':
      case 'get_augmented_news':
        return (
          <div className="bg-gradient-to-br from-cyan-900/30 to-cyan-800/20 border border-cyan-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-cyan-300 font-medium text-sm">
              <span>📰</span>
              <span>News Articles</span>
            </div>
            {(resultObj.articles || resultObj.news) && (
              <div className="text-xs space-y-2">
                <div className="text-gray-400">
                  Found {(resultObj.articles?.length || resultObj.news?.length || 0)} articles
                </div>
                {resultObj.articles?.[0] && (
                  <div className="bg-gray-800/50 p-2 rounded border-l-2 border-cyan-500">
                    <div className="text-cyan-300 font-medium mb-1">{resultObj.articles[0].title}</div>
                    <div className="text-gray-400 text-xs">{resultObj.articles[0].source}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      
      case 'get_risk_assessment':
        return (
          <div className="bg-gradient-to-br from-rose-900/30 to-rose-800/20 border border-rose-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-rose-300 font-medium text-sm">
              <span>🛡️</span>
              <span>Risk Assessment</span>
            </div>
            {resultObj.riskScore && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div><span className="text-gray-400">Risk Score:</span> <span className="text-white font-semibold">{resultObj.riskScore}/10</span></div>
                <div><span className="text-gray-400">Category:</span> <span className="text-white">{resultObj.riskCategory}</span></div>
              </div>
            )}
          </div>
        )
      
      case 'rag_search':
        return (
          <div className="bg-gradient-to-br from-slate-900/30 to-slate-800/20 border border-slate-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-slate-300 font-medium text-sm">
              <span>📚</span>
              <span>Knowledge Search</span>
            </div>
            {resultObj.results && (
              <div className="text-xs text-gray-400">
                Found {resultObj.results.length} relevant knowledge entries
              </div>
            )}
          </div>
        )
      
      case 'search_symbol':
        return (
          <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-600/30 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2 text-blue-300 font-medium text-sm">
              <span>🔍</span>
              <span>Symbol Search</span>
            </div>
            {(resultObj.matches || resultObj.results) && (
              <div className="text-xs space-y-1">
                <div className="text-gray-400">Found {(resultObj.matches?.length || resultObj.results?.length || 0)} matches</div>
                {(resultObj.matches?.[0] || resultObj.results?.[0]) && (
                  <div className="text-white">
                    <span className="font-mono">{(resultObj.matches?.[0] || resultObj.results?.[0]).symbol}</span>
                    {' - '}
                    <span>{(resultObj.matches?.[0] || resultObj.results?.[0]).name}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )
      
      default:
        // For other tools, show a clean summary without raw JSON
        if (resultObj && typeof resultObj === 'object') {
          const keys = Object.keys(resultObj)
          const hasData = keys.length > 0
          
          return (
            <div className="bg-gradient-to-br from-gray-800/50 to-gray-700/30 border border-gray-600/40 rounded-lg p-4">
              <div className="flex items-center gap-2 text-gray-300 font-medium text-sm mb-2">
                <span>🔧</span>
                <span>Tool Result</span>
              </div>
              {hasData ? (
                <div className="text-xs text-gray-400">
                  Operation completed successfully with {keys.length} data field{keys.length !== 1 ? 's' : ''}
                </div>
              ) : (
                <div className="text-xs text-gray-400">Operation completed</div>
              )}
            </div>
          )
        }
        return null
    }
  }

  const structuredResult = renderStructuredResult(toolName, result)
  
  if (structuredResult) {
    return <>{structuredResult}</>
  }
  
  // Fallback for completely unknown result types
  return (
    <div className="bg-gray-900/50 border border-gray-600/30 rounded-lg p-3 text-xs text-gray-400 text-center">
      Tool execution completed successfully
    </div>
  )
})

StructuredResults.displayName = 'StructuredResults'