# HTTP-caching

## Introduction
`Rapidy` allows efficient HTTP caching using standard headers like `ETag`, `Cache-Control`, `Last-Modified`, and `Expires`.
These headers help browsers and API clients cache content and reduce server load.

## Using `ETag` and `If-None-Match`
The `ETag` header enables the server to identify a unique version of a resource. The client can send the `If-None-Match` header, allowing the server to check
if the resource version has changed since the last request.
```python
{!> ./examples/http_caching/etag_and_if_none_match.py !}
```

## Using `Last-Modified` and `If-Modified-Since`
The `Last-Modified` header specifies the date when a resource was last modified. The client can send the `If-Modified-Since` header to check
whether the resource has been updated since the last request.
```python
{!> ./examples/http_caching/last_modified_and_if_modified_since.py !}
```

## Using `Cache-Control`
The `Cache-Control` header manages caching policies and defines how long a resource can be stored in the cache.
```python
{!> ./examples/http_caching/cache_control.py !}
```

## Using `Expires`
The `Expires` header sets a specific expiration time for the cache.
```python
{!> ./examples/http_caching/expires.py !}
```

## Combined Example
This example demonstrates the use of all major caching headers:
```python
{!> ./examples/http_caching/all_cache.py !}
```

## Conclusion
Using HTTP caching in `Rapidy` significantly reduces server load, speeds up request processing, and minimizes data transfer.
By combining `ETag`, `Cache-Control`, `Last-Modified`, and `Expires` headers, you can flexibly manage content caching based on your application's requirements.
