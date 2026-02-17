# Inbox

Drop any `.md` notes here. The system will ingest them on the next sync and
parse constraint keywords, then move the file to `processed/`.

## Recognised constraint keywords

| Keyword | Example |
|---|---|
| `no workout` | No workout on 2026-02-20 — family visit |
| `no run` | No run March 5 |
| `rest day` | Rest day 2026-02-22 (childcare) |
| `unavailable` | Unavailable Feb 28 - travel |
| `busy` | Busy 2026-03-01, wife works |
| `travel` | Travel 2/27 through 3/1 |
| `skip` | Skip workout 2026-02-25 |
| `childcare` | Childcare 2026-03-04 |
| `wife works` | Wife works 2026-03-06 |
| `night shift` | Night shift 2/28 |
| `on call` | On call 2026-02-19 |

## Supported date formats

- `2026-02-20` (ISO)
- `2/20/2026` or `2/20/26` or `2/20` (US numeric)
- `February 20, 2026` or `Feb 20` (month name)

## Example note

```
# Travel Week

No workout 2026-03-08 — conference in Chicago.
Rest day 2026-03-11 — travel back.
```

> Files are moved to `inbox/processed/` after ingestion and are not re-processed.
