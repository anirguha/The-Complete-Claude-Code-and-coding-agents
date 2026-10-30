"""A small Confluence Cloud client for storing saved documents as pages.

Pages use the v2 REST API; attachments use v1, which v2 cannot upload. Configured from the environment:
ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN, CONFLUENCE_URL (e.g. https://acme.atlassian.net/wiki) and
CONFLUENCE_SPACE_KEY.
"""

import os
from dataclasses import dataclass
from functools import cached_property

import httpx


class ConfluenceError(Exception):
    """Confluence could not be reached or rejected a request."""


@dataclass(frozen=True)
class Page:
    id: str
    url: str


class Confluence:
    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        space_key: str,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.space_key = space_key
        self.http = httpx.Client(
            base_url=self.base_url,
            auth=(email, api_token),
            timeout=30,
            follow_redirects=True,
            transport=transport,
        )

    @classmethod
    def from_env(cls) -> "Confluence | None":
        """The configured client, or None when the environment does not set up Confluence."""
        names = ("CONFLUENCE_URL", "ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN", "CONFLUENCE_SPACE_KEY")
        values = [os.environ.get(name, "").strip() for name in names]
        return cls(*values) if all(values) else None

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = self.http.request(method, url, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ConfluenceError(f"{method} {url} failed: {error.response.status_code} {error.response.text[:300]}")
        except httpx.HTTPError as error:
            raise ConfluenceError(f"{method} {url} failed: {error}")
        return response

    @cached_property
    def space_id(self) -> str:
        results = self._request("GET", "/api/v2/spaces", params={"keys": self.space_key}).json()["results"]
        if not results:
            raise ConfluenceError(f"Confluence space {self.space_key!r} not found")
        return results[0]["id"]

    def _page(self, data: dict) -> Page:
        return Page(id=data["id"], url=self.base_url + data["_links"]["webui"])

    @staticmethod
    def _content(title: str, body: str) -> dict:
        return {"status": "current", "title": title, "body": {"representation": "storage", "value": body}}

    def create_page(self, title: str, body: str) -> Page:
        data = self._request("POST", "/api/v2/pages", json={"spaceId": self.space_id, **self._content(title, body)})
        return self._page(data.json())

    def update_page(self, page_id: str, title: str, body: str) -> Page:
        version = self._request("GET", f"/api/v2/pages/{page_id}").json()["version"]["number"]
        data = self._request(
            "PUT",
            f"/api/v2/pages/{page_id}",
            json={"id": page_id, **self._content(title, body), "version": {"number": version + 1}},
        ).json()
        return self._page(data)

    def delete_page(self, page_id: str) -> None:
        self._request("DELETE", f"/api/v2/pages/{page_id}")

    def attach(self, page_id: str, filename: str, content: bytes, media_type: str) -> None:
        """Adds the file to the page, or replaces an attachment with the same name."""
        self._request(
            "PUT",
            f"/rest/api/content/{page_id}/child/attachment",
            headers={"X-Atlassian-Token": "no-check"},
            files={"file": (filename, content, media_type)},
            data={"minorEdit": "true"},
        )

    def read_attachment(self, page_id: str, filename: str) -> bytes:
        results = self._request(
            "GET", f"/rest/api/content/{page_id}/child/attachment", params={"filename": filename}
        ).json()["results"]
        if not results:
            raise ConfluenceError(f"Page {page_id} has no attachment {filename!r}")
        return self._request("GET", results[0]["_links"]["download"]).content
