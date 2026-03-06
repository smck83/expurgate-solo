![expurgate - simplify, hide and exceed SPF lookup limits](https://github.com/smck83/expurgate/blob/main/expurgate.png?raw=true)

> A single-container, self-hosted SPF flattening solution. Expurgate Solo combines the resolver and DNS server into one Docker image — simpler to deploy, with a built-in supervisord web interface for process management.

- 🌐 **Don't want to self-host?** Try [spf.guru](https://spf.guru)
- 🐳 **Want separate containers?** See [Expurgate (multi-container)](https://github.com/smck83/expurgate)

For full background on how SPF flattening works, see the [Expurgate README](https://github.com/smck83/expurgate/blob/main/README.md).

---

## Table of Contents

- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
  - [Run with Docker](#run-with-docker)
  - [Amazon Lightsail](#amazon-lightsail)
- [DNS Setup](#dns-setup)
- [Supervisord Web Interface](#supervisord-web-interface)
- [Environment Variables](#environment-variables)
- [Video Tutorial](#video-tutorial)

---

## How It Works

Expurgate Solo runs two processes in a single container via [supervisord](http://supervisord.org/):

| Process | Role |
|---|---|
| **expurgate-resolver** | Reads your source SPF record from a private subdomain, resolves all hostnames to IPs, and writes an rbldnsd config file. Reruns every `DELAY` seconds. |
| **rbldnsd** | DNS server that answers SPF macro queries using the generated config. Listens on UDP/53. |

Your public SPF record is replaced with a macro:
```
v=spf1 include:%{ir}.%{d}._spf.yourdomain.com -all
```

When a receiving mail server evaluates this, it queries your Expurgate Solo instance directly — which responds with just the relevant IP, not your full vendor list.

---

## Quick Start

### Step 1 — Copy your SPF record to a private subdomain

Pick an obscure subdomain prefix (e.g. `_sd6sdyfn`) and publish your existing SPF record there. This becomes the source of truth that Expurgate reads from:

```
_sd6sdyfn.yourdomain.com.  IN  TXT  "v=spf1 include:sendgrid.net include:mailgun.org -all"
```

### Step 2 — Create DNS records pointing to your instance

```
; A record pointing to the server running Expurgate Solo
spf-ns.yourdomain.com.   IN  A   192.0.2.1

; Delegate the _spf subdomain to your instance
_spf.yourdomain.com.     IN  NS  spf-ns.yourdomain.com.
```

### Step 3 — Run the container

### Run with Docker

```bash
docker run -d \
  -p 53:53/udp \
  -p 9001:9001 \
  -e ZONE="_spf.yourdomain.com" \
  -e MY_DOMAINS="yourdomain.com yourdomain2.com" \
  -e SOURCE_PREFIX="_sd6sdyfn" \
  -e NS_RECORD="spf-ns.yourdomain.com" \
  -e SOA_HOSTMASTER="hostmaster@yourdomain.com" \
  --dns 1.1.1.1 --dns 8.8.8.8 \
  --restart always \
  smck83/expurgate-solo
```

Open UDP port 53 on your host/firewall. Optionally open TCP port 9001 (restricted to your IP) to access the supervisord web interface.

### Step 4 — Replace your old SPF record with the macro

Apply this to all domains in `MY_DOMAINS`:

```
v=spf1 include:%{ir}.%{d}._spf.yourdomain.com -all
```

---

## Amazon Lightsail

Use the following as a **Launch Script** when creating a new Lightsail Debian instance:

```bash
wget https://raw.githubusercontent.com/smck83/expurgate-solo/main/install.sh && \
chmod 755 install.sh && ./install.sh && \
docker run -d \
  -p 9001:9001 \
  -p 53:53/udp \
  -e ZONE="_spf.yourdomain.com" \
  -e MY_DOMAINS="yourdomain.com yourdomain2.com yourdomain3.com" \
  -e SOURCE_PREFIX="_sd6sdyfn" \
  --dns 1.1.1.1 --dns 8.8.8.8 \
  --restart always \
  smck83/expurgate-solo
```

After the instance is running, assign a static IP and open UDP/53. Optionally open TCP/9001 restricted to your own IP.

---

## Supervisord Web Interface

Expurgate Solo uses [supervisord](http://supervisord.org/) to manage the resolver and rbldnsd processes. A basic web UI is available:

| Setting | Value |
|---|---|
| URL | `http://<host-ip>:9001` |
| Username | `admin` |
| Default password | `Expurgate` |

Set a custom password using the `SUPERVISOR_PW` environment variable (see below). You can pass it as plaintext or as a SHA1 hash.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ZONE` | **Yes** | — | The DNS zone served by rbldnsd. Must match the NS delegation. E.g. `_spf.yourdomain.com` |
| `MY_DOMAINS` | **Yes*** | — | Space-separated list of domains to generate config for. E.g. `yourdomain.com yourdomain2.com` |
| `SOURCE_PREFIX` | **Yes** | `_xpg8` | Subdomain prefix where your source SPF record lives. E.g. `_sd6sdyfn` → reads `_sd6sdyfn.yourdomain.com` |
| `DELAY` | No | `300` | Seconds between resolver runs. Minimum: 30 |
| `SUPERVISOR_PW` | No | `Expurgate` | Password for the supervisord web interface. Accepts plaintext or SHA1 hash, e.g. `{SHA}93eb18474e9067ff5a6f98c54b8854026cee02cb` |
| `NS_RECORD` | No | — | Hostname for the NS record, e.g. `spf-ns.yourdomain.com`. Required alongside `SOA_HOSTMASTER` for DNS standards compliance |
| `SOA_HOSTMASTER` | No | — | Email address for the SOA record, e.g. `hostmaster@yourdomain.com`. Required alongside `NS_RECORD` |
| `TZ` | No | — | Timezone, e.g. `Australia/Sydney`. [Full list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) |
| `DISCORD_WEBHOOK` | No | — | Discord webhook URL for change notifications. E.g. `https://discord.com/api/webhooks/123456789/...` |
| `UPTIMEKUMA_PUSH_URL` | No | — | [Uptime Kuma](https://github.com/louislam/uptime-kuma) push URL for health monitoring. Must end in `ping=` |
| `SOURCE_PREFIX_OFF` | No | `False` | Disables the source prefix subdomain lookup and resolves the root domain directly. Only change this for testing or advanced use cases |
| `RESTDB_URL` | No | — | RestDB endpoint URL for managing `MY_DOMAINS` via API instead of environment variable |
| `RESTDB_KEY` | No | — | API key for RestDB authentication. Required when `RESTDB_URL` is set |

*If `MY_DOMAINS` is not set and `RESTDB_URL` is not configured, the container runs in **demo mode** using a set of common public SPF records (`_spf.google.com`, `_netblocks.mimecast.com`, `spf.protection.outlook.com`, etc.).

---

## Video Tutorial

A walkthrough of deploying Expurgate Solo on Amazon Lightsail:

[![How to run Expurgate Solo for SPF Macro hosting in Amazon Lightsail](https://img.youtube.com/vi/MeUNizXkdU8/0.jpg)](https://www.youtube.com/watch?v=MeUNizXkdU8)

---

## Support the Project

If Expurgate Solo has been useful, consider [buying me a coffee ☕](https://www.buymeacoffee.com/smc83)
