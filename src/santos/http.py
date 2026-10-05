from urllib.request import Request, urlopen


class HttpResponse:
    def __init__(self, status: int, headers: dict[str, str], body: bytes):
        self.status = status
        self.headers = headers
        self.body = body


def http_fetch(url: str, headers: dict[str, str]) -> HttpResponse:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request) as response:
            return HttpResponse(
                response.status,
                {key.lower(): value for key, value in response.headers.items()},
                response.read(),
            )
    except Exception as exc:
        status = getattr(exc, "code", None)
        if status is None:
            raise
        payload = exc.read() if hasattr(exc, "read") else b""
        header_items = getattr(getattr(exc, "headers", None), "items", lambda: [])()
        return HttpResponse(
            status,
            {key.lower(): value for key, value in header_items},
            payload,
        )
