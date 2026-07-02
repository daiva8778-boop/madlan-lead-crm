import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="firecrawl")

import config

_client = None


def get_client():
    global _client
    if _client is None:
        from firecrawl import Firecrawl
        if not config.FIRECRAWL_API_KEY:
            raise RuntimeError("FIRECRAWL_API_KEY is not set in .env")
        _client = Firecrawl(api_key=config.FIRECRAWL_API_KEY)
    return _client


def scrape(url, wait_for=8000, timeout=45000, actions=None, formats=None):
    """Returns (content, markdown, credits_used) or (None, None, 0) on failure.
    `content` is doc.raw_html when 'rawHtml' was requested (needed to see
    <script> tags — the cleaned 'html' format strips them), else doc.html."""
    client = get_client()
    formats = formats or ["html"]
    try:
        kwargs = dict(
            formats=formats,
            wait_for=wait_for,
            timeout=timeout,
            max_age=0,
        )
        if actions:
            kwargs["actions"] = actions
        doc = client.scrape(url, **kwargs)
        content = doc.raw_html if "rawHtml" in formats else getattr(doc, "html", None)
        markdown = getattr(doc, "markdown", None)
        credits_used = getattr(doc.metadata, "credits_used", 1) if doc.metadata else 1
        return content, markdown, credits_used or 1
    except Exception as e:
        print(f"[firecrawl_client] scrape failed for {url}: {e}")
        return None, None, 0
