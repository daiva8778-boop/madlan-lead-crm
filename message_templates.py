"""
WhatsApp message templates — EDIT THE TEXT BELOW, NOTHING ELSE.

There are exactly 4 templates. Each has a "version" name (bump it, e.g. opener_site_v2,
whenever you change the wording — the app tracks results per version so you can see which
wording performs best).

Available placeholders (only use these two, spelled exactly like this):
  [AGENCY_NAME]  -> replaced with the agency's name
  [DEAL_COUNT]   -> replaced with the agency's deal count (or omitted gracefully if unknown)

Do not delete the "key" or "version" lines. Only edit the "text" value (the part between the
three quote marks \"\"\" ... \"\"\").
"""

TEMPLATES = {
    "opener_has_site": {
        "version": "opener_site_v1",
        # Sent to agencies that DO have a website.
        "text": """שלום [AGENCY_NAME], ראיתי שביצעתם [DEAL_COUNT] עסקאות לאחרונה - כתבו כאן את ההודעה שלכם.""",
    },
    "opener_no_site": {
        "version": "opener_nosite_v1",
        # Sent to agencies that do NOT have a website.
        "text": """שלום [AGENCY_NAME], שמתי לב שאין לכם עדיין אתר אינטרנט - כתבו כאן את ההודעה שלכם.""",
    },
    "followup": {
        "version": "followup_v1",
        # Sent to agencies that are SENT but haven't replied after 3+ days.
        "text": """שלום [AGENCY_NAME], רציתי לחזור ולוודא שקיבלתם את ההודעה הקודמת שלי - כתבו כאן את ההודעה שלכם.""",
    },
    "auto_reply": {
        "version": "autoreply_v1",
        # Sent ONCE, automatically, by the optional auto-reply module when an agency
        # in SENT/FOLLOW-UP DUE replies for the first time.
        "text": """תודה על התגובה [AGENCY_NAME]! כתבו כאן את הודעת המענה האוטומטית שלכם.""",
    },
}
