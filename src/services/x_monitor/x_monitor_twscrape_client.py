"""Thin twscrape adapter for X monitor collection."""

from datetime import UTC, datetime
import inspect


def _payload_get(payload, key: str):
    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)


def _coerce_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(UTC)


def _extract_raw_json(post) -> dict:
    if isinstance(post, dict):
        return dict(post)
    if hasattr(post, "dict") and callable(post.dict):
        return post.dict()
    if hasattr(post, "__dict__"):
        return {
            key: value
            for key, value in vars(post).items()
            if not callable(value) and not key.startswith("_")
        }
    return {}


def _normalize_post(post) -> dict:
    if isinstance(post, dict):
        payload = post
        author = payload.get("user", {}) or {}
    else:
        payload = post
        author = getattr(payload, "user", None)

    post_id = str(_payload_get(payload, "id"))
    author_username = (
        getattr(author, "username", None)
        if author is not None and not isinstance(author, dict)
        else author.get("username")
        if isinstance(author, dict)
        else None
    ) or _payload_get(payload, "username")
    author_user_id = (
        getattr(author, "id", None)
        if author is not None and not isinstance(author, dict)
        else author.get("id")
        if isinstance(author, dict)
        else None
    )
    text_raw = (
        getattr(payload, "rawContent", None)
        or getattr(payload, "text", None)
        or _payload_get(payload, "rawContent")
        or _payload_get(payload, "text")
        or ""
    )
    url = getattr(payload, "url", None) or _payload_get(payload, "url")
    if not url and author_username and post_id:
        url = f"https://x.com/{author_username}/status/{post_id}"

    media = getattr(payload, "media", None)
    if media is None and isinstance(payload, dict):
        media = payload.get("media")

    return {
        "post_id": post_id,
        "author_username": author_username or "",
        "author_user_id": None if author_user_id is None else str(author_user_id),
        "created_at": _coerce_datetime(
            getattr(payload, "date", None)
            or _payload_get(payload, "date")
            or _payload_get(payload, "created_at")
        ),
        "text_raw": text_raw,
        "url": url or "",
        "is_reply": bool(
            getattr(payload, "inReplyToTweetId", None)
            or _payload_get(payload, "inReplyToTweetId")
            or _payload_get(payload, "is_reply")
        ),
        "is_retweet": bool(
            getattr(payload, "retweetedTweet", None)
            or _payload_get(payload, "retweetedTweet")
            or _payload_get(payload, "is_retweet")
        ),
        "has_media": bool(
            media
            or getattr(payload, "photos", None)
            or getattr(payload, "videos", None)
            or _payload_get(payload, "photos")
            or _payload_get(payload, "videos")
            or _payload_get(payload, "has_media")
        ),
        "lang": getattr(payload, "lang", None) or _payload_get(payload, "lang"),
        "raw_json": _extract_raw_json(post),
    }


class XMonitorTwscrapeClient:
    """Wrapper around a twscrape API instance."""

    def __init__(self, api):
        self.api = api

    async def resolve_user_id(self, username: str) -> str:
        user = await self.api.user_by_login(username)
        if user is None:
            raise ValueError(f"Unable to resolve user id for {username}")
        return str(user.id)

    async def fetch_recent_posts(
        self,
        user_id: str,
        include_replies: bool,
        limit: int,
    ) -> list[dict]:
        fetcher = (
            self.api.user_tweets_and_replies if include_replies else self.api.user_tweets
        )
        result = fetcher(user_id, limit=limit)

        if hasattr(result, "__aiter__"):
            posts = [post async for post in result]
        elif inspect.isawaitable(result):
            posts = await result
        else:
            posts = result

        return [_normalize_post(post) for post in posts]
