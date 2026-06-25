# Deploying RIDE OR DIE to the web (rop1)

The whole game is **one FastAPI app** — it serves both the JSON API and the CRT-terminal UI on a
single origin, and the frontend calls relative `/api/*` paths. So there's nothing to "connect"
between front and back: **deploy the one server and the UI ships with it.**

It's **multi-user**: each browser gets an opaque session cookie, and that token keys its own game
(its own save slot, rewind checkpoints, and Ace voice-memory). State is file-backed per session, so
the server is stateless per request and safe to run with `uvicorn --workers N`.

Target: **rop1**, alongside the Ace stack, so her voice (Nemotron + Kokoro) is a local call.

---

## 1. Put the code on the box

```bash
sudo mkdir -p /opt/fairlady && sudo chown "$USER" /opt/fairlady
git clone https://github.com/badlerSI/fairlady.git /opt/fairlady
cd /opt/fairlady
git checkout ride-or-die          # until it's merged to main

# Linux Python (modern OpenSSL) is fine for live OSM routing.
python3 -m venv .venv
./.venv/bin/pip install -U pip
./.venv/bin/pip install -r backend/requirements.txt
```

A dedicated service user (the unit assumes `fairlady`):

```bash
sudo useradd --system --home /opt/fairlady --shell /usr/sbin/nologin fairlady || true
sudo chown -R fairlady:fairlady /opt/fairlady          # data/ must be writable for saves
```

## 2. Configure

```bash
cp deploy/fairlady.env.example deploy/fairlady.env
# edit deploy/fairlady.env — adapter=ace, the Ace URL (localhost if co-located), routing=osm
```

Smoke-test it by hand first (Ctrl-C to stop):

```bash
set -a && . deploy/fairlady.env && set +a
./.venv/bin/uvicorn app:app --app-dir backend --host 127.0.0.1 --port 8739
curl -s localhost:8739/api/health        # {"ok":true,"adapter":"ace","routing":"osm"}
```

## 3. Run it as a service

```bash
sudo cp deploy/fairlady.service /etc/systemd/system/fairlady.service
sudo systemctl daemon-reload
sudo systemctl enable --now fairlady
systemctl status fairlady --no-pager
curl -s localhost:8739/api/health
```

Prune abandoned sessions daily (optional but tidy):

```bash
chmod +x deploy/sweep-sessions.sh
sudo cp deploy/fairlady-sweep.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now fairlady-sweep.timer
```

## 4. Expose it on a subdomain with TLS

Point DNS for the hostname (e.g. `rideordie.badler.ai`) at rop1 **first**, then:

**Caddy** (simplest — automatic Let's Encrypt TLS):
```bash
# add deploy/Caddyfile.example's block to your Caddyfile (edit the hostname), then:
sudo systemctl reload caddy
```

**…or Cloudflare Tunnel** (how the SOUL fleet does it — no open ports): add an ingress rule
`hostname: rideordie.badler.ai → service: http://127.0.0.1:8739` to your tunnel config and reload
`cloudflared`. See `Caddyfile.example` for the snippet.

Either way the app stays bound to `127.0.0.1:8739`; the proxy terminates TLS and forwards
`X-Forwarded-Proto`, which `--proxy-headers` uses to set the **Secure** session cookie.

## 5. Verify live

```bash
curl -sI https://rideordie.badler.ai/                       # 200/302, served over TLS
curl -s  https://rideordie.badler.ai/api/health
```
Open it in a browser, talk to her, confirm the voice plays and a refresh keeps your game.

---

## Updating

```bash
cd /opt/fairlady && git pull && sudo systemctl restart fairlady
```
The UI assets revalidate automatically (the app sends `Cache-Control: no-cache` on `/ui`), so a
plain browser reload picks up new JS/CSS.

## Notes / hardening worth doing

- **Rate-limit `/api/command`.** In `ace` mode every turn can hit the GPU; cap it at the proxy
  (Caddy `rate_limit`, or Cloudflare) so a bot can't run up the box. Snippet in `Caddyfile.example`.
- **Voice source.** If the game and Ace are on the same box, set `FAIRLADY_ACE_URL` to the local
  Ace address — lower latency and no public hop.
- **Backups.** Player games live in `/opt/fairlady/data/saves/web_*.json`; back that dir up if you
  care about not wiping everyone's road trip on a redeploy.
- **Same-origin.** The UI and API share an origin, so there's no CORS to configure.
