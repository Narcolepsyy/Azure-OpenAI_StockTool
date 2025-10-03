import asyncio
import logging
from app.services.perplexity_web_search import BraveSearchClient

async def main():
    query = 'SBI住信ネット銀行 顧客基盤 成長戦略 2025'
    async with BraveSearchClient() as client:
        print('is_available:', client.is_available)
        results = await client.search(query, count=5, freshness='pw')
        print('results_count:', len(results))
        for r in results[:3]:
            print('-', r.get('title'), '\n  ', r.get('url'))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s:%(message)s')
    asyncio.run(main())
