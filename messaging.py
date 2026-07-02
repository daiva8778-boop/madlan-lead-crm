from urllib.parse import quote

from message_templates import TEMPLATES


def render_template(template_key, agency_name, deal_count):
    tpl = TEMPLATES[template_key]
    text = tpl["text"]
    text = text.replace("[AGENCY_NAME]", agency_name or "")
    if deal_count is not None:
        text = text.replace("[DEAL_COUNT]", str(deal_count))
    else:
        # graceful omission when deal count is unknown, per template-editing spec
        text = text.replace("[DEAL_COUNT]", "")
    return text, tpl["version"]


def choose_template_key(has_website, is_follow_up_due):
    if is_follow_up_due:
        return "followup"
    return "opener_has_site" if has_website else "opener_no_site"


def build_wa_url(phone_used, message_text):
    if not phone_used:
        return None
    return f"https://wa.me/{phone_used}?text={quote(message_text)}"
