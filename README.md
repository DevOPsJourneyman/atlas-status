# Atlas Status

A real-time container monitoring dashboard for Atlas Lab. Talks directly to the Docker daemon via socket mount, displaying live health data for all containers on zeus01.

## What It Does

- Live status for all running containers — uptime, CPU, memory
- Port mappings with direct links to each app
- Last 20 log lines per container — expandable
- Docker network topology
- Stopped container visibility
- Auto-refreshes every 30 seconds
- Manual refresh button
- Graceful error state if daemon is unreachable

## Key Docker Concept — The Socket Mount

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

The Docker daemon communicates via a Unix socket at `/var/run/docker.sock`. By mounting this socket into the container, the Flask app can query the daemon directly using the Docker SDK for Python — the same way the Docker CLI works, but programmatically.

`:ro` mounts the socket read-only at the filesystem level. This is a security best practice.

**Interview answer:** *"I mounted the Docker socket so the monitoring app could query the daemon via the Python SDK. I'm aware this grants broad API access, and in production I'd front it with a Docker Socket Proxy to restrict which endpoints are exposed."*

## Quick Start

```bash
docker pull devopsjourneyman/atlas-status:latest
docker run -d -p 5003:5000 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  devopsjourneyman/atlas-status:latest
```

Open `http://localhost:5003`

## Atlas Lab Deployment

```bash
git clone https://github.com/DevOpsJourneyman/atlas-status
cd atlas-status
docker compose up -d --build
```

Running at `http://192.168.0.24:5003`

## Tech Stack

- Python / Flask
- Docker SDK for Python (`docker==7.1.0`)
- Socket mount — no database needed, data comes live from the daemon
- Docker + Docker Compose
- Ubuntu Server VM on Proxmox (Atlas Lab)

## Atlas Lab — Full Stack

| App | Port | Purpose |
|---|---|---|
| atlas-nutrition-tracker | 5001 | Meal tracking + shopping lists |
| atlas-dojo | 5002 | DevOps interview prep (spaced repetition) |
| atlas-status | 5003 | Container monitoring dashboard |

## Part of the DevOps Roadmap

**Week:** 2 — Docker Fundamentals  
Capstone project introducing the Docker daemon, Unix sockets, and the Docker SDK for Python. Completes the Week 2 trilogy alongside atlas-nutrition-tracker and atlas-dojo.
