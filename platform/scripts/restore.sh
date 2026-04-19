#!/usr/bin/env bash
# Forge Platform — DB restore script (Enterprise Audit item #5).
#
# Restores a gzipped pg_dump into a target database. Used for:
#   - monthly restore verification (restore into _restore_test DB, verify, drop)
#   - disaster recovery (restore into production DB)
#
# Usage:
#   ./restore.sh <backup-file>                      # restore into DB=forge_restore_test (safe)
#   TARGET_DB=forge_platform ./restore.sh <file>    # restore into prod DB (destructive)
#   DB_CONTAINER=my-db ./restore.sh <file>
#
# Safety:
#   - Script REFUSES to restore into the running production DB without
#     FORCE_PROD=1 (guard against accidental prod wipe).
#   - Target DB is DROPPED + CREATED before restore (clean slate).
#
# Exit codes:
#   0 success + smoke query OK
#   1 bad arguments / missing file
#   2 container missing
#   3 restore failed
#   4 safety guard tripped

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  echo "Env: TARGET_DB (default forge_restore_test), DB_CONTAINER (default platform-db-1),"
  echo "     POSTGRES_USER (default forge), FORCE_PROD=1 to permit production overwrite"
  exit 1
fi

BACKUP_FILE="$1"
DB_CONTAINER="${DB_CONTAINER:-platform-db-1}"
POSTGRES_USER="${POSTGRES_USER:-forge}"
TARGET_DB="${TARGET_DB:-forge_restore_test}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "ERROR: backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

# Safety: production DB requires explicit FORCE_PROD
if [[ "${TARGET_DB}" == "forge_platform" && "${FORCE_PROD:-0}" != "1" ]]; then
  echo "REFUSED: target is production DB 'forge_platform' without FORCE_PROD=1."
  echo "         Set FORCE_PROD=1 explicitly if this is an intentional restore."
  exit 4
fi

if ! docker ps --format '{{.Names}}' | grep -qx "${DB_CONTAINER}"; then
  echo "ERROR: container '${DB_CONTAINER}' not running" >&2
  exit 2
fi

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "Restoring ${BACKUP_FILE} → ${DB_CONTAINER}:${TARGET_DB}"

# --- Drop + recreate target DB ---
# Connecting to 'postgres' admin DB to DROP/CREATE the target.
log "Dropping and recreating ${TARGET_DB}"
docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d postgres \
  -c "DROP DATABASE IF EXISTS ${TARGET_DB};" \
  -c "CREATE DATABASE ${TARGET_DB};"

# --- Restore ---
log "Piping gzip stream into psql"
if ! gunzip -c "${BACKUP_FILE}" | docker exec -i "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" >/dev/null; then
  log "ERROR: psql import failed"
  exit 3
fi

# --- Smoke verify: table count > 0 ---
TABLE_COUNT=$(docker exec "${DB_CONTAINER}" psql -U "${POSTGRES_USER}" -d "${TARGET_DB}" -tAc \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
TABLE_COUNT=$(echo "${TABLE_COUNT}" | tr -d '[:space:]')

if [[ "${TABLE_COUNT}" -lt 1 ]]; then
  log "ERROR: restored DB has zero tables — likely malformed backup"
  exit 3
fi

log "Restore OK: ${TABLE_COUNT} tables present in ${TARGET_DB}"

if [[ "${TARGET_DB}" == "forge_restore_test" ]]; then
  log "NOTE: Verification-only restore; drop with:"
  log "  docker exec ${DB_CONTAINER} psql -U ${POSTGRES_USER} -d postgres -c 'DROP DATABASE ${TARGET_DB};'"
fi
