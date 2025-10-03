import React from 'react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'

interface ChartPoint {
  time: string
  close: number
  open?: number
  high?: number
  low?: number
  volume?: number
}

interface ChartRange {
  key: string
  label?: string
  period?: string
  interval?: string
  start?: string | null
  end?: string | null
  points?: ChartPoint[]
}

interface PriceChart {
  ranges?: ChartRange[]
  default_range?: string
  timezone?: string
}

interface QuoteData {
  symbol?: string
  price?: number
  currency?: string
  change?: number
  change_percent?: number
  previous_close?: number
  day_open?: number
  day_high?: number
  day_low?: number
  volume?: number
  market_cap?: number
  shares_outstanding?: number
  year_high?: number
  year_low?: number
  eps?: number
  pe_ratio?: number
  as_of?: string | null
  chart?: PriceChart
}

type ChartDatum = {
  timestamp: number
  price: number
  rawLabel: string
}

interface PriceQuoteCardProps {
  data: QuoteData
}

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === 'number' && Number.isFinite(value)

const useChartData = (ranges: ChartRange[], activeKey: string): ChartDatum[] => {
  const activeRange = ranges.find((range) => range.key === activeKey) ?? ranges[0]
  if (!activeRange?.points?.length) {
    return []
  }

  return activeRange.points
    .map((point) => {
      const parsed = Date.parse(point.time)
      const timestamp = Number.isNaN(parsed) ? Date.now() : parsed
      return {
        timestamp,
        price: point.close,
        rawLabel: point.time,
      }
    })
    .sort((a, b) => a.timestamp - b.timestamp)
}

const formatCurrency = (value?: number, currency: string = 'USD'): string => {
  if (!isFiniteNumber(value)) return '—'
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency,
      maximumFractionDigits: value >= 100 ? 2 : 4,
      minimumFractionDigits: value >= 100 ? 2 : 2,
    }).format(value)
  } catch {
    return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }
}

const formatCompactNumber = (value?: number): string => {
  if (!isFiniteNumber(value)) return '—'
  try {
    return new Intl.NumberFormat(undefined, {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value)
  } catch {
    return value.toLocaleString(undefined, { maximumFractionDigits: 1 })
  }
}

const formatNumber = (value?: number, fractionDigits = 2): string => {
  if (!isFiniteNumber(value)) return '—'
  return value.toFixed(fractionDigits)
}

const formatTimestamp = (value?: string | null): string => {
  if (!value) return ''
  const parsed = Date.parse(value)
  if (Number.isNaN(parsed)) return value
  return new Date(parsed).toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const PriceQuoteCard: React.FC<PriceQuoteCardProps> = ({ data }) => {
  const symbol = data.symbol ?? '—'
  const currencyCode = data.currency ?? 'USD'
  const ranges = React.useMemo(() => {
    if (!data.chart?.ranges) return []
    return data.chart.ranges.filter((range): range is ChartRange => {
      return Boolean(range?.key && range.points && range.points.length)
    })
  }, [data.chart])

  const [activeKey, setActiveKey] = React.useState<string>(() => {
    if (data.chart?.default_range) return data.chart.default_range
    return ranges[0]?.key ?? ''
  })

  React.useEffect(() => {
    if (!ranges.length) return
    if (!ranges.find((range) => range.key === activeKey)) {
      const firstKey = ranges[0]?.key
      if (firstKey) {
        setActiveKey(firstKey)
      }
    }
  }, [ranges, activeKey])

  const chartData = React.useMemo(() => useChartData(ranges, activeKey), [ranges, activeKey])

  const priceDomain = React.useMemo(() => {
    if (!chartData.length) return undefined

    const firstFinitePoint = chartData.find((point) => Number.isFinite(point.price))
    if (!firstFinitePoint) {
      return undefined
    }

    let minPrice = firstFinitePoint.price
    let maxPrice = firstFinitePoint.price

    for (const point of chartData) {
      if (Number.isFinite(point.price)) {
        minPrice = Math.min(minPrice, point.price)
        maxPrice = Math.max(maxPrice, point.price)
      }
    }

    if (!Number.isFinite(minPrice) || !Number.isFinite(maxPrice)) {
      return undefined
    }

    const range = maxPrice - minPrice
    const padding = range === 0
      ? Math.max(Math.abs(maxPrice || minPrice) * 0.02, 0.5)
      : range * 0.08

    const lowerBound = minPrice >= 0 ? Math.max(minPrice - padding, 0) : minPrice - padding
    const upperBound = maxPrice + padding

    if (!Number.isFinite(lowerBound) || !Number.isFinite(upperBound)) {
      return undefined
    }

    return [lowerBound, upperBound] as [number, number]
  }, [chartData])

  const formatAxisTick = React.useCallback(
    (value: number): string => {
      if (!Number.isFinite(value)) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      if (activeKey === '1d') {
        return date.toLocaleTimeString(undefined, {
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        })
      }
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
      })
    },
    [activeKey]
  )

  const formatTooltipLabel = React.useCallback((label: unknown): string => {
    if (typeof label === 'number') {
      const date = new Date(label)
      if (!Number.isNaN(date.getTime())) {
        return date.toLocaleString(undefined, {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          hour12: false,
        })
      }
    }
    if (typeof label === 'string') {
      const parsed = Date.parse(label)
      if (!Number.isNaN(parsed)) {
        return formatTooltipLabel(parsed)
      }
      return label
    }
    return ''
  }, [])

  const summaryItems = React.useMemo(
    () => [
      { label: 'Open', value: formatCurrency(data.day_open, currencyCode) },
      { label: 'Day Low', value: formatCurrency(data.day_low, currencyCode) },
      { label: 'Day High', value: formatCurrency(data.day_high, currencyCode) },
      { label: 'Previous Close', value: formatCurrency(data.previous_close, currencyCode) },
      { label: 'Volume', value: formatCompactNumber(data.volume) },
      { label: 'Market Cap', value: formatCompactNumber(data.market_cap) },
      { label: '52W Low', value: formatCurrency(data.year_low, currencyCode) },
      { label: '52W High', value: formatCurrency(data.year_high, currencyCode) },
      { label: 'EPS (TTM)', value: formatNumber(data.eps) },
      { label: 'P/E Ratio', value: formatNumber(data.pe_ratio) },
    ],
    [currencyCode, data.day_open, data.day_low, data.day_high, data.previous_close, data.volume, data.market_cap, data.year_low, data.year_high, data.eps, data.pe_ratio]
  )

  const changeClass = data.change
    ? data.change > 0
      ? 'text-green-400'
      : 'text-red-400'
    : 'text-gray-300'

  const changeText = React.useMemo(() => {
    if (!isFiniteNumber(data.change)) return '—'
    const pct = isFiniteNumber(data.change_percent) ? ` (${data.change_percent.toFixed(2)}%)` : ''
    const sign = data.change > 0 ? '+' : ''
    return `${sign}${data.change.toFixed(2)}${pct}`
  }, [data.change, data.change_percent])

  return (
    <div className="bg-gradient-to-br from-gray-900/70 via-gray-900/30 to-gray-800/40 border border-gray-700/40 rounded-xl p-5 space-y-5 shadow-lg">
      <div className="flex flex-col gap-2">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <div className="text-xs uppercase tracking-wide text-gray-400">{symbol}</div>
            <div className="flex items-baseline gap-3 mt-1">
              <span className="text-3xl font-semibold text-white">
                {formatCurrency(data.price, currencyCode)}
              </span>
              <span className={`text-sm font-medium ${changeClass}`}>{changeText}</span>
            </div>
          </div>
          {data.as_of && (
            <div className="text-right text-xs text-gray-400">
              <div>As of</div>
              <div>{formatTimestamp(data.as_of)}</div>
            </div>
          )}
        </div>

        {ranges.length > 1 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {ranges.map((range) => (
              <button
                key={range.key}
                type="button"
                onClick={() => setActiveKey(range.key)}
                className={`px-3 py-1 text-xs font-medium rounded-md border transition-colors ${
                  activeKey === range.key
                    ? 'bg-blue-500/20 border-blue-400 text-blue-200'
                    : 'border-gray-700 text-gray-400 hover:text-gray-200'
                }`}
              >
                {range.label ?? range.key.toUpperCase()}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="h-64 w-full">
        {chartData.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#60a5fa" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="timestamp"
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                tickFormatter={formatAxisTick}
              />
              <YAxis
                stroke="#6b7280"
                tick={{ fontSize: 11 }}
                tickFormatter={(value: number) =>
                  formatCurrency(value, currencyCode).replace(/[^0-9.\-]/g, '')
                }
                domain={priceDomain ?? ['auto', 'auto']}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#111827',
                  border: '1px solid #1f2937',
                  borderRadius: '0.75rem',
                }}
                cursor={{ stroke: '#93c5fd', strokeWidth: 1, strokeDasharray: '4 4' }}
                formatter={(value: number) => [formatCurrency(value, currencyCode), 'Price']}
                labelFormatter={formatTooltipLabel}
              />
              <Area
                type="monotone"
                dataKey="price"
                stroke="#60a5fa"
                strokeWidth={2}
                fill="url(#priceGradient)"
                dot={false}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500 text-sm border border-dashed border-gray-700 rounded-lg">
            No chart data available
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-xs">
        {summaryItems.map((item) => (
          <div key={item.label} className="rounded-lg border border-gray-700/40 bg-gray-900/40 p-3">
            <div className="text-gray-400 uppercase tracking-wide text-[10px] mb-1">{item.label}</div>
            <div className="text-sm text-gray-100">{item.value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PriceQuoteCard
export type { QuoteData }
