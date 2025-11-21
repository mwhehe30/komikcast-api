import asyncio
from .async_scraper import AsyncScraper


class AsyncScraperAdapter:
    def __init__(self, base_url):
        self.base_url = base_url

    def _run_async(self, coroutine):
        """Run async coroutine in sync context"""
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            # Fallback for environments where asyncio.run might fail (e.g. existing loop)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coroutine)

    def get_all_komik(self, page):
        async def wrapper():
            async with AsyncScraper(self.base_url) as scraper:
                return await scraper.get_all_komik(page)

        return self._run_async(wrapper())

    def get_latest_komik(self):
        async def wrapper():
            async with AsyncScraper(self.base_url) as scraper:
                return await scraper.get_latest_komik()

        return self._run_async(wrapper())

    def get_komik_detail(self, slug):
        async def wrapper():
            async with AsyncScraper(self.base_url) as scraper:
                return await scraper.get_komik_detail(slug)

        return self._run_async(wrapper())

    def get_chapter(self, slug):
        async def wrapper():
            async with AsyncScraper(self.base_url) as scraper:
                return await scraper.get_chapter(slug)

        return self._run_async(wrapper())

    def search_komik(self, query, page):
        async def wrapper():
            async with AsyncScraper(self.base_url) as scraper:
                return await scraper.search_komik(query, page)

        return self._run_async(wrapper())
