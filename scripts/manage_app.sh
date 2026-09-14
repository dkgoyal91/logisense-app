#!/usr/bin/env bash
set -euo pipefail

ACTION="${1:-start}"
COMPOSE_FILES=("docker-compose.yml" "compose.yml" "docker-compose.yaml" "compose.yaml")
COMPOSE_FILE=""

for candidate in "${COMPOSE_FILES[@]}"; do
  if [[ -f "$candidate" ]]; then
    COMPOSE_FILE="$candidate"
    break
  fi
done

if [[ -z "$COMPOSE_FILE" ]]; then
  echo "No Docker Compose file found in the repo root."
  echo "Create docker-compose.yml first, then rerun this script."
  exit 1
fi

resolve_compose_cmd() {
  if command -v docker >/dev/null 2>&1; then
    if docker compose version >/dev/null 2>&1; then
      echo "docker compose"
      return
    fi
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
    return
  fi

  echo "MISSING_DOCKER" >&2
  echo "Docker Desktop is required on macOS. Install it and ensure 'docker compose' works in a new terminal." >&2
  exit 1
}

COMPOSE_CMD="$(resolve_compose_cmd)"

run_compose() {
  if [[ "$COMPOSE_CMD" == "docker compose" ]]; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    docker-compose -f "$COMPOSE_FILE" "$@"
  fi
}

case "$ACTION" in
  start)
    echo "Stopping any existing app instance..."
    run_compose down --remove-orphans --volumes || true
    echo "Starting app from $COMPOSE_FILE ..."
    run_compose up --build -d
    echo "Application started."
    echo "---"
    run_compose ps
    ;;
  stop)
    echo "Stopping app and removing existing containers..."
    run_compose down --remove-orphans --volumes || true
    echo "Application stopped."
    ;;
  restart)
    echo "Restarting app with a clean lifecycle..."
    run_compose down --remove-orphans --volumes || true
    run_compose up --build -d
    echo "Application restarted."
    echo "---"
    run_compose ps
    ;;
  logs)
    run_compose logs -f
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|logs}"
    exit 1
    ;;
esac
