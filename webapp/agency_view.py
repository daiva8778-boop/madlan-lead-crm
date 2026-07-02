from datetime import datetime, timedelta

import config

STATUSES = ['NEW', 'SENT', 'REPLIED', 'MEETING', 'CLIENT', 'NOT_INTERESTED', 'DO_NOT_CONTACT']


def is_follow_up_due(row):
    if row["status"] != "SENT" or not row["sent_at"]:
        return False
    try:
        sent_at = datetime.fromisoformat(row["sent_at"])
    except ValueError:
        return False
    return datetime.now() - sent_at > timedelta(days=config.FOLLOW_UP_DUE_DAYS)


def serialize_agency(row):
    d = dict(row)
    d["is_follow_up_due"] = is_follow_up_due(row)
    d["city_label"] = config.CITIES.get(d["city"], {}).get("label", d["city"])
    return d
