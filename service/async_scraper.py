import re
import asyncio
import aiohttp
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
import dateparser
from datetime import datetime
from typing import List, Dict, Any


class AsyncScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.type_cache = {}
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def normalize_time(self, time_text):
        parsed = dateparser.parse(time_text, languages=["id", "en"])
        return parsed.isoformat() if parsed else datetime.now().isoformat()

    def normalize_text(self, text):
        if not text:
            return text

        normalized = re.sub(r"[\n\r\t\u000b\u000c\u0085\u2028\u2029]+", " ", text)
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    async def scrape(self, url=None):
        target_url = url if url else self.base_url
        async with self.session.get(target_url) as response:
            html = await response.text()
            return BeautifulSoup(html, "html.parser")

    async def get_komik_type_from_detail(self, slug):
        """Mengambil tipe komik dari halaman detail dengan async"""
        if slug in self.type_cache:
            return self.type_cache[slug]

        try:
            detail_url = f"{self.base_url}komik/{slug}/"
            soup = await self.scrape(detail_url)

            type_element = soup.select_one("span.komik_info-content-info-type a")
            if type_element:
                komik_type = type_element.get_text(strip=True)
            else:
                # Fallback
                type_elements = soup.find_all(
                    ["b", "strong"], string=re.compile(r"Type:|Tipe:", re.IGNORECASE)
                )
                komik_type = "Unknown"
                for element in type_elements:
                    next_sibling = element.next_sibling
                    if next_sibling and hasattr(next_sibling, "get_text"):
                        komik_type = next_sibling.get_text(strip=True)
                        break

            self.type_cache[slug] = komik_type
            return komik_type

        except Exception as e:
            print(f"Error getting type for {slug}: {e}")
            self.type_cache[slug] = "Unknown"
            return "Unknown"

    async def get_komik_types_batch(self, slugs: List[str]) -> Dict[str, str]:
        """Mengambil type untuk multiple slugs sekaligus dengan asyncio"""
        tasks = [self.get_komik_type_from_detail(slug) for slug in slugs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        type_mapping = {}
        for slug, result in zip(slugs, results):
            if isinstance(result, Exception):
                print(f"Error processing {slug}: {result}")
                type_mapping[slug] = "Unknown"
            else:
                type_mapping[slug] = result

        return type_mapping

    async def get_all_komik(self, page: int):
        url = f"{self.base_url}daftar-komik/page/{page}/"
        soup = await self.scrape(url)

        all_komik_data = []
        slugs = []

        # Kumpulkan data dasar dulu
        for uta in soup.select(".list-update_item"):
            komik_data = {
                "title": (
                    uta.find("h3").get_text(strip=True) if uta.find("h3") else None
                ),
                "slug": (
                    urlparse(uta.find("a")["href"]).path.strip("/").split("/")[-1]
                    if uta.find("a")
                    else None
                ),
                "rating": (
                    float(uta.select_one(".numscore").get_text(strip=True))
                    if uta.select_one(".numscore")
                    and uta.select_one(".numscore")
                    .get_text(strip=True)
                    .replace(".", "", 1)
                    .isdigit()
                    else None
                ),
                "latest_chapter": {
                    "title": (
                        uta.select_one(".chapter").get_text(strip=True)
                        if uta.select_one(".chapter")
                        else None
                    ),
                    "slug": (
                        urlparse(uta.select_one(".chapter")["href"])
                        .path.strip("/")
                        .split("/")[-1]
                        if uta.select_one(".chapter")
                        else None
                    ),
                },
                "thumbnail": (
                    uta.find("img")["data-src"]
                    if uta.find("img") and uta.find("img").has_attr("data-src")
                    else uta.find("img")["src"] if uta.find("img") else None
                ),
                "type": "Unknown",  # Default value
            }

            if komik_data["slug"]:
                slugs.append(komik_data["slug"])

            all_komik_data.append(komik_data)

        # Ambil type untuk semua komik sekaligus dengan async
        if slugs:
            type_mapping = await self.get_komik_types_batch(slugs)
            for komik in all_komik_data:
                if komik["slug"] and komik["slug"] in type_mapping:
                    komik["type"] = type_mapping[komik["slug"]]

        has_next_page = bool(
            soup.select('a.next.page-numbers, .next.page-numbers, a[rel="next"]')
        )

        return all_komik_data, has_next_page

    async def get_latest_komik(self):
        soup = await self.scrape()

        latest_release_data = []
        slugs = []

        # Kumpulkan data dasar dulu
        for uta in soup.select(".listupd .uta"):
            komik_data = {
                "title": (
                    uta.find("h3").get_text(strip=True) if uta.find("h3") else None
                ),
                "slug": (
                    urlparse(uta.find("a", class_="series")["href"])
                    .path.strip("/")
                    .split("/")[-1]
                    if uta.find("a", class_="series")
                    else None
                ),
                "thumbnail": (
                    uta.find("img")["data-src"]
                    if uta.find("img") and uta.find("img").has_attr("data-src")
                    else uta.find("img")["src"] if uta.find("img") else None
                ),
                "latest_chapter": {
                    "title": (
                        self.normalize_text(
                            uta.select_one("ul li a").get_text(strip=True)
                        )
                        if uta.select_one("ul li a")
                        else None
                    ),
                    "slug": (
                        urlparse(uta.select_one("ul li a")["href"])
                        .path.strip("/")
                        .split("/")[-1]
                        if uta.select_one("ul li a")
                        else None
                    ),
                },
                "updated_at": (
                    self.normalize_time(
                        uta.select_one("ul li span i").get_text(strip=True)
                    )
                    if uta.select_one("ul li span i")
                    else None
                ),
                "type": "Unknown",  # Default value
            }

            if komik_data["slug"]:
                slugs.append(komik_data["slug"])

            latest_release_data.append(komik_data)

        # Ambil type untuk semua komik sekaligus dengan async
        if slugs:
            type_mapping = await self.get_komik_types_batch(slugs)
            for komik in latest_release_data:
                if komik["slug"] and komik["slug"] in type_mapping:
                    komik["type"] = type_mapping[komik["slug"]]

        return latest_release_data

    async def search_komik(self, query: str, page: int):
        encoded_query = quote(query)

        if page > 1:
            search_url = f"{self.base_url}/page/{page}/?s={encoded_query}"
        else:
            search_url = f"{self.base_url}?s={encoded_query}"

        soup = await self.scrape(search_url)

        search_data = []
        slugs = []

        # Kumpulkan data dasar dulu
        for uta in soup.select(".list-update_item"):
            komik_data = {
                "title": (
                    uta.find("h3").get_text(strip=True) if uta.find("h3") else None
                ),
                "slug": (
                    urlparse(uta.find("a")["href"]).path.strip("/").split("/")[-1]
                    if uta.find("a")
                    else None
                ),
                "rating": (
                    float(uta.select_one(".numscore").get_text(strip=True))
                    if uta.select_one(".numscore")
                    and uta.select_one(".numscore")
                    .get_text(strip=True)
                    .replace(".", "", 1)
                    .isdigit()
                    else None
                ),
                "latest_chapter": {
                    "title": (
                        uta.select_one(".chapter").get_text(strip=True)
                        if uta.select_one(".chapter")
                        else None
                    ),
                    "slug": (
                        urlparse(uta.select_one(".chapter")["href"])
                        .path.strip("/")
                        .split("/")[-1]
                        if uta.select_one(".chapter")
                        else None
                    ),
                },
                "thumbnail": (
                    uta.find("img")["data-src"]
                    if uta.find("img") and uta.find("img").has_attr("data-src")
                    else uta.find("img")["src"] if uta.find("img") else None
                ),
                "type": "Unknown",  # Default value
            }

            if komik_data["slug"]:
                slugs.append(komik_data["slug"])

            search_data.append(komik_data)

        # Ambil type untuk semua komik sekaligus dengan async
        if slugs:
            type_mapping = await self.get_komik_types_batch(slugs)
            for komik in search_data:
                if komik["slug"] and komik["slug"] in type_mapping:
                    komik["type"] = type_mapping[komik["slug"]]

        has_next_page = bool(
            soup.select('a.next.page-numbers, .next.page-numbers, a[rel="next"]')
        )

        return search_data, has_next_page

    async def get_komik_detail(self, href):
        detail_url = self.base_url + href
        soup = await self.scrape(detail_url)

        title = soup.find("h1", itemprop="headline").get_text(strip=True)
        synopsis = self.normalize_text(
            soup.select_one('[itemprop="articleBody"]').get_text(strip=True)
        )
        komik_type = soup.select_one("span.komik_info-content-info-type a").get_text(
            strip=True
        )
        status = soup.select_one(
            "span.komik_info-content-info b:contains('Status:')"
        ).next_sibling.get_text(strip=True)
        rating = (
            float(soup.select_one(".data-rating").get("data-ratingkomik"))
            if soup.select_one(".data-rating").get("data-ratingkomik")
            else None
        )
        genres = [g.text for g in soup.select("span.komik_info-content-genre a")]
        thumbnail = soup.select_one("[itemprop='image'] img").get("src")
        chapter_time = soup.select("ul#chapter-wrapper li .chapter-link-time")
        chapters = [
            {
                "title": self.normalize_text(c.text),
                "slug": urlparse(c["href"]).path.strip("/").split("/")[-1],
                "released_at": self.normalize_time(chapter_time[i].text.strip()),
            }
            for i, c in enumerate(soup.select("ul#chapter-wrapper li a"))
        ]

        return {
            "title": title,
            "thumbnail": thumbnail,
            "synopsis": synopsis,
            "type": komik_type,
            "status": status,
            "rating": rating,
            "genres": genres,
            "chapters": chapters,
        }

    async def get_chapter(self, href):
        chapter_url = self.base_url + href
        soup = await self.scrape(chapter_url)

        chap = soup.select(".main-reading-area img")
        images = [c.get("src") for c in chap]
        title = soup.select_one("h1[itemprop='name']").get_text(strip=True)
        next_chapter = (
            urlparse(soup.select_one(".nextprev > [rel='next']").get("href"))
            .path.strip("/")
            .split("/")[-1]
            if soup.select_one(".nextprev > [rel='next']")
            else None
        )
        prev_chapter = (
            urlparse(soup.select_one(".nextprev > [rel='prev']").get("href"))
            .path.strip("/")
            .split("/")[-1]
            if soup.select_one(".nextprev > [rel='prev']")
            else None
        )

        return {
            "title": title,
            "next_chapter_slug": next_chapter,
            "previous_chapter_slug": prev_chapter,
            "images": images,
        }
