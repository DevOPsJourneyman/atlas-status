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
kubectl apply -f kubernetes/
```

**Note:** Docker socket monitoring is unavailable in k3s (containerd runtime — no Docker daemon). Dashboard shows daemon unreachable when deployed on the cluster. Fix tracked as a GitHub issue — planned migration to Kubernetes API.

See [atlas-lab](https://github.com/DevOpsJourneyman/atlas-lab) for infrastructure details.

## Tech Stack

- Python / Flask
- Docker SDK for Python (`docker==7.1.0`)
- Socket mount — queries live data from the Docker daemon
- Docker + Docker Compose
- Kubernetes (k3s) — Deployment, Service
- Ubuntu Server VMs on Proxmox (Atlas Lab)

## Atlas Lab — Full Stack

| App | NodePort | Purpose |
|---|---|---|
| atlas-nutrition-tracker | 30505 | Meal tracking + shopping lists |
| atlas-dojo | 30502 | DevOps interview prep (spaced repetition) |
| atlas-status | 30504 | Container monitoring dashboard |#

## Part of the DevOps Roadmap

**Weeks:** 2 (Docker) · 3–4 (Kubernetes)  
Portfolio goal: Demonstrate Docker daemon interaction via socket mount, Python SDK usage, and Kubernetes deployment. Known limitation: socket monitoring unavailable in k3s — tracked as an open issue.
