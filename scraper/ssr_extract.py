import json
import re

SSR_MARKER = "window.__SSR_HYDRATED_CONTEXT__="


def _extract_balanced_json(raw_html, start):
    """Scans for the matching closing brace rather than a regex, since the
    blob's own string values can contain "</script>"-like substrings that
    would confuse a naive non-greedy match."""
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(raw_html)):
        c = raw_html[i]
        if in_string:
            if escape:
                escape = False
            elif c == "\\":
                escape = True
            elif c == '"':
                in_string = False
            continue
        if c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return raw_html[start:i + 1]
    return None


def extract_ssr_state(raw_html):
    """Madlan server-side embeds page data as window.__SSR_HYDRATED_CONTEXT__
    inside a <script> tag on both directory and profile pages. Requires the
    RAW page source (plain `requests`, or Firecrawl's 'rawHtml' format — the
    cleaned 'html' format strips <script> tags). Returns the parsed dict, or
    None if the marker/blob isn't present or fails to parse."""
    if not raw_html:
        return None
    start = raw_html.find(SSR_MARKER)
    if start == -1:
        return None
    start += len(SSR_MARKER)
    blob_text = _extract_balanced_json(raw_html, start)
    if not blob_text:
        return None
    # this is a JS object literal, not strict JSON — it contains bare
    # `undefined` values (e.g. unset router params) that json.loads rejects
    blob_text = re.sub(r"([:,])undefined\b", r"\1null", blob_text)
    try:
        return json.loads(blob_text)
    except json.JSONDecodeError:
        return None
