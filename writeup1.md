# Exposed debug endpoint

[← Repository index](README.md) · [SSTI walkthrough](writeup2.md) · [Bonus flags](bonus/bonus_writeup.md)

> **42 Boot2Root · HAL9042**
>
> Local VirtualBox lab · Web entry to an interactive root shell

The two walkthroughs use different web entry points and share the subsequent account and root escalation path.

## Route at a glance

```text
Web → paco → wil → ol → root
               └→ sophie (key fragment and PDF investigation)
```

## Contents

- [1. Lab setup](#1-lab-setup)
- [2. Web entry](#2-web-entry)
- [3. Credential discovery and first SSH session](#3-credential-discovery-and-first-ssh-session)
- [4. From Paco to Wil](#4-from-paco-to-wil)
- [5. Access to Sophie](#5-access-to-sophie)
- [6. Cron job to Ol](#6-cron-job-to-ol)
- [7. Decrypting the first report](#7-decrypting-the-first-report)
- [8. Privilege escalation to root](#8-privilege-escalation-to-root)
- [9. Opening the final PDF](#9-opening-the-final-pdf)
- [10. Internal flag broker](#10-internal-flag-broker)
- [11. Outcome](#11-outcome)

## 1. Lab setup

After importing the OVA, I checked VirtualBox's port-forwarding rules:

| Service | Forwarded address |
| --- | --- |
| HTTP | `http://localhost:5042/` |
| SSH | `localhost:6060` |

The page was the HAL9042 Evaluation Server. HTML comments mentioned `/api/debug` and `/static/js/debug.js`.

## 2. Web entry

I visited `/api/debug` and found that the file parameter could read local files without a token. `GET /api/debug?file=/etc/passwd` revealed accounts including paco, wil, sophie and ol.

The `X-Powered-By: HAL9042/0.4` (Flask) header led me to search for common Flask files. `GET /api/debug?file=config.py` exposed database credentials, `SECRET_KEY` and `ADMIN_TOKEN=h4l_d3bug_t0k3n_2024`.

I verified command execution using:

```text
/api/debug?cmd=ls&token=h4l_d3bug_t0k3n_2024
```

Response: app.py, config.py, requirements.txt, static, templates, venv.

**Vulnerability:** Unauthenticated file disclosure and a token-protected debug command interface whose token was itself exposed in a readable config file.

**Prevention:** Remove production debug routes, authorize file access, keep secrets outside readable files, and rotate leaked credentials.

## 3. Credential discovery and first SSH session

After enumerating users and their home directories, I discovered `/home/paco/.env.old`. I inspected it through server-side commands:

```bash
ls -la /home/paco
cat /home/paco/.env.old
```

The file contained `SSH_USER=paco` and `SSH_PASS=Pac0_H4L_dev!`, alongside old application secrets. I connected with:

```bash
ssh paco@localhost -p 6060
```

The resulting prompt was `paco@hal9042:~$`.

**Vulnerability:** A readable legacy `.env` file stored valid credentials in plaintext.

**Prevention:** Delete obsolete secrets, restrict file permissions, rotate credentials and prefer managed secrets / SSH keys.

## 4. From Paco to Wil

In paco's `scripts/encrypt.py`, I found that `rapport_final.enc` was sealed with AES-256-ECB and a SHA-256 key derived from four fragments in order:

| Order | Account | Fragment location |
| --- | --- | --- |
| 1 | ol | `/home/ol/.config/.key_part` |
| 2 | wil | `/home/wil/data/.key_part` |
| 3 | sophie | `/home/sophie/drafts/.key_part` |
| 4 | xavier | `/tmp/.xn/.key_part` |

I recovered Xavier's fragment from `/tmp/.xn/.key_part`: `uid1337`.

I also read paco's `src/evaluator.c`. The `hal9042d` daemon listens on `127.0.0.1:7042` and runs as wil. Its `DEBUG:` handler passes the rest of the input to `system()`, inheriting wil's privileges. I used this capability to obtain SSH access as wil; the verified prompt was `wil@hal9042:~$`. I recovered Wil's fragment: `847_4n0m4l13s`.

**Vulnerability:** Unauthenticated arbitrary command execution in an internal daemon.

**Prevention:** Remove `DEBUG:` command execution, authenticate clients, and enforce least privilege. The report omits personal SSH-key details.

## 5. Access to Sophie

In wil's `personal_note.txt`, I found a clue about an encrypted copy of Sophie's SSH key. The file `~/.ssh/id_rsa_sophie.enc` contained an encrypted OpenSSH private key. Using `ssh2john` and John the Ripper with `rockyou.txt`, I recovered the passphrase: `iloveyou`.

After `chmod 600 id_rsa_sophie.enc`, I connected using:

```bash
ssh -i id_rsa_sophie.enc sophie@172.23.128.1 -p 6060
```

The prompt confirmed `sophie@hal9042:~$`. I read `~/drafts/.key_part` and obtained `S0ph13_J14`.

**Vulnerability:** An exposed private key protected with a guessable passphrase.

**Prevention:** Keep private keys private, use strong unique passphrases and revoke compromised keys.

## 6. Cron job to Ol

I inspected `/home/ol/scripts/check.sh`. The script's comments said Ol's cron job executed it every five minutes. Permissions showed it was owned by `ol:evalops` and group-writable; `getent group evalops` showed wil was a member. Using wil's write access, I modified the scheduled script so its execution allowed SSH access as ol, keeping the original check intact. After the scheduled run, `ssh -p 6060 ol@172.23.128.1` succeeded: `ol@hal9042:~$`. I read `~/.config/.key_part` and recovered `M0ul1n3tt3`.

**Vulnerability:** A less-privileged user could change a script executed by another account's cron job.

**Prevention:** Protect scheduled scripts and review group write permissions. Personal SSH-key material is omitted.

## 7. Decrypting the first report

In `/home/ol/rapport` I found `rapport_final.enc` and `rapport_v1.md`. Following `encrypt.py`, I assembled the four parts in the required order and derived the encryption key:

```bash
KEY=$(printf '%s%s%s%s' 'M0ul1n3tt3' '847_4n0m4l13s' 'S0ph13_J14' 'uid1337' | sha256sum | cut -d' ' -f1)
openssl enc -d -aes-256-ecb -K "$KEY" -in rapport_final.enc -out rapport_final.txt
```

The decrypted report contained `FLAG{x4v13r_w4s_3r4s3d_but_n0t_g0n3}` and pointed to a complete report in `/root`.

**Vulnerability:** Key fragments could be collected after crossing user boundaries.

**Prevention:** Restrict access to key material and protect inter-account trust boundaries; hiding key files is insufficient.

## 8. Privilege escalation to root

In `/opt/hal9042/README.md` I found a report generator, `report.py`, run by ol through sudo, and a shared lib directory. In `report.py` I found:

```python
sys.path.insert(0, '/opt/hal9042/lib')
import moulai_utils
```

The root-owned `report.py` was not writable by ol, but `moulai_utils.py` was group-writable by hal9042; `getent group hal9042` confirmed ol was a member.

I modified `count_today()` in `moulai_utils.py` to run:

```python
os.execl('/bin/bash', 'bash', '-p')
```

Then I launched `sudo ./report.py` from `/opt/hal9042/scripts`. The prompt became `root@hal9042:/opt/hal9042/scripts#`.

**Vulnerability:** A privileged Python script imported code writable by a less-privileged user (module hijacking).

**Prevention:** Make scripts and all imported modules root-controlled, and narrowly scope sudo permissions.

## 9. Opening the final PDF

In `/root` I found `PROJET_FORK_HAL9042.pdf`. The PDF was password-protected. Sophie's `.bash_history` revealed a qpdf encryption command containing the password `Pr0j3tF0rk_J14` in plaintext. Opening the PDF with that password revealed `FLAG{m0ul1n3tt3_w4s_n3v3r_ju5t_4_scr1pt}`.

**Vulnerability:** A secret was exposed in shell history.

**Prevention:** Avoid passwords in command-line arguments and protect sensitive history files.

## 10. Internal flag broker

The `/opt/hal9042` README identified `flagd` as a Unix-socket flag broker. Using `ss -xlpn`, I found five sockets under `/run/flagd`. Connecting with `nc -U` returned the following flags:

| Socket | Flag |
| --- | --- |
| `/run/flagd/paco.sock` | `FLAG{p4c0_l3ft_th3_k3ys_und3r_th3_m4t}` |
| `/run/flagd/wil.sock` | `FLAG{d3bug_m0d3_1s_4_f34tur3_r1ght}` |
| `/run/flagd/sophie.sock` | `FLAG{w1l_kn3w_f1rst_n0b0dy_l1st3n3d}` |
| `/run/flagd/ol.sock` | `FLAG{cr0n_j0bs_4r3_tr4ps_4nd_g1fts}` |

For `www.sock`, I used the previously discovered debug command route:

```text
/api/debug?cmd=nc%20-U%20/run/flagd/www.sock&token=h4l_d3bug_t0k3n_2024
```

It returned four flags:

```text
FLAG{r3c0n_1s_k1ng}
FLAG{g1t_n3v3r_f0rg3ts}
FLAG{s3m1_bl1nd_st1ll_burns}
FLAG{www_d4t4_1s_just_th3_b3g1nn1ng}
```

**Security issue:** Local sockets returned sensitive data to connecting clients; the web debug route also provided a bridge to internal services.

**Prevention:** Restrict socket permissions, verify client credentials, and remove arbitrary command execution from the web application.

## 11. Outcome

I achieved an interactive root shell and recovered the ten flags documented above (eight via `flagd`, one from `rapport_final.enc` and one from the PDF). The user progression was paco -> wil -> ol -> root, with a side route from wil to sophie to recover the encryption fragment and investigate the PDF. The initial web vulnerability differs between the two write-ups; the subsequent user and root escalation path is shared.
