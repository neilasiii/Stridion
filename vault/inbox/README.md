# Inbox

Drop any `.md` notes here. The system will ingest them on the next sync and
parse constraint keywords, then move the file to `processed/`.

## Recognised constraint keywords

| Keyword | Example |
|---|---|
| `no workout` | No workout on 2026-03-10 — family visit |
| `no run` | No run March 5 |
| `rest day` | Rest day 2026-03-08 (childcare) |
| `unavailable` | Unavailable March 12 - travel |
| `busy` | Busy 2026-03-14, spouse works |
| `travel` | Travel 3/15 through 3/17 |
| `skip` | Skip workout 2026-03-20 |
| `childcare` | Childcare 2026-03-22 |
| `spouse works` | Spouse works 2026-03-25 |
| `night shift` | Night shift 3/18 |
| `on call` | On call 2026-03-19 |

## Supported date formats

- `2026-02-20` (ISO)
- `2/20/2026` or `2/20/26` or `2/20` (US numeric)
- `February 20, 2026` or `Feb 20` (month name)

## Example note

```
# Travel Week

No workout 2026-03-20 — conference.
Rest day 2026-03-23 — travel back.
```

> Files are moved to `inbox/processed/` after ingestion and are not re-processed.
