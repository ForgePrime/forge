#!/usr/bin/env bash
# Forge Platform — nightly DB backup script (Enterprise Audit item #5).
#
# Usage:
#   ./backup.sh                    # dumps to ./backups/forge-<ts>.sql.gz
#   BACKUP_DIR=/var/backups ./backup.sh
#   S3_BUCKET=my-backups ./backup.sh  # also uploads to s3://my-backups/
#
# Environment vars (all optional, sensible defaults for docker-compose setup):
#   DB_CONTAINER   (default: platform-db-1)
#   POSTGRES_USER  (default: forge)
#   POSTGRES_DB    (default: forge_platform)
#   BACKUP_DIR     (default: ./backups)
#   RETENTION_DAYS (default: 30 — older files removed)
#   S3_BUCKET      (default: empty — skip S3 upload)
#
# Exit codes:
#   0 success (local dump OK; S3 upload OK if configured)
#   1 pg_dump failed
#   2 S3 upload failed (local dump still valid)
#   3 container not running

set -euo pipefail

DB_CONTAINER="${DB_CONTAINER:-platform-db-1}"
POSTGRES_USER="${POSTGRES_USER:-forge}"
POSTGRES_DB="${POSTGRES_DB:-forge_platform}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"

TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
OUTFILE="${BACKUP_DIR}/forge-${TS}.sql.gz"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

# --- Sanity ---
if ! docker ps --format '{{.Names}}' | grep -qx "${DB_CONTAINER}"; then
  log "ERROR: container '${DB_CONTAINER}' not running. Start the stack first."
  exit 3
fi

mkdir -p "${BACKUP_DIR}"

# --- Dump ---
log "Dumping ${POSTGRES_DB} from ${DB_CONTAINER} → ${OUTFILE}"
if ! docker exec "${DB_CONTAINER}" pg_dump \
       -U "${POSTGRES_USER}" \
       --format=plain \
       --no-owner \
       --no-privileges \
       "${POSTGRES_DB}" \
     | gzip -9 > "${OUTFILE}"; then
  log "ERROR: pg_dump failed. Removing partial file."
  rm -f "${OUTFILE}"
  exit 1
fi

SIZE=$(du -h "${OUTFILE}" | cut -f1)
log "Backup complete: ${OUTFILE} (${SIZE})"

# --- Retention ---
log "Pruning backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}"
find "${BACKUP_DIR}" -maxdepth 1 -name "forge-*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -print -delete || true

# --- Optional S3 upload ---
if [[ -n "${S3_BUCKET}" ]]; then
  if ! command -v aws >/dev/null 2>&1; then
    log "WARN: aws CLI not installed; skipping S3 upload."
    exit 0
  fi
  log "Uploading to s3://${S3_BUCKET}/forge-${TS}.sql.gz"
  if ! aws s3 cp "${OUTFILE}" "s3://${S3_BUCKET}/forge-${TS}.sql.gz" --only-show-errors; then
    log "ERROR: S3 upload failed. Local backup preserved."
    exit 2
  fi
  log "S3 upload OK"
fi

log "Done."
