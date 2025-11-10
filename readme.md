# Unofficial KomikCast API Documentation

This is an unofficial API that provides access to manga data from KomikCast, a popular Indonesian manga website. The API allows you to retrieve manga lists, details, chapters, and perform searches, all with proper pagination and error handling.

## Base URL

```
https://unofficial-komikcast-api.vercel.app  # Production URL
```
```
http://localhost:5000  # Default development URL
```

## Endpoints

### 1. Get All Manga

Retrieve a paginated list of all manga available on the site.

#### Endpoint
```
GET /komikcast[/<int:page>]
```

#### Parameters
- `page` (optional, default: 1): Page number for pagination

#### Response
```json
{
  "success": true,
  "message": "Successfully retrieved manga list",
  "meta": {
    "page": 1,
    "total_count": 20,
    "next_page": 2,
    "prev_page": null
  },
  "data": [
    {
      "title": "Manga Title",
      "slug": "manga-slug",
      "rating": 8.5,
      "latest_chapter": {
        "title": "Chapter 123",
        "slug": "chapter-slug"
      },
      "thumbnail": "https://example.com/image.jpg",
      "type": "Manga"
    }
  ]
}
```

### 2. Get Latest Manga

Retrieve the latest manga releases from the site.

#### Endpoint
```
GET /komikcast/latest
```

#### Response
```json
{
  "success": true,
  "message": "Successfully retrieved latest manga",
  "meta": {
    "total_count": 10
  },
  "data": [
    {
      "title": "Latest Manga Title",
      "slug": "manga-slug",
      "thumbnail": "https://example.com/image.jpg",
      "latest_chapter": {
        "title": "Chapter 45",
        "slug": "chapter-slug"
      },
      "updated_at": "2025-11-10T10:30:00+00:00",
      "type": "Manhwa"
    }
  ]
}
```

### 3. Get Manga Detail

Retrieve detailed information about a specific manga.

#### Endpoint
```
GET /komikcast/detail/<string:slug>
```

#### Parameters
- `slug`: The unique identifier for the manga (without "/komik/" prefix)

#### Response
```json
{
  "success": true,
  "message": "Successfully retrieved manga details",
  "data": {
    "title": "Manga Title",
    "thumbnail": "https://example.com/image.jpg",
    "synopsis": "Detailed manga description...",
    "type": "Manga",
    "status": "Ongoing",
    "rating": 9.0,
    "genres": ["Action", "Adventure", "Comedy"],
    "chapters": [
      {
        "title": "Chapter 1",
        "slug": "chapter-slug",
        "released_at": "2025-11-01T10:00:00+00:00"
      }
    ]
  }
}
```

### 4. Get Chapter Content

Retrieve chapter images and navigation links.

#### Endpoint
```
GET /komikcast/chapter/<string:slug>
```

#### Parameters
- `slug`: The unique identifier for the chapter (without "/chapter/" prefix)

#### Response
```json
{
  "success": true,
  "message": "Successfully retrieved chapter images",
  "data": {
    "title": "Chapter Title",
    "next_chapter_slug": "next-chapter-slug",
    "previous_chapter_slug": "prev-chapter-slug",
    "images": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg",
      "https://example.com/image3.jpg"
    ]
  }
}
```

### 5. Search Manga

Search for manga by title or other keywords.

#### Endpoint
```
GET /komikcast/search
```

#### Query Parameters
- `q` (required): Search query string
- `page` (optional, default: 1): Page number for pagination

#### Response
```json
{
  "success": true,
  "message": "Successfully retrieved search results",
  "meta": {
    "query": "attack on titan",
    "page": 1,
    "total_count": 5,
    "pagination": {
      "current_page": 1,
      "previous_page": null,
      "next_page": 2
    }
  },
  "data": [
    {
      "title": "Attack on Titan",
      "slug": "attack-on-titan",
      "rating": 9.5,
      "latest_chapter": {
        "title": "Chapter 139",
        "slug": "chapter-139"
      },
      "thumbnail": "https://example.com/image.jpg",
      "type": "Manga"
    }
  ]
}
```

## Home Endpoint

Get information about the API.

#### Endpoint
```
GET /
```

#### Response
```json
{
  "message": "Welcome to the API",
  "name": "Unofficial KomikCast API",
  "description": "API for scraping komikcast",
  "author": "Mwhehe30",
  "docs": "https://github.com/mwhehe30/komikcast-api",
  "version": "1.0.0"
}
```

## Error Responses

All endpoints return standard error responses when needed:

```json
{
  "success": false,
  "error": "Error message",
  "message": "Detailed error description"
}
```

### Common Error Codes
- `400`: Bad Request - Missing required parameters (for search)
- `404`: Not Found - Resource does not exist or endpoint not found
- `500`: Internal Server Error - Internal processing error
- `502`: Network Error - Error connecting to upstream service (KomikCast)

## CORS Policy

This API has CORS enabled and allows requests from any origin.

## Dependencies

This API is built with:
- Flask
- BeautifulSoup for HTML parsing
- Requests for HTTP handling
- Dateparser for time normalization
- aiohttp for async requests
- Flask-CORS for cross-origin resource sharing

## Rate Limiting

Note that this API scrapes data from KomikCast. Please be respectful of their servers and avoid making excessive requests in a short period of time. The API uses async scraping to be efficient and respectful of upstream resources.

## Important Notes

- All manga and chapter data is scraped from KomikCast in real-time
- Manga slugs are the URL-friendly identifiers used to access manga details
- Chapter slugs are the URL-friendly identifiers used to access chapter content
- The API normalizes text and time data to ensure consistent responses
- Thumbnail and image URLs are directly from KomikCast and may change

## Example Usage

Here are some example cURL commands:

```bash
# Get first page of manga
curl https://unofficial-komikcast-api.vercel.app/komikcast

# Get second page of manga
curl https://unofficial-komikcast-api.vercel.app/komikcast/2

# Get latest manga releases
curl https://unofficial-komikcast-api.vercel.app/komikcast/latest

# Get manga details by slug
curl https://unofficial-komikcast-api.vercel.app/komikcast/detail/gintama

# Get chapter content by slug
curl https://unofficial-komikcast-api.vercel.app/komikcast/chapter/gintama-001

# Search for manga
curl "https://unofficial-komikcast-api.vercel.app/komikcast/search?q=naruto&page=1"
```

## Contributing

This API is built and maintained by Mwhehe30. If you find any issues or have suggestions, please check the GitHub repository for the latest updates and contributions.

## License

This is an unofficial API. All manga content is owned by their respective creators and publishers. This API is for educational and personal use only.
