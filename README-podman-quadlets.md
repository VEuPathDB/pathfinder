# Pathfinder — Podman Quadlet Deployment

Deploy the Pathfinder stack as rootless Podman containers managed by
`systemctl --user`.

## Prerequisites

- **Podman 4.4+** (quadlet support)
- **systemd user session** active
- **loginctl enable-linger** (for services to survive logout / start at boot)

```bash
# Check Podman version
podman --version

# Enable linger so user services persist after logout
loginctl enable-linger $USER
```

## 1. Build the application images

From the project root:

```bash
# Podman's Buildah doesn't support Docker-style glob COPY fallbacks,
# so ensure this optional config file exists (empty is fine)
touch ollama_models.yaml

podman build -t pathfinder-api:latest -f apps/api/Dockerfile .

podman build -t pathfinder-web:latest -f apps/web/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=http://pathfinder-api:8000 .
```

## 2. Set up the environment file

The API container loads API keys and settings from
`~/.config/pathfinder/.env`. Copy the project `.env` (or `.env.example`)
there:

```bash
mkdir -p ~/.config/pathfinder
cp .env ~/.config/pathfinder/.env
# Edit as needed — at minimum set an LLM provider API key
```

## 3. Install the quadlet files

```bash
mkdir -p ~/.config/containers/systemd
cp quadlets/* ~/.config/containers/systemd/
systemctl --user daemon-reload
```

## 4. Start the stack

Kill the docker compose stack if it's running.

Starting the web service pulls in all its dependencies automatically:

```bash
systemctl --user start pathfinder-web
```

Or start everything explicitly:

```bash
systemctl --user start pathfinder-db pathfinder-redis pathfinder-qdrant pathfinder-api pathfinder-web
```

## 5. Check status

```bash
systemctl --user status pathfinder-db pathfinder-redis pathfinder-qdrant pathfinder-api pathfinder-web
```

## 6. View logs

```bash
# Follow API logs
journalctl --user -u pathfinder-api -f

# Last 100 lines from all Pathfinder services
journalctl --user -u 'pathfinder-*' -n 100
```

## 7. Enable on boot

With linger enabled, services with `WantedBy=default.target` start at boot:

```bash
systemctl --user enable pathfinder-db pathfinder-redis pathfinder-qdrant pathfinder-api pathfinder-web
```

## 8. Changing ports

Edit the `PublishPort=` line in the relevant `.container` file under
`~/.config/containers/systemd/`, then reload:

```bash
# Example: change web port to 8080
# Edit ~/.config/containers/systemd/pathfinder-web.container
#   PublishPort=8080:3000
systemctl --user daemon-reload
systemctl --user restart pathfinder-web
```

## 9. Rebuild images after code changes

```bash
podman build -t pathfinder-api:latest -f apps/api/Dockerfile .
systemctl --user restart pathfinder-api

podman build -t pathfinder-web:latest -f apps/web/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=http://pathfinder-api:8000 .
systemctl --user restart pathfinder-web
```

## 10. Stop everything

```bash
systemctl --user stop pathfinder-web pathfinder-api pathfinder-qdrant pathfinder-redis pathfinder-db
```

## 11. Remove persistent data

```bash
podman volume rm pathfinder-postgres-data pathfinder-redis-data pathfinder-qdrant-data
```

## Services overview

| Service | Image | Published port | Depends on |
|---------|-------|---------------|------------|
| pathfinder-db | postgres:16-alpine | — (internal) | — |
| pathfinder-redis | redis:7-alpine | — (internal) | — |
| pathfinder-qdrant | qdrant/qdrant:latest | — (internal) | — |
| pathfinder-api | localhost/pathfinder-api:latest | 8000 | db, redis |
| pathfinder-web | localhost/pathfinder-web:latest | 3000 | api |
