#!/usr/bin/env bash
# Copy only. Default is a dry run. Originals are never removed.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE=/home/riki/web_dev/story_builder
DEST="$ROOT/local_data"
MODE="${1:---dry-run}"
case "$MODE" in --dry-run|--copy) ;; *) echo "Usage: $0 [--dry-run|--copy]" >&2; exit 2;; esac
command -v rsync >/dev/null
[[ -d "$SOURCE/video_audio_analyzer/models" ]] || { echo "Donor missing" >&2; exit 1; }
mkdir -p "$DEST"
# No overwrites of different existing files; restart safely after interruption.
# Story Builder now contains compatibility links into the retained runtime tree. Copy
# their contents, never the links (which could point a staged file at itself).
OPTS=(-rLtp --omit-dir-times --ignore-existing --partial --partial-dir=.rsync-partial --info=progress2,stats2
 --exclude=.git --exclude=.env --exclude=.venv --exclude=venv --exclude=node_modules
 --exclude=__pycache__ --exclude=.pytest_cache --exclude=.cache --exclude=cache
 --exclude='*.log' --exclude=logs --exclude=temp
 # Old databases contain donor queues/history, not portable media. Never migrate them.
 --exclude='*.sqlite' --exclude='*.sqlite-*' --exclude='*.sqlite3' --exclude='*.sqlite3-*'
 --exclude='*.db' --exclude='*.db-*' --exclude='*.db3' --exclude='*.db3-*')
[[ "$MODE" != --dry-run ]] || OPTS+=(--dry-run)
copy() {
 local relative="$1" destination
 case "$relative" in
  video_audio_analyzer/*) destination="engines/video-analyzer/${relative#video_audio_analyzer/}" ;;
  TTS_skills|TTS_skills/*) destination="engines/tts-skills${relative#TTS_skills}" ;;
  video_repertoire/downloads|video_repertoire/downloads/*) destination="youtube_downloads/files${relative#video_repertoire/downloads}" ;;
  video_repertoire/*) destination="video_repertoire/legacy/donor-video/${relative#video_repertoire/}" ;;
  video_summariser/*) destination="video_repertoire/legacy/${relative#video_summariser/}" ;;
  youtube_code/*) destination="engines/youtube-import/${relative#youtube_code/}" ;;
  audio/*) destination="engines/audio/${relative#audio/}" ;;
  *) echo "No approved destination for $relative" >&2; return 1 ;;
 esac
 [[ -e "$SOURCE/$relative" ]] || { echo "Missing optional source: $relative"; return; }
 mkdir -p "$DEST/$(dirname -- "$destination")"
 echo "Copying $relative"
 if [[ -d "$SOURCE/$relative" ]]; then
  mkdir -p "$DEST/$destination"
  rsync "${OPTS[@]}" "$SOURCE/$relative/" "$DEST/$destination/"
 else
  rsync "${OPTS[@]}" "$SOURCE/$relative" "$DEST/$destination"
 fi
}
# Standalone analyzer runtime and weights, preserving its expected layout.
for part in models src vendor configs scripts docker; do copy "video_audio_analyzer/$part"; done
for file in "$SOURCE"/video_audio_analyzer/Dockerfile* "$SOURCE"/video_audio_analyzer/*.sh "$SOURCE"/video_audio_analyzer/requirements*.txt "$SOURCE"/video_audio_analyzer/docker-compose.yml "$SOURCE"/video_audio_analyzer/README.md; do
 [[ ! -f "$file" ]] || copy "${file#"$SOURCE/"}"
done
copy TTS_skills
# Keep the searchable repertoire manifests and the media they reference. Raw
# analyzer runs, indexes, job folders and hand-made working directories are
# donor state, not runtime inputs; completed summaries/selected clips are
# imported through Vibe's explicit library flow instead.
for part in downloads uploads clips frames audio music manifests; do copy "video_repertoire/$part"; done
copy video_summariser/out_videos
for part in out_videos saved_mp3 split_mp3; do copy "youtube_code/$part"; done
# Selected audio code/config/models/media; skip environments, caches, test
# fixtures, documentation copies, notebooks and training datasets. Keep the
# licenses/readmes at each copied project root through explicit copies below.
mkdir -p "$DEST/engines/audio"
rsync "${OPTS[@]}" --exclude=.cache --exclude=wandb --exclude=logs \
 --exclude='*/tests/**' --exclude='*/notebooks/**' --exclude='*/docs/**' --exclude='*/.github/**' \
 --exclude='*/Data/**' --exclude='*/dataset/**' --exclude='*/outputs/**' --exclude='*.ipynb' \
 --include='*/' --include='*.py' --include='*.sh' --include='*.json' --include='*.yaml' --include='*.yml' \
 --include='*.toml' --include='*.txt' --include='*.md' --include='*.csv' --include='*.tsv' \
 --include='*.pt' --include='*.pth' --include='*.t7' --include='*.ckpt' --include='*.safetensors' --include='*.bin' --include='*.onnx' \
 --include='*.wav' --include='*.mp3' --include='*.flac' --include='*.ogg' --include='*.m4a' \
 --include='*.mp4' --include='*.webm' --include='*.aup3' --include='*.png' --include='*.jpg' --include='*.jpeg' --exclude='*' \
 "$SOURCE/audio/" "$DEST/engines/audio/"
for file in "$SOURCE"/audio/*/README* "$SOURCE"/audio/*/LICENSE* "$SOURCE"/audio/*/COPYING*; do
 [[ ! -f "$file" ]] || copy "${file#"$SOURCE/"}"
done
if [[ "$MODE" == --copy ]]; then
 python3 "$ROOT/tools/rebase_donor_video_manifests.py" \
  --stage-root "$DEST/video_repertoire/legacy/donor-video" --donor-root "$SOURCE/video_repertoire" \
  --downloads-root "$DEST/youtube_downloads/files" --youtube-root "$DEST/engines/youtube-import"
fi
echo "Finished $MODE. Saved under $DEST. Donor removal is NOT verified."
