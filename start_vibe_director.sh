#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BACKEND_ROOT="$PROJECT_ROOT/backend"
FRONTEND_ROOT="$PROJECT_ROOT/frontend"
APP_URL="http://127.0.0.1:8082/"
API_URL="http://127.0.0.1:3020/api/status"
BACKEND_PID=""
FRONTEND_PID=""
IMAGE_WORKER_PID=""
VIDEO_WORKER_PID=""
# Manual video generation is enabled; automated runs still require verified output.
export VIBE_DIRECTOR_ENABLE_T2V="${VIBE_DIRECTOR_ENABLE_T2V:-1}"
export VIBE_DIRECTOR_ENABLE_FL2VA="${VIBE_DIRECTOR_ENABLE_FL2VA:-1}"
export VIBE_DIRECTOR_ENABLE_R2V="${VIBE_DIRECTOR_ENABLE_R2V:-1}"

api_healthy() {
  curl --silent --show-error --fail --max-time 2 "$API_URL" 2>/dev/null \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("backend",{}).get("connected") is True else 1)' 2>/dev/null
}

frontend_healthy() {
  curl --silent --show-error --fail --max-time 2 "$APP_URL" 2>/dev/null \
    | python3 -c 'import sys; sys.exit(0 if "Vibe Director" in sys.stdin.read() else 1)' 2>/dev/null
}

image_worker_healthy() {
  curl --silent --show-error --fail --max-time 2 "http://127.0.0.1:3020/api/images/worker" 2>/dev/null \
    | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("available") is True else 1)' 2>/dev/null
}

video_worker_healthy() {
  curl --silent --show-error --fail --max-time 2 "http://127.0.0.1:3020/api/video/worker" 2>/dev/null \
    | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin).get("available") is True else 1)' 2>/dev/null
}

port_is_open() {
  python3 - "$1" <<'PY'
import socket, sys
try:
    with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=0.3):
        sys.exit(0)
except OSError:
    sys.exit(1)
PY
}

stop_started_services() {
  local pid
  for pid in "$VIDEO_WORKER_PID" "$IMAGE_WORKER_PID" "$FRONTEND_PID" "$BACKEND_PID"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null || true
    fi
  done
  for pid in "$VIDEO_WORKER_PID" "$IMAGE_WORKER_PID" "$FRONTEND_PID" "$BACKEND_PID"; do
    if [[ -n "$pid" ]]; then wait "$pid" 2>/dev/null || true; fi
  done
}
trap stop_started_services EXIT INT TERM

for command in curl python3 node; do
  if ! command -v "$command" >/dev/null 2>&1; then
    printf 'Missing required command: %s\n' "$command" >&2
    exit 1
  fi
done

CONDA_BASE="$(conda info --base 2>/dev/null)" || {
  echo 'Conda is unavailable. Install/initialize Conda, then run this script again.' >&2
  exit 1
}
REACT_PYTHON="$CONDA_BASE/envs/react/bin/python"
if [[ ! -x "$REACT_PYTHON" ]]; then
  echo "The react Conda environment is missing: $REACT_PYTHON" >&2
  exit 1
fi
if [[ ! -x "$FRONTEND_ROOT/node_modules/.bin/vite" ]]; then
  echo "Frontend dependencies are missing. Run 'npm ci' once in $FRONTEND_ROOT" >&2
  exit 1
fi

if ! api_healthy; then
  if port_is_open 3020; then
    echo 'Port 3020 is occupied by a service that is not Vibe Director; leaving it untouched.' >&2
    exit 1
  fi
  echo 'Starting Vibe Director backend on port 3020...'
  (
    cd "$BACKEND_ROOT"
    export VIBE_DIRECTOR_DATA_DIR="$PROJECT_ROOT/local_data"
    export VIBE_DIRECTOR_PORT=3020
    export PYTHONPATH=.
    exec "$REACT_PYTHON" -m story_builder.isolated_server
  ) &
  BACKEND_PID=$!
  ready=0
  for _ in {1..60}; do
    if api_healthy; then ready=1; break; fi
    if ! kill -0 "$BACKEND_PID" 2>/dev/null; then break; fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo 'Backend did not become ready. Check the startup error above.' >&2
    exit 1
  fi
else
  echo 'Vibe Director backend is already running; reusing it.'
fi

if ! frontend_healthy; then
  if port_is_open 8082; then
    echo 'Port 8082 is occupied by a service that is not Vibe Director; leaving it untouched.' >&2
    exit 1
  fi
  echo 'Starting Vibe Director frontend on port 8082...'
  (
    cd "$FRONTEND_ROOT"
    exec ./node_modules/.bin/vite --host 127.0.0.1 --port 8082 --strictPort
  ) &
  FRONTEND_PID=$!
  ready=0
  for _ in {1..60}; do
    if frontend_healthy; then ready=1; break; fi
    if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then break; fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo 'Frontend did not become ready. Check the startup error above.' >&2
    exit 1
  fi
else
  echo 'Vibe Director frontend is already running; reusing it.'
fi

if ! image_worker_healthy; then
  echo 'Starting the Vibe Director image worker (shared workload scheduling applies)...'
  mkdir -p "$PROJECT_ROOT/local_data/logs"
  (
    cd "$BACKEND_ROOT"
    export VIBE_DIRECTOR_DATA_DIR="$PROJECT_ROOT/local_data"
    export PYTHONPATH=.
    exec "$REACT_PYTHON" -m story_builder.isolated_image_worker --enable-worker
  ) >>"$PROJECT_ROOT/local_data/logs/image-worker.log" 2>&1 &
  IMAGE_WORKER_PID=$!
  ready=0
  for _ in {1..30}; do
    if image_worker_healthy; then ready=1; break; fi
    if ! kill -0 "$IMAGE_WORKER_PID" 2>/dev/null; then break; fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo "Image worker did not become ready. See $PROJECT_ROOT/local_data/logs/image-worker.log" >&2
    exit 1
  fi
else
  echo 'Vibe Director image worker is already running; reusing it.'
fi

if ! video_worker_healthy; then
  echo 'Starting the Vibe Director video worker (shared workload scheduling applies)...'
  mkdir -p "$PROJECT_ROOT/local_data/logs"
  (
    cd "$BACKEND_ROOT"
    export VIBE_DIRECTOR_DATA_DIR="$PROJECT_ROOT/local_data"
    export PYTHONPATH=.
    exec "$REACT_PYTHON" -m story_builder.isolated_worker --enable-worker
  ) >>"$PROJECT_ROOT/local_data/logs/video-worker.log" 2>&1 &
  VIDEO_WORKER_PID=$!
  ready=0
  for _ in {1..30}; do
    if video_worker_healthy; then ready=1; break; fi
    if ! kill -0 "$VIDEO_WORKER_PID" 2>/dev/null; then break; fi
    sleep 1
  done
  if [[ "$ready" != 1 ]]; then
    echo "Video worker did not become ready. See $PROJECT_ROOT/local_data/logs/video-worker.log" >&2
    exit 1
  fi
else
  echo 'Vibe Director video worker is already running; reusing it.'
fi

echo 'Checking TRELLIS multi-view service (models stay unloaded)...'
if ! PYTHONPATH="$BACKEND_ROOT" "$REACT_PYTHON" -c 'import sys; from story_builder.services.multiview_3d import ensure_ready; ensure_ready(sys.argv[1])' "$PROJECT_ROOT/local_data" >>"$PROJECT_ROOT/local_data/logs/trellis-service.log" 2>&1; then
  echo 'TRELLIS multi-view service is unavailable; other tools remain ready. See local_data/logs/trellis-service.log.' >&2
fi

echo "Vibe Director is ready: $APP_URL"
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$APP_URL" >/dev/null 2>&1 || true
fi
echo 'Leave this terminal open while it runs. Press Ctrl+C to stop services started by this script.'

started_pids=()
for pid in "$VIDEO_WORKER_PID" "$IMAGE_WORKER_PID" "$BACKEND_PID" "$FRONTEND_PID"; do
  if [[ -n "$pid" ]]; then started_pids+=("$pid"); fi
done
if (( ${#started_pids[@]} )); then
  wait -n "${started_pids[@]}" || true
else
  while api_healthy && frontend_healthy && image_worker_healthy && video_worker_healthy; do sleep 5; done
fi
