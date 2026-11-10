# Boot2Root writeups

> **42 Boot2Root · HAL9042**
>
> Two routes from the web application to root, plus five bonus flags.

Walkthroughs for the HAL9042 local VirtualBox VM, covering discovery, account transitions, privilege escalation, and flag recovery.

> [!WARNING]
> These writeups contain challenge spoilers, lab credentials, and flags from an intentionally vulnerable local lab.

## Choose a walkthrough

| Writeup | Entry point | Coverage |
| --- | --- | --- |
| [01 · Exposed debug endpoint](writeup1.md) | File disclosure and debug command execution | Web entry → account escalation → root → 10 flags |
| [02 · Jinja2 SSTI](writeup2.md) | Server-side template injection | Alternative web entry and the shared escalation path |
| [Bonus · Five additional flags](bonus/bonus_writeup.md) | Files, history, UDP, process environment, and stored XSS | Discovery, evidence, impact, and prevention for each flag |

## Account progression

```text
Web application → paco → wil → ol → root
                        └→ sophie
                           Key fragment and PDF investigation
```

Both main walkthroughs follow this account progression after their initial web entry. They recover eight flags through `flagd`, one from the encrypted report, and one from the final PDF.

## Lab access

| Service | VirtualBox forwarded address |
| --- | --- |
| Web application | `http://localhost:5042/` |
| SSH | `localhost:6060` |

## Supporting script

[`scripts/xss_get_server.py`](scripts/xss_get_server.py) is the Flask GET callback server used in the stored XSS investigation. It listens on port `8888` and logs the `test` query parameter received at `/c` or `/collect`.

Run it in a Python environment with Flask installed:

```bash
python scripts/xss_get_server.py
```

## Repository map

```text
boot2root-writeups/
├── README.md
├── writeup1.md
├── writeup2.md
├── bonus/
│   └── bonus_writeup.md
└── scripts/
    └── xss_get_server.py
```
