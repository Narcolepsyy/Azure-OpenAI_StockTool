import React, { useState } from 'react'
import clsx from 'clsx'
import { 
  Globe, 
  TrendingUp, 
  DollarSign, 
  FileText, 
  Search,
  PieChart,
  Shield,
  BookOpen,
  BarChart3,
  Calendar,
  Users,
  Coins,
  Target,
  LineChart,
  Activity,
  Newspaper,
  Building,
  Calculator,
  Crosshair,
  GitBranch
} from 'lucide-react'

// Tool categories and metadata based on tools.py
const TOOL_CATEGORIES = {
  stock_data: {
    label: 'Stock Data',
    icon: TrendingUp,
    color: 'bg-green-50 text-green-700 border-green-200',
    description: 'Real-time and historical stock market data'
  },
  financials: {
    label: 'Financial Analysis',
    icon: BarChart3,
    color: 'bg-blue-50 text-blue-700 border-blue-200',
    description: 'Financial statements and analytical metrics'
  },
  market_data: {
    label: 'Market Intelligence',
    icon: PieChart,
    color: 'bg-purple-50 text-purple-700 border-purple-200',
    description: 'Market indices, summaries, and broader market data'
  },
  search_tools: {
    label: 'Search & Research',
    icon: Globe,
    color: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    description: 'Web search, news, and knowledge retrieval tools'
  },
  technical_analysis: {
    label: 'Technical Analysis',
    icon: LineChart,
    color: 'bg-amber-50 text-amber-700 border-amber-200',
    description: 'Technical indicators and pattern analysis'
  },
  risk_analysis: {
    label: 'Risk Assessment',
    icon: Shield,
    color: 'bg-red-50 text-red-700 border-red-200',
    description: 'Risk metrics and portfolio analysis'
  }
}

// Complete tool registry based on tools.py
const TOOLS_REGISTRY = [
  // Stock Data Tools
  {
    name: 'get_stock_quote',
    category: 'stock_data',
    label: 'Live Stock Quote',
    icon: DollarSign,
    description: 'Get the latest close price for any stock ticker symbol',
    parameters: ['symbol'],
    example: 'get_stock_quote(symbol="AAPL")',
    useCase: 'Check current stock prices for quick analysis'
  },
  {
    name: 'get_company_profile',
    category: 'stock_data',
    label: 'Company Profile',
    icon: Building,
    description: 'Get comprehensive company details including sector, industry, and business summary',
    parameters: ['symbol'],
    example: 'get_company_profile(symbol="MSFT")',
    useCase: 'Research company fundamentals and business overview'
  },
  {
    name: 'get_historical_prices',
    category: 'stock_data',
    label: 'Historical Prices',
    icon: BarChart3,
    description: 'Get historical OHLCV price data with flexible time periods and intervals',
    parameters: ['symbol', 'period?', 'interval?', 'limit?'],
    example: 'get_historical_prices(symbol="GOOGL", period="1y", interval="1d")',
    useCase: 'Analyze price trends and perform technical analysis'
  },

  // Financial Analysis Tools
  {
    name: 'get_financials',
    category: 'financials',
    label: 'Financial Statements',
    icon: FileText,
    description: 'Get comprehensive financial statements including income statement, balance sheet, and cash flow',
    parameters: ['symbol', 'freq?'],
    example: 'get_financials(symbol="AMZN", freq="quarterly")',
    useCase: 'Analyze company financial health and performance metrics'
  },
  {
    name: 'get_earnings_data',
    category: 'financials',
    label: 'Earnings Data',
    icon: Calendar,
    description: 'Get earnings history, quarterly earnings, and earnings calendar with estimates',
    parameters: ['symbol'],
    example: 'get_earnings_data(symbol="TSLA")',
    useCase: 'Track earnings performance and upcoming earnings dates'
  },
  {
    name: 'get_analyst_recommendations',
    category: 'financials',
    label: 'Analyst Recommendations',
    icon: Target,
    description: 'Get analyst recommendations, price targets, and consensus ratings',
    parameters: ['symbol'],
    example: 'get_analyst_recommendations(symbol="NVDA")',
    useCase: 'See what Wall Street analysts think about a stock'
  },
  {
    name: 'get_institutional_holders',
    category: 'financials',
    label: 'Institutional Holders',
    icon: Users,
    description: 'Get institutional holders, mutual fund holders, and major shareholders data',
    parameters: ['symbol'],
    example: 'get_institutional_holders(symbol="META")',
    useCase: 'Understand institutional ownership and smart money positioning'
  },
  {
    name: 'get_market_cap_details',
    category: 'financials',
    label: 'Market Cap Details',
    icon: Calculator,
    description: 'Get comprehensive market capitalization and valuation metrics',
    parameters: ['symbol'],
    example: 'get_market_cap_details(symbol="AAPL")',
    useCase: 'Analyze company valuation and market position'
  },
  {
    name: 'get_dividends_splits',
    category: 'financials',
    label: 'Dividends & Splits',
    icon: Coins,
    description: 'Get dividend history and stock split information',
    parameters: ['symbol', 'period?'],
    example: 'get_dividends_splits(symbol="JNJ", period="5y")',
    useCase: 'Track dividend payments and stock split history'
  },

  // Market Intelligence Tools
  {
    name: 'get_market_indices',
    category: 'market_data',
    label: 'Market Indices',
    icon: PieChart,
    description: 'Get current prices and performance of major market indices worldwide',
    parameters: ['region?'],
    example: 'get_market_indices(region="us")',
    useCase: 'Monitor overall market performance and regional trends'
  },
  {
    name: 'get_market_summary',
    category: 'market_data',
    label: 'Market Summary',
    icon: Activity,
    description: 'Get comprehensive market summary including global indices and sentiment',
    parameters: [],
    example: 'get_market_summary()',
    useCase: 'Get a quick overview of global market conditions'
  },
  {
    name: 'get_nikkei_news_with_sentiment',
    category: 'market_data',
    label: 'Nikkei News & Sentiment',
    icon: Newspaper,
    description: 'Get recent Nikkei 225 news headlines with sentiment analysis',
    parameters: ['limit?'],
    example: 'get_nikkei_news_with_sentiment(limit=10)',
    useCase: 'Monitor Japanese market sentiment and news flow'
  },
  {
    name: 'get_augmented_news',
    category: 'market_data',
    label: 'Augmented News',
    icon: Newspaper,
    description: 'Get recent news articles with optional full text and RAG context enhancement',
    parameters: ['symbol', 'limit?', 'include_full_text?', 'include_rag?'],
    example: 'get_augmented_news(symbol="AAPL", include_rag=true)',
    useCase: 'Get comprehensive news analysis with AI-enhanced context'
  },

  // Search & Research Tools
  {
    name: 'perplexity_search',
    category: 'search_tools',
    label: 'AI Web Search',
    icon: Globe,
    description: 'PRIORITY TOOL: Enhanced web search with AI-powered answer synthesis - supports all languages',
    parameters: ['query', 'max_results?', 'synthesize_answer?', 'include_recent?'],
    example: 'perplexity_search(query="Tesla Q3 2024 earnings analysis")',
    useCase: 'Get current information and comprehensive research on any topic'
  },
  {
    name: 'augmented_rag_search',
    category: 'search_tools',
    label: 'Enhanced RAG Search',
    icon: BookOpen,
    description: 'Advanced search combining knowledge base and web search for complete context',
    parameters: ['query', 'kb_k?', 'web_results?', 'include_web?'],
    example: 'augmented_rag_search(query="investment strategies")',
    useCase: 'Combine internal knowledge with current web information'
  },
  {
    name: 'financial_context_search',
    category: 'search_tools',
    label: 'Financial Context Search',
    icon: Search,
    description: 'Specialized search for financial topics with news and knowledge base integration',
    parameters: ['query', 'symbol?', 'include_news?', 'kb_k?'],
    example: 'financial_context_search(query="ESG investing trends", symbol="MSCI")',
    useCase: 'Get comprehensive financial research with market context'
  },
  {
    name: 'rag_search',
    category: 'search_tools',
    label: 'Knowledge Search',
    icon: BookOpen,
    description: 'Retrieve relevant information from the internal knowledge base',
    parameters: ['query', 'k?'],
    example: 'rag_search(query="portfolio diversification strategies")',
    useCase: 'Access curated financial knowledge and best practices'
  },

  // Technical Analysis Tools
  {
    name: 'get_technical_indicators',
    category: 'technical_analysis',
    label: 'Technical Indicators',
    icon: LineChart,
    description: 'Calculate technical analysis indicators like SMA, EMA, RSI, MACD, Bollinger Bands',
    parameters: ['symbol', 'period?', 'indicators?'],
    example: 'get_technical_indicators(symbol="SPY", indicators=["sma_20", "rsi_14"])',
    useCase: 'Perform technical analysis and identify trading signals'
  },
  {
    name: 'check_golden_cross',
    category: 'technical_analysis',
    label: 'Golden Cross Analysis',
    icon: Crosshair,
    description: 'Check for golden cross and death cross patterns between moving averages',
    parameters: ['symbol', 'short_period?', 'long_period?', 'period?'],
    example: 'check_golden_cross(symbol="AAPL", short_period=5, long_period=25)',
    useCase: 'Identify bullish/bearish moving average crossover signals'
  },
  {
    name: 'calculate_correlation',
    category: 'technical_analysis',
    label: 'Correlation Analysis',
    icon: GitBranch,
    description: 'Calculate correlation coefficient between two stocks or indices',
    parameters: ['symbol1', 'symbol2', 'period?', 'interval?'],
    example: 'calculate_correlation(symbol1="AAPL", symbol2="MSFT", period="1y")',
    useCase: 'Analyze relationships between securities for portfolio diversification'
  },

  // Risk Analysis Tools
  {
    name: 'get_risk_assessment',
    category: 'risk_analysis',
    label: 'Risk Assessment',
    icon: Shield,
    description: 'Compute comprehensive risk metrics including volatility, Sharpe ratio, VaR, and beta',
    parameters: ['symbol', 'period?', 'interval?', 'rf_rate?', 'benchmark?'],
    example: 'get_risk_assessment(symbol="TSLA", period="1y", benchmark="SPY")',
    useCase: 'Evaluate investment risk and risk-adjusted returns'
  }
]

interface ToolsRegistryProps {
  className?: string
}

interface ToolCardProps {
  tool: typeof TOOLS_REGISTRY[0]
  isExpanded: boolean
  onToggle: () => void
}

const ToolCardComponent: React.FC<ToolCardProps> = ({ tool, isExpanded, onToggle }) => {
  const Icon = tool.icon
  const category = TOOL_CATEGORIES[tool.category as keyof typeof TOOL_CATEGORIES]
  
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden hover:border-gray-600 transition-colors">
      {/* Tool Header */}
      <div 
        className="p-3 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-start gap-3">
          <div className={clsx(
            "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center",
            category.color
          )}>
            <Icon className="w-4 h-4" />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="text-white font-medium text-sm">{tool.label}</h3>
              <code className="text-xs text-gray-400 bg-gray-900 px-1.5 py-0.5 rounded text-[10px]">
                {tool.name}
              </code>
            </div>
            
            <p className="text-gray-300 text-xs leading-relaxed mb-2">
              {tool.description}
            </p>
            
            <div className="flex items-center gap-2">
              <span className={clsx(
                "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium",
                category.color
              )}>
                <category.icon className="w-2.5 h-2.5" />
                {category.label}
              </span>
              
              <button className="text-blue-400 hover:text-blue-300 text-[10px]">
                {isExpanded ? 'Hide details' : 'View details'}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Tool Details */}
      {isExpanded && (
        <div className="border-t border-gray-700 p-3 bg-gray-850 space-y-2">
          {/* Parameters */}
          <div>
            <h4 className="text-gray-300 text-[10px] font-medium mb-1">Parameters</h4>
            <div className="flex flex-wrap gap-1">
              {tool.parameters.map((param) => (
                <code
                  key={param}
                  className={clsx(
                    "inline-block px-1.5 py-0.5 rounded text-[9px]",
                    param.endsWith('?') 
                      ? "bg-gray-700 text-gray-300" // Optional parameter
                      : "bg-blue-900 text-blue-300"  // Required parameter
                  )}
                >
                  {param}
                </code>
              ))}
            </div>
          </div>
          
          {/* Example */}
          <div>
            <h4 className="text-gray-300 text-[10px] font-medium mb-1">Example Usage</h4>
            <code className="block p-2 bg-gray-900 rounded text-[9px] text-green-400 overflow-x-auto">
              {tool.example}
            </code>
          </div>
          
          {/* Use Case */}
          <div>
            <h4 className="text-gray-300 text-[10px] font-medium mb-1">Use Case</h4>
            <p className="text-gray-400 text-[10px] leading-relaxed">
              {tool.useCase}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export const ToolsRegistry: React.FC<ToolsRegistryProps> = ({ className }) => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')

  const toggleTool = (toolName: string) => {
    const newExpanded = new Set(expandedTools)
    if (newExpanded.has(toolName)) {
      newExpanded.delete(toolName)
    } else {
      newExpanded.add(toolName)
    }
    setExpandedTools(newExpanded)
  }

  // Filter tools based on category and search
  const filteredTools = TOOLS_REGISTRY.filter(tool => {
    const matchesCategory = !selectedCategory || tool.category === selectedCategory
    const matchesSearch = !searchQuery || 
      tool.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tool.name.toLowerCase().includes(searchQuery.toLowerCase())
    
    return matchesCategory && matchesSearch
  })

  // Group tools by category
  const toolsByCategory = Object.entries(TOOL_CATEGORIES).map(([categoryKey, categoryData]) => ({
    key: categoryKey,
    ...categoryData,
    tools: filteredTools.filter(tool => tool.category === categoryKey),
    totalTools: TOOLS_REGISTRY.filter(tool => tool.category === categoryKey).length
  }))

  return (
    <div className={clsx("space-y-4", className)}>
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-xl font-bold text-white">Available Tools</h2>
        <p className="text-gray-400 text-sm max-w-3xl mx-auto">
          Comprehensive toolkit for financial analysis, market research, and investment insights. 
          Each tool provides specialized functionality for different aspects of financial analysis.
        </p>
        <div className="text-xs text-gray-500">
          Total: {TOOLS_REGISTRY.length} tools across {Object.keys(TOOL_CATEGORIES).length} categories
        </div>
      </div>

      {/* Search */}
      <div className="max-w-md mx-auto">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search tools..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 text-sm"
          />
        </div>
      </div>

      {/* Category Filter */}
      <div className="flex flex-wrap justify-center gap-1">
        <button
          onClick={() => setSelectedCategory(null)}
          className={clsx(
            "px-2 py-1 rounded-full text-xs font-medium transition-colors",
            !selectedCategory 
              ? "bg-blue-600 text-white" 
              : "bg-gray-700 text-gray-300 hover:bg-gray-600"
          )}
        >
          All ({TOOLS_REGISTRY.length})
        </button>
        
        {Object.entries(TOOL_CATEGORIES).map(([key, category]) => {
          const count = TOOLS_REGISTRY.filter(tool => tool.category === key).length
          const Icon = category.icon
          
          return (
            <button
              key={key}
              onClick={() => setSelectedCategory(selectedCategory === key ? null : key)}
              className={clsx(
                "inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors",
                selectedCategory === key 
                  ? category.color 
                  : "bg-gray-700 text-gray-300 hover:bg-gray-600"
              )}
            >
              <Icon className="w-3 h-3" />
              {category.label} ({count})
            </button>
          )
        })}
      </div>

      {/* Tools by Category */}
      <div className="space-y-6">
        {toolsByCategory.map(category => {
          if (category.tools.length === 0) return null
          
          return (
            <div key={category.key}>
              {/* Category Header */}
              {!selectedCategory && (
                <div className="flex items-center gap-3 mb-3">
                  <div className={clsx(
                    "flex items-center gap-2 px-2 py-1 rounded-lg",
                    category.color
                  )}>
                    <category.icon className="w-3 h-3" />
                    <span className="font-medium text-xs">{category.label}</span>
                    <span className="text-[10px] opacity-75">
                      ({category.tools.length}/{category.totalTools})
                    </span>
                  </div>
                  <p className="text-gray-400 text-xs">{category.description}</p>
                </div>
              )}
              
              {/* Tools Grid */}
              <div className="grid gap-3 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {category.tools.map(tool => (
                  <ToolCardComponent
                    key={tool.name}
                    tool={tool}
                    isExpanded={expandedTools.has(tool.name)}
                    onToggle={() => toggleTool(tool.name)}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* No Results */}
      {filteredTools.length === 0 && (
        <div className="text-center py-6">
          <Search className="w-8 h-8 text-gray-600 mx-auto mb-2" />
          <h3 className="text-gray-400 font-medium mb-1 text-sm">No tools found</h3>
          <p className="text-gray-500 text-xs">
            Try adjusting your search or category filter
          </p>
        </div>
      )}

      {/* Usage Tips */}
      <div className="mt-6 p-3 bg-blue-900/20 border border-blue-800 rounded-lg">
        <h3 className="text-blue-300 font-medium mb-2 text-sm">💡 Usage Tips</h3>
        <ul className="text-blue-200 text-xs space-y-1">
          <li>• <strong>perplexity_search</strong> is the priority tool for current information and research</li>
          <li>• Tools with <code className="bg-blue-900 px-1 rounded">?</code> parameters are optional</li>
          <li>• Combine multiple tools for comprehensive analysis (e.g., quote + technicals + news)</li>
          <li>• Use <strong>financial_context_search</strong> for specialized financial research</li>
          <li>• <strong>get_risk_assessment</strong> provides comprehensive risk metrics for any stock</li>
        </ul>
      </div>
    </div>
  )
}

export default ToolsRegistry