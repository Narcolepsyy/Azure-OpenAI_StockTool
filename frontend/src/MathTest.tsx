import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeRaw from 'rehype-raw'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import './katex-dark.css'

const MathTest = () => {
  const sampleContent = `
# 20日間平均出来高の計算例

## 基本的な計算式

20日間の平均出来高を計算：

$$\\text{平均出来高} = \\frac{\\text{合計出来高}}{20}$$

合計出来高 = 1,142,100 + 1,026,000 + ... + 1,650,000 = 1,300,000 (仮に)

$$\\text{平均出来高} = \\frac{1,300,000}{20} = 65,000$$

## 本日の出来高との比較

$$\\text{増減率} = \\left(\\frac{\\text{本日の出来高} - \\text{平均出来高}}{\\text{平均出来高}}\\right) \\times 100$$

ここで、本日の出来高が仮に2,000,000とすると：

$$\\text{増減率} = \\left(\\frac{2,000,000 - 65,000}{65,000}\\right) \\times 100 \\approx 2,976.9\\%$$

## インライン数式の例

本日の出来高 $V_t = 2,000,000$ が平均出来高 $\\overline{V} = 65,000$ を大幅に上回っている。

変化率は $\\Delta V = \\frac{V_t - \\overline{V}}{\\overline{V}} \\times 100\\% \\approx 2,976.9\\%$ となります。

## 統計的指標

- 標準偏差: $\\sigma = \\sqrt{\\frac{1}{n}\\sum_{i=1}^{n}(V_i - \\overline{V})^2}$
- Zスコア: $Z = \\frac{V_t - \\overline{V}}{\\sigma}$
- 相対強度指数 (RSI): $RSI = 100 - \\frac{100}{1 + RS}$

**注意**: この計算は教育目的のデモンストレーションです。
`

  return (
    <div style={{ 
      backgroundColor: '#111827', 
      color: '#e5e7eb', 
      padding: '2rem', 
      minHeight: '100vh',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    }}>
      <h1 style={{ color: '#ffffff', marginBottom: '2rem' }}>KaTeX Mathematical Rendering Test</h1>
      <div className="prose prose-lg max-w-none">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeRaw, rehypeKatex]}
          className="text-gray-100"
          components={{
            p: ({children}) => <p style={{color: '#e5e7eb', lineHeight: '1.7', marginBottom: '1rem'}}>{children}</p>,
            h1: ({children}) => <h1 style={{color: '#ffffff', fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem'}}>{children}</h1>,
            h2: ({children}) => <h2 style={{color: '#ffffff', fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '0.75rem'}}>{children}</h2>,
            h3: ({children}) => <h3 style={{color: '#ffffff', fontSize: '1.125rem', fontWeight: 'bold', marginBottom: '0.5rem'}}>{children}</h3>,
            ul: ({children}) => <ul style={{color: '#e5e7eb', marginLeft: '1.5rem', listStyle: 'disc'}}>{children}</ul>,
            li: ({children}) => <li style={{color: '#e5e7eb', marginBottom: '0.25rem'}}>{children}</li>,
            strong: ({children}) => <strong style={{color: '#ffffff', fontWeight: 'bold'}}>{children}</strong>,
          }}
        >
          {sampleContent}
        </ReactMarkdown>
      </div>
    </div>
  )
}

export default MathTest