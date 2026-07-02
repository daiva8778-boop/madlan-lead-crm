# Madlan Lead CRM

A local dashboard that scrapes real estate agencies from madlan.co.il, tracks WhatsApp outreach
to them, and (optionally) auto-replies to their first reply.

Everything runs on your own computer. Nothing is uploaded anywhere except to Firecrawl (which you
already pay for) and to WhatsApp itself when you send a message.

## 1. Install once

You need:
- **Python 3.10+** — check with `python --version`
- **A Firecrawl API key** (you already have a paid account) — from https://www.firecrawl.dev/app/api-keys
- **Node.js 22.5+** — only if you want the optional auto-reply module. Check with `node --version`.
  Get it from https://nodejs.org if you don't have it.

Steps:
1. Copy `.env.example` to a new file named `.env` in this same folder.
2. Open `.env` and paste your Firecrawl key after `FIRECRAWL_API_KEY=`, e.g.:
   ```
   FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
3. That's it — everything else installs itself the first time you run the app (see below).

## 2. Run it

Double-click **`run.bat`** (Windows). A terminal window opens, installs anything missing, and
your browser opens automatically to the dashboard at `http://127.0.0.1:5000`.

To also start the WhatsApp auto-reply module, run it from a terminal with a flag instead of
double-clicking:
```
run.bat --with-autoreply
```
This opens a second window for the auto-reply module (see section 4).

On Mac/Linux, use `./run.sh` or `./run.sh --with-autoreply` instead.

## 3. Using the dashboard

**Left panel — scraping:**
- Pick a city from the dropdown, click **"Scrape Next 50"**. It scrapes exactly 50 new agencies
  (skipping any already in your database), showing live progress, then a summary (how many
  scraped, how many had no website, how many Firecrawl credits were used).
- Click it again any time — it remembers where it left off per city and continues from there.
- If a page fails to scrape (blocked, broken, etc.) it's skipped and logged — click **"Failed
  URLs"** in the left panel to see what was skipped.

**Right panel — your leads:**
- Filter tabs: All / New / Sent / Follow-up due / Replied / No-site only. "Follow-up due" appears
  automatically for anything you messaged more than 3 days ago that hasn't replied.
- Click the green **WhatsApp** button on a row to open WhatsApp with a pre-written message already
  typed in (in Hebrew, with the agency's name and deal count filled in) — you just hit send in
  WhatsApp. The row automatically flips to "Sent". If you clicked by mistake, hit **"undo"** next
  to the button.
- Change any agency's status with the dropdown in the Status column (New, Sent, Replied, Meeting,
  Client, Not interested, Do not contact).
- **"Do not contact"** is permanent — once set, that agency is hidden from every outreach filter,
  protected from accidental status changes (you'll be asked to confirm), and stays that way even
  if you re-scrape the same city later.
- Type directly into the Notes box on any row — it saves automatically as you type.
- **"Export to Excel"** / **"Export to CSV"** download the full list with every column, ready to
  open in Excel (no-website agencies are highlighted yellow, header row is frozen, filters are
  turned on).
- **"Template performance"** panel shows, per message version, how many you sent and how many led
  to a reply — useful for comparing different wording over time.

## 4. Editing your WhatsApp messages

Open **`message_templates.py`** in this folder — it's a plain text file, not code you need to
understand. There are exactly 4 messages:

- `opener_has_site` — first message sent to an agency that has a website
- `opener_no_site` — first message sent to an agency with no website
- `followup` — sent automatically instead of the opener if 3+ days have passed with no reply
- `auto_reply` — sent once by the auto-reply module (see below) when someone replies for the
  first time

Just replace the Hebrew text between the `"""..."""` marks with your own wording. Keep
`[AGENCY_NAME]` and `[DEAL_COUNT]` wherever you want those filled in automatically — delete them
if you don't want to use them in a particular message. Don't touch anything else in the file.

If you change a message's wording in a meaningful way, also bump its `"version"` (e.g.
`opener_site_v1` → `opener_site_v2`) so the Template performance panel tracks the two wordings
separately.

## 5. The auto-reply module (optional)

**What it does:** if it's running and someone you messaged (status Sent or Follow-up due) replies
to you on WhatsApp for the first time, it automatically (a) marks them "Replied" in the dashboard,
and (b) after a random human-like pause (30–90 seconds), sends them the `auto_reply` message —
**once, ever, per contact.** It will never message anyone who isn't already in your CRM, and never
sends anything except that one pre-approved message.

**Important — read this:**
- This uses **whatsapp-web.js**, an *unofficial* library that connects the same way WhatsApp Web
  does. It is not made or supported by WhatsApp/Meta. Use at your own discretion.
- **Your computer must stay on and the auto-reply window open** for it to keep working — if you
  close it or shut down, it simply stops (nothing breaks, you just lose the auto-reply behavior
  until you start it again).
- The dashboard has its own **master ON/OFF switch** for this (left panel, default **OFF**). Even
  if the module is running, it does nothing at all while the switch is off — that's your kill
  switch, no exceptions.
- Note about WhatsApp Business's own greeting message: it does **not** trigger when someone
  replies to a chat *you* started — it only fires on a completely new incoming chat. That's the
  gap this module fills.

**How to link it:**
1. Run `run.bat --with-autoreply` (or `./run.sh --with-autoreply`).
2. A second window opens and prints a QR code.
3. On your phone: WhatsApp → Settings → Linked Devices → Link a Device, then scan the code.
4. Once linked, the dashboard's auto-reply panel shows "Connection: linked". Flip the master
   switch ON when you're ready for it to actually act.

**How to unlink it:** open WhatsApp on your phone → Settings → Linked Devices → find this
computer in the list → Log out. You can also just delete the `autoreply/.wwebjs_auth` folder here
and it will ask you to scan a fresh QR code next time.

**If the connection drops** (phone off, WiFi issue, logged out remotely): the dashboard shows
"Connection: disconnected". Incoming messages will still be detected and marked "Replied," but no
auto-reply will be sent until it's reconnected — nothing gets queued up and sent late.

## 6. Cities

The city dropdown covers: Tel Aviv, Jerusalem, Haifa, Ramat Gan, Netanya, Rishon LeZion. To add or
change cities, edit the `CITIES` dictionary near the top of `config.py` — each entry needs the
city's exact Hebrew URL slug from madlan.co.il's own directory page (open the city's page on
madlan.co.il and copy the part of the URL after `/madad-search/`).

## 7. Backups

Every time you start the app, it automatically makes one timestamped backup copy of your database
into `db/backups/` (skipped if it already made one today). Your live data is always in
`data/madlan_crm.db`.

## 8. How phone numbers and websites are actually obtained

madlan.co.il embeds its real data directly in each page's own source as structured data (meant to
power the site's own React app), rather than requiring anything to be scraped from visible page
text. The scraper reads that directly:

- The **directory page** (one per city) embeds the full office list for the entire city in one
  go — every agency's name, deal count, exclusives count, and phone number. One fetch returns
  everything (633/633 Tel Aviv agencies came back in a single request in testing) — no scrolling
  or pagination needed.
- Each new agency's own **profile page** is then visited once to confirm the name/phone and pick
  up a real **website URL** (kept separate from their social media links, which are also present
  but ignored). If a website is found, the scraper visits it (per the original spec) to look for a
  direct mobile number, which is preferred over Madlan's own tracking number when found.
- Both steps normally succeed via a plain, free HTTP request — no Firecrawl credit spent most of
  the time. If madlan.co.il's protection is ever more active than usual, the scraper automatically
  falls back to Firecrawl (a few credits) and retries a blocked profile page up to 5 times before
  giving up and saving the agency with whatever data it already has.

A few things worth knowing:
- The phone numbers Madlan shows by default are their own **073 call-tracking numbers**, not each
  agency's own line. When a real 05X mobile is found via their website, that's used instead and
  labeled "(mobile)" next to the WhatsApp button — the tracking number is labeled "(073)".
- Not every agency has a phone or a website — those are still saved with whatever data is
  available (name/city/deals/exclusives at minimum), and the WhatsApp button is simply disabled
  for anything with no phone at all.
- If madlan.co.il changes how this data is structured in the future, the parsing logic lives in
  `scraper/ssr_extract.py` (shared extraction), `scraper/directory_parser.py`, and
  `scraper/profile_parser.py` — all clearly commented for exactly this situation.
