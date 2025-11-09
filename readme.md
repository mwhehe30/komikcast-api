# API Documentation

This API provides access to manga data from KomikCast, a popular Indonesian manga website. The API allows you to retrieve manga lists, details, chapters, and search functionality.

## Base URL

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
  "page": 1,
  "count": 20,
  "data": [
    {
      "title": "Manga Title",
      "slug": "manga-slug",
      "rating": "8.5",
      "latest_chapter": {
        "label": "Chapter 123",
        "link": "chapter-slug"
      },
      "image": "https://example.com/image.jpg"
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
  "data": [
    {
      "title": "Latest Manga Title",
      "slug": "manga-slug",
      "image": "https://example.com/image.jpg",
      "latest_chapter": {
        "label": "Chapter 45",
        "link": "chapter-slug"
      },
      "update_time": "2025-11-09T12:34:56+00:00"
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

- `slug`: The unique identifier for the manga

#### Response

```json
{
  "data": {
    "title": "Manga Title",
    "image": "https://example.com/image.jpg",
    "synopsis": "Detailed manga description...",
    "type": "Manga",
    "status": "Ongoing",
    "rating": "9.0",
    "genres": ["Action", "Adventure", "Comedy"],
    "chapters": [
      {
        "label": "Chapter 1",
        "link": "chapter-slug",
        "chapter_release": "2025-11-01T10:00:00+00:00"
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

- `slug`: The unique identifier for the chapter

#### Response

```json
{
  "data": {
    "title": "Chapter Title",
    "next_chapter": "next-chapter-slug",
    "prev_chapter": "prev-chapter-slug",
    "chapter": [
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
  "query": "attack on titan",
  "page": 1,
  "results": [
    {
      "title": "Attack on Titan",
      "slug": "attack-on-titan",
      "image": "https://example.com/image.jpg"
    }
  ],
  "total": 1
}
```

## Error Responses

All endpoints return standard error responses when needed:

```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

### Common Error Codes

- `400`: Bad Request - Missing required parameters
- `404`: Not Found - Resource does not exist
- `500`: Internal Server Error - Internal processing error
- `502`: Network Error - Error connecting to upstream service

## CORS Policy

This API has CORS enabled and allows requests from any origin.

## Dependencies

This API is built with:

- Flask
- BeautifulSoup for HTML parsing
- Requests for HTTP handling
- Dateparser for time normalization

## Rate Limiting

Note that this API scrapes data from KomikCast. Please be respectful of their servers and avoid making excessive requests in a short period of time.
