<div align="center">

<br/>

<img alt="pwn-arena" src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=800&size=44&duration=2400&pause=900&color=A78BFA&center=true&vCenter=true&width=900&height=80&lines=pwn-arena"/>

**Dynamic CTF platform with per-user isolated containers.**
_For security training, university courses, internal red-team exercises._

<br/>

<p>
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
<img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white"/>
<img src="https://img.shields.io/badge/Security-CC0000?style=for-the-badge&logoColor=white"/>
</p>

<p>
<img src="https://img.shields.io/github/stars/kasimmj/pwn-arena?style=social"/>
<img src="https://img.shields.io/github/forks/kasimmj/pwn-arena?style=social"/>
</p>

</div>

---

## 🚩 Why pwn-arena?

CTFd shares challenge instances across all players — one exploit ruins everyone's experience. HackTheBox is paid and not self-hostable. Building your own CTF infra means weeks of Docker, networking, and flag-rotation code.

**pwn-arena gives every player their own isolated container, per challenge.**

- 🛡️ **Per-user-per-challenge isolation** — your exploit can't affect anyone else
- 🎲 **Dynamic flag rotation** — flags are unique per attempt, can't be shared
- 🔄 **One-click reset** — fresh container if you broke something
- 📜 **Markdown-based challenge format** — write challenges in your favorite editor
- 🏆 **Built-in scoreboard** — dynamic scoring, write-up submissions
- ⏰ **Time-boxed challenges** — auto-shutdown after N minutes
- 📊 **Player heatmaps** — see where players get stuck
- 🐳 **One-command setup** — `docker compose up`

---

## ⚡ Quick Start

```bash
git clone https://github.com/kasimmj/pwn-arena
cd pwn-arena
./up.sh
```

You now have:
- **Player portal** at `http://localhost:8000`
- **Admin panel** at `http://localhost:8000/admin`
- **Challenge containers** spawned on-demand on private network

Default admin: `admin / admin` (change in `.env` before first start in production).

---

## 🏗️ Architecture

```
                ┌─────────────────────────────────────────┐
                │           Player Portal (UI)             │
                │     - Browse challenges                   │
                │     - Submit flags                        │
                │     - Scoreboard, write-ups               │
                └─────────────┬───────────────────────────┘
                              │
                ┌─────────────▼───────────────────────────┐
                │       Platform API (FastAPI)             │
                │   - Auth (JWT)                            │
                │   - Challenge lifecycle                   │
                │   - Flag verification                     │
                │   - Scoring engine                        │
                └─────────────┬───────────────────────────┘
                              │
                ┌─────────────▼───────────────────────────┐
                │      Runner (Docker orchestration)        │
                │   - Spawn container per (user, chal)      │
                │   - Inject unique flag at startup         │
                │   - Network-isolated CNI                  │
                │   - Reap on timeout/idle                  │
                └─────────────┬───────────────────────────┘
                              │
                  ┌───────────┴───────────┐
                  │                       │
            ┌─────▼─────┐         ┌──────▼────┐
            │ chal:1234 │         │ chal:5678 │  (isolated containers)
            │  user-a   │         │  user-b   │
            └───────────┘         └───────────┘
```

---

## 📝 Writing a Challenge

A challenge is a folder with three files:

```
challenges/web-sqli/
├── challenge.yaml      # metadata
├── Dockerfile          # how to build the challenge container
└── README.md           # description shown to players
```

**`challenge.yaml`:**

```yaml
name: "SQL Injection 101"
category: "Web"
difficulty: "Easy"
points: 100
description: |
  A vulnerable login form. Can you authenticate as `admin`?
flag:
  type: "dynamic"      # "dynamic" (per-attempt) | "static"
  format: "ctf{...}"
  inject_env: "FLAG"   # name of env var the container reads on startup
network:
  ports:
    - 80
  egress: false        # block internet from inside the container
timeouts:
  idle: 30m            # container stops after 30 min idle
  hard: 4h             # hard kill after 4 hours
hints:
  - cost: 10
    text: "Look at the login form's HTML — what gets POSTed?"
  - cost: 25
    text: "Try `' OR 1=1--`"
```

**`Dockerfile`:**

```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
COPY app.py /opt/app/
RUN apk add --no-cache python3 py3-flask
ENV FLAG=placeholder
CMD ["sh", "-c", "echo $FLAG > /opt/app/.flag && python3 /opt/app/app.py"]
```

That's it. Drop the folder in `challenges/` → admin → "Reload challenges" → it's live.

---

## 🔐 Dynamic Flag Rotation

When a player launches a challenge, pwn-arena:

1. Generates a unique flag: `ctf{<challenge-id>_<user-id>_<random-hash>}`
2. Sets it as an env var when spawning the container
3. Stores it in the platform DB
4. Verifies submissions against the user's specific flag

This means **sharing flags doesn't work** — every player's flag is different. Cheating is structurally impossible.

For "static flag" challenges (intro material), set `flag.type: static` and provide a literal flag in the YAML.

---

## 🏆 Scoring Engine

Three scoring modes, configurable per event:

### 1. Static Points
Each challenge worth a fixed number declared in YAML.

### 2. Dynamic Points (decays with solves)
Worth more when only a few have solved it. Formula:
```
points = floor(
  min_points +
  (max_points - min_points) * exp(-solves / decay_rate)
)
```

### 3. First-Blood Bonuses
First 3 solvers get +50%, +30%, +15% respectively.

---

## 📊 Admin Dashboard

`/admin`:

- **Live containers** — see all running instances, kill any
- **Solve attempts** — every flag submission with diff (correct/wrong/wrong-user)
- **Player stats** — solves, time spent, hints used
- **Per-challenge heatmap** — average time to solve, drop-off points
- **Anti-cheat alerts** — repeated wrong flags from same IP, shared containers, etc.

---

## 🛡️ Isolation Model

Each challenge container:
- Joins a **per-user private Docker network** (`bridge-{user-id}`)
- Cannot reach the platform API or other users' containers
- Egress to the internet is **blocked by default** (allowlist via YAML)
- Runs as **non-root** unless explicitly enabled in the Dockerfile
- Resource-limited: 512MB RAM, 0.5 CPU, 1GB disk per challenge
- Has **no host filesystem access**

For pwn (binary exploitation) challenges, you can opt into `privileged: true` or `cap_add: [SYS_PTRACE]` — but the runner audits these on challenge load.

---

## 🌟 Use Cases

- 🎓 **University courses** — security curriculum with hands-on labs
- 🏢 **Internal red-team exercises** — train your blue team safely
- 🏆 **CTF competitions** — host your event with thousands of concurrent players
- 🎯 **Onboarding** — security engineering interviews and assessments
- 🧪 **Vulnerability research** — sandbox to test exploits

---

## 📁 Sample Challenges Included

| Challenge | Category | Difficulty | Points |
|-----------|----------|------------|--------|
| Crypto: RSA Weak Primes | Crypto | Easy | 100 |
| Web: SQL Injection 101 | Web | Easy | 100 |
| Pwn: Buffer Overflow | Pwn | Medium | 250 |
| Forensics: PCAP Analysis | Forensics | Medium | 250 |
| Reverse: ELF Crackme | Reverse | Hard | 500 |

More in `challenges/`. Contribute your own via PR.

---

## 🚀 Roadmap

- [x] Core platform + runner
- [x] Dynamic flag rotation
- [x] Markdown challenge format
- [x] Scoreboard
- [ ] Team mode (solve as squads)
- [ ] Snapshot/restore challenge state
- [ ] Cloud deployment (AWS/GCP/Hetzner Terraform modules)
- [ ] Mobile app for solving on-the-go

---

## 📜 License

MIT.

---

<div align="center">

**Star ⭐ to host your own CTF.**

</div>
