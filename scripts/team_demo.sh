#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ACTION="${1:-init}"
MEMBER="${2:-member1}"

member_ports() {
  case "$1" in
    member1) echo "8000 5173" ;;
    member2) echo "8010 5183" ;;
    member3) echo "8020 5193" ;;
    member4) echo "8030 5203" ;;
    member5) echo "8040 5213" ;;
    *)
      echo "Unknown member: $1" >&2
      echo "Use one of: member1 member2 member3 member4 member5" >&2
      exit 1
      ;;
  esac
}

init_env() {
  for m in member1 member2 member3 member4 member5; do
    read -r backend_port frontend_port <<< "$(member_ports "$m")"
    env_file="${ROOT_DIR}/.env.${m}"
    cat > "$env_file" <<EOF
APP_NAME="LogiSense AI Copilot"
DEBUG=false
DATABASE_PATH="data/logisense-${m}.db"
ROW_LIMIT=50
AI_PROVIDER="fallback"
ENABLE_EXTERNAL_AI=false
BACKEND_PORT=${backend_port}
FRONTEND_PORT=${frontend_port}
LOGISENSE_INSTANCE="${m}"
GROQ_API_KEY=""
GROQ_MODEL="llama-3.1-8b-instant"
GEMINI_API_KEY=""
GEMINI_MODEL="gemini-1.5-flash"
EOF
    echo "Created ${env_file}"
  done

  echo "All member env files created."
  echo "Start one member instance: ./scripts/team_demo.sh start member3"
}

start_member() {
  read -r backend_port frontend_port <<< "$(member_ports "$MEMBER")"
  env_file="${ROOT_DIR}/.env.${MEMBER}"

  if [[ ! -f "$env_file" ]]; then
    echo "Missing ${env_file}. Run ./scripts/team_demo.sh init first."
    exit 1
  fi

  cd "$ROOT_DIR"
  set -a
  source "$env_file"
  set +a

  export VITE_API_BASE_URL="http://localhost:${backend_port}"

  echo "Starting ${MEMBER} -> backend:${backend_port} frontend:${frontend_port}"
  python3 run.py local
}

stop_member() {
  env_file="${ROOT_DIR}/.env.${MEMBER}"
  if [[ ! -f "$env_file" ]]; then
    echo "Missing ${env_file}. Run ./scripts/team_demo.sh init first."
    exit 1
  fi

  cd "$ROOT_DIR"
  set -a
  source "$env_file"
  set +a

  echo "Stopping ${MEMBER}"
  python3 run.py stop
}

reseed_member() {
  env_file="${ROOT_DIR}/.env.${MEMBER}"
  if [[ ! -f "$env_file" ]]; then
    echo "Missing ${env_file}. Run ./scripts/team_demo.sh init first."
    exit 1
  fi

  cd "$ROOT_DIR"
  set -a
  source "$env_file"
  set +a

  rm -f "$ROOT_DIR/${DATABASE_PATH}"
  echo "Removed ${DATABASE_PATH}; a fresh dataset will be seeded on next backend start."
}

case "$ACTION" in
  init)
    init_env
    ;;
  start)
    start_member
    ;;
  stop)
    stop_member
    ;;
  reseed)
    reseed_member
    ;;
  *)
    echo "Usage: $0 {init|start|stop|reseed} {member1|member2|member3|member4|member5}"
    exit 1
    ;;
esac
