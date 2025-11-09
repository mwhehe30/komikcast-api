from flask import Blueprint, jsonify
from service.async_adapter import AsyncScraperAdapter  # Ganti ini
from flask import request
import requests

komikcast = Blueprint("komikcast", __name__)

BASE_URL = "https://komikcast03.com/"


@komikcast.route("/komikcast", defaults={"page": 1})
@komikcast.route("/komikcast/<int:page>")
def scraper_page(page):
    try:
        scraper = AsyncScraperAdapter(BASE_URL)  # Ganti ini
        data, has_next_page = scraper.get_all_komik(page)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Successfully retrieved manga list",
                    "meta": {
                        "page": page,
                        "total_count": len(data),
                        "next_page": page + 1 if has_next_page else None,
                        "prev_page": page - 1 if page > 1 else None,
                    },
                    "data": data,
                }
            ),
            200,
        )
    except requests.exceptions.RequestException as e:
        return (
            jsonify({"success": False, "error": "Network error", "message": str(e)}),
            502,
        )
    except Exception as e:
        return (
            jsonify({"success": False, "error": "Internal error", "message": str(e)}),
            500,
        )


@komikcast.route("/komikcast/latest")
def scraper_latest():
    try:
        scraper = AsyncScraperAdapter(BASE_URL)  # Ganti ini
        data = scraper.get_latest_komik()
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Successfully retrieved latest manga",
                    "meta": {"total_count": len(data)},
                    "data": data,
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify({"success": False, "error": "Internal error", "message": str(e)}),
            500,
        )


@komikcast.route("/komikcast/detail/<string:slug>")
def scraper_detail(slug):
    try:
        if "/komik/" in slug:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Invalid URL structure",
                        "message": "Invalid URL structure",
                    }
                ),
                404,
            )

        scraper = AsyncScraperAdapter(BASE_URL)  # Ganti ini
        data = scraper.get_komik_detail(slug)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Successfully retrieved manga details",
                    "data": data,
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify({"success": False, "error": "Internal error", "message": str(e)}),
            500,
        )


@komikcast.route("/komikcast/chapter/<string:slug>")
def scraper_chapter(slug):
    try:
        scraper = AsyncScraperAdapter(BASE_URL)  # Ganti ini
        data = scraper.get_chapter(slug)
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Successfully retrieved chapter images",
                    "data": data,
                }
            ),
            200,
        )
    except Exception as e:
        return (
            jsonify({"success": False, "error": "Internal error", "message": str(e)}),
            500,
        )


@komikcast.route("/komikcast/search", methods=["GET"])
def search_comics():
    query = request.args.get("q", "")
    page = request.args.get("page", 1, type=int)

    if not query:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Bad Request",
                    "message": 'Query parameter "q" is required',
                }
            ),
            400,
        )

    if page < 1:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Bad Request",
                    "message": "Page number must be greater than 0",
                }
            ),
            400,
        )

    try:
        scraper = AsyncScraperAdapter(BASE_URL)  # Ganti ini
        results, has_next_page = scraper.search_komik(query, page)

        if not results and page > 1:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Not Found",
                        "message": f"No results found for page {page}",
                        "meta": {
                            "query": query,
                            "page": page,
                            "total_count": 0,
                            "suggestion": "Try a lower page number or different query",
                        },
                        "data": [],
                    }
                ),
                404,
            )

        if not results:
            return jsonify(
                {
                    "success": True,
                    "message": "No comics found for your search query",
                    "meta": {
                        "query": query,
                        "page": page,
                        "total_count": 0,
                    },
                    "data": [],
                }
            )

        return jsonify(
            {
                "success": True,
                "message": "Successfully retrieved search results",
                "meta": {
                    "query": query,
                    "page": page,
                    "total_count": len(results),
                    "pagination": {
                        "current_page": page,
                        "previous_page": page - 1 if page > 1 else None,
                        "next_page": page + 1 if has_next_page else None,
                    },
                },
                "data": results,
            }
        )

    except Exception as e:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal error",
                    "message": f"An error occurred while searching: {str(e)}",
                }
            ),
            500,
        )
