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
        "version": "opener_site_v2",
        # Sent to agencies that DO have a website.
        "text": """היי [AGENCY_NAME],מדבר אביעד מה נשמע?
 ישר ולעניין:

ראיתי את האתר שלכם. יש לו נוכחות, אבל כל פנייה שנכנסת ממנו צריכה מישהו שיתפנה אליה — ועד אז הלקוח כבר יכול להתקרר.

אני מחבר לאתרים מענה אוטומטי שעונה תוך שניות — הלקוח מקבל תשובה בשניות, אתם לא צריכים להיות שם.

אם זה לא רלוונטי — תתעלמו. אם כן — אראה לכם דוגמה קצרה ללא עלות""",
    },
    "opener_no_site": {
        "version": "opener_nosite_v1",
        # Sent to agencies that do NOT have a website.
        "text": """היי [AGENCY_NAME], זה אביעד. ישר ולעניין:

חיפשתי את האתר שלכם — לא מצאתי. מי שמחפש אתכם לא מוצא זה עולה לכם בלקוחות כל שבוע.

אני בונה אתרים שמכניסים פניות ישר לוואטסאפ ועונים להן לבד — יותר לקוחות, בלי שזה ייקח לכם זמן.

אני יכול להכין הדגמה לעסק שלך בלי עלות
דבר כזה יכול לעניין אותך?""",
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
