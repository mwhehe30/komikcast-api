import re
import asyncio
import aiohttp
import json
import os
from urllib.parse import quote, urlparse
from bs4 import BeautifulSoup
import dateparser
from datetime import datetime
import tempfile
from typing import List, Dict, Any


class AsyncScraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = None
        self.cache_file = os.path.join(tempfile.gettempdir(), "komik_types.json")
        self.type_cache = self._load_cache()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        }

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.type_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving cache: {e}")

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        # Save cache on exit
        self._save_cache()

    def normalize_time(self, time_text):
        if not time_text:
            return datetime.now().isoformat()
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
            return BeautifulSoup(html, "lxml")

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
            return "Unknown"

    async def get_komik_types_batch(self, slugs: List[str]) -> Dict[str, str]:
        """Mengambil type untuk multiple slugs sekaligus dengan asyncio"""
        slugs_to_fetch = [slug for slug in slugs if slug not in self.type_cache]

        if slugs_to_fetch:
            tasks = [self.get_komik_type_from_detail(slug) for slug in slugs_to_fetch]
            await asyncio.gather(*tasks, return_exceptions=True)
            # Cache is updated in get_komik_type_from_detail

        return {slug: self.type_cache.get(slug, "Unknown") for slug in slugs}

    def _extract_type_from_list(self, element):
        """Helper to extract type from an element if available (e.g. search results)"""
        type_element = element.select_one("span.type")
        if type_element:
            type_text = type_element.get_text(strip=True)
            class_list = type_element.get("class", [])
            if "manga-bg" in class_list:
                return "Manga"
            elif "manhwa-bg" in class_list:
                return "Manhwa"
            elif "manhua-bg" in class_list:
                return "Manhua"
            return type_text if type_text else "Unknown"
        return "Unknown"

    async def get_all_komik(self, page: int):
        url = f"{self.base_url}daftar-komik/page/{page}/"
        soup = await self.scrape(url)

        all_komik_data = []
        slugs = []

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
                "type": "Unknown",
            }

            if komik_data["slug"]:
                slugs.append(komik_data["slug"])

            all_komik_data.append(komik_data)

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

        for uta in soup.select(".bixbox .listupd:not(.project) .uta"):
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
                "type": "Unknown",
            }

            if komik_data["slug"]:
                slugs.append(komik_data["slug"])

            latest_release_data.append(komik_data)

        if slugs:
            # Fetch types for current slugs
            type_mapping = await self.get_komik_types_batch(slugs)
            for komik in latest_release_data:
                if komik["slug"] and komik["slug"] in type_mapping:
                    komik["type"] = type_mapping[komik["slug"]]

            # PRUNE CACHE: Keep only slugs that are in the current latest list
            # Note: This is aggressive. It means if you visit 'get_all_komik', those types are cached,
            # but if you then visit 'get_latest_komik', they are wiped if not in latest.
            # Based on user request "yg sudah tidak ada di latest update... dihapus judulnya", this is correct.
            self.type_cache = {k: v for k, v in self.type_cache.items() if k in slugs}
            self._save_cache()

        return latest_release_data

    async def search_komik(self, query: str, page: int):
        encoded_query = quote(query)

        if page > 1:
            search_url = f"{self.base_url}/page/{page}/?s={encoded_query}"
        else:
            search_url = f"{self.base_url}?s={encoded_query}"

        soup = await self.scrape(search_url)

        search_data = []

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
                "type": self._extract_type_from_list(uta),
            }

            search_data.append(komik_data)

        has_next_page = bool(
            soup.select('a.next.page-numbers, .next.page-numbers, a[rel="next"]')
        )

        return search_data, has_next_page

    async def get_komik_detail(self, href):
        detail_url = self.base_url + href
        soup = await self.scrape(detail_url)

        title_elem = soup.find("h1", itemprop="headline")
        title = title_elem.get_text(strip=True) if title_elem else ""

        synopsis_elem = soup.select_one('[itemprop="articleBody"]')
        synopsis = self.normalize_text(synopsis_elem.get_text(strip=True)) if synopsis_elem else ""

        type_elem = soup.select_one("span.komik_info-content-info-type a")
        komik_type = type_elem.get_text(strip=True) if type_elem else "Unknown"

        status_elem = soup.select_one("span.komik_info-content-info b:contains('Status:')")
        status = status_elem.next_sibling.get_text(strip=True) if status_elem and status_elem.next_sibling else "Unknown"

        rating_elem = soup.select_one(".data-rating")
        rating = (
            float(rating_elem.get("data-ratingkomik"))
            if rating_elem and rating_elem.get("data-ratingkomik")
            else None
        )

        genres = [g.text for g in soup.select("span.komik_info-content-genre a")]

        img_elem = soup.select_one("[itemprop='image'] img")
        thumbnail = img_elem.get("src") if img_elem else None

        chapter_time = soup.select("ul#chapter-wrapper li .chapter-link-time")
        chapter_links = soup.select("ul#chapter-wrapper li a")

        chapters = []
        for i, c in enumerate(chapter_links):
            time_text = chapter_time[i].text.strip() if i < len(chapter_time) else ""
            chapters.append({
                "title": self.normalize_text(c.text),
                "slug": urlparse(c["href"]).path.strip("/").split("/")[-1],
                "released_at": self.normalize_time(time_text),
            })

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

        komik_link = soup.select_one(".allc a")
        komik_slug = komik_link.get("href").rstrip("/").split("/")[-1] if komik_link else None

        images = [c.get("src") for c in chap if c.get("src")]

        title_elem = soup.select_one("h1[itemprop='name']")
        title = title_elem.get_text(strip=True) if title_elem else ""

        next_elem = soup.select_one(".nextprev > [rel='next']")
        next_chapter = (
            urlparse(next_elem.get("href")).path.strip("/").split("/")[-1]
            if next_elem
            else None
        )

        prev_elem = soup.select_one(".nextprev > [rel='prev']")
        prev_chapter = (
            urlparse(prev_elem.get("href")).path.strip("/").split("/")[-1]
            if prev_elem
            else None
        )

        return {
            "title": title,
            "komik_slug": komik_slug,
            "next_chapter_slug": next_chapter,
            "previous_chapter_slug": prev_chapter,
            "images": images,
        }
