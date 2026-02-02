#!/bin/bash
#
# IOSP Restore Script
# Restores database and media files from backup
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/iosp/backups}"

# Database config
DB_HOST="${DB_HOST:-db}"
DB_NAME="${POSTGRES_DB:-iosp_db}"
DB_USER="${POSTGRES_USER:-iosp_user}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# List available backups
list_backups() {
    echo "=== Available PostgreSQL Backups ==="
    ls -lt "${BACKUP_DIR}/postgres/"*.sql.gz 2>/dev/null | head -10 || echo "No backups found"
    echo ""
    echo "=== Available Media Backups ==="
    ls -lt "${BACKUP_DIR}/media/"*.tar.gz 2>/dev/null | head -10 || echo "No backups found"
}

# Restore PostgreSQL database
restore_postgres() {
    local backup_file="$1"

    if [ ! -f "${backup_file}" ]; then
        log_error "Backup file not found: ${backup_file}"
        return 1
    fi

    log_warn "This will OVERWRITE the current database!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "${confirm}" != "yes" ]; then
        log_info "Restore cancelled"
        return 0
    fi

    log_info "Creating backup of current database before restore..."
    ./backup.sh pre-restore

    log_info "Stopping services that depend on database..."
    docker compose stop backend celery-worker celery-beat || true

    log_info "Restoring PostgreSQL from ${backup_file}..."

    # Drop and recreate database
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();
    " || true

    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d postgres -c "CREATE DATABASE ${DB_NAME};"

    # Restore
    gunzip -c "${backup_file}" | PGPASSWORD="${DB_PASSWORD}" pg_restore \
        -h "${DB_HOST}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-owner \
        --no-acl \
        -j 4 \
        || log_warn "Some errors during restore (this may be normal for constraints)"

    log_info "Starting services..."
    docker compose start backend celery-worker celery-beat

    log_info "PostgreSQL restore completed!"
}

# Restore media files
restore_media() {
    local backup_file="$1"

    if [ ! -f "${backup_file}" ]; then
        log_error "Backup file not found: ${backup_file}"
        return 1
    fi

    log_warn "This will OVERWRITE the current media files!"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    if [ "${confirm}" != "yes" ]; then
        log_info "Restore cancelled"
        return 0
    fi

    local media_dir="/opt/iosp/media"

    log_info "Creating backup of current media files..."
    if [ -d "${media_dir}" ]; then
        mv "${media_dir}" "${media_dir}.bak.$(date +%Y%m%d_%H%M%S)"
    fi

    log_info "Restoring media from ${backup_file}..."
    mkdir -p "$(dirname ${media_dir})"
    tar -xzf "${backup_file}" -C "$(dirname ${media_dir})"

    log_info "Media restore completed!"
}

# Main
main() {
    local command="${1:-list}"
    local backup_file="${2:-}"

    case "${command}" in
        list)
            list_backups
            ;;
        postgres)
            if [ -z "${backup_file}" ]; then
                log_error "Please specify backup file"
                echo "Usage: $0 postgres /path/to/backup.sql.gz"
                exit 1
            fi
            restore_postgres "${backup_file}"
            ;;
        media)
            if [ -z "${backup_file}" ]; then
                log_error "Please specify backup file"
                echo "Usage: $0 media /path/to/backup.tar.gz"
                exit 1
            fi
            restore_media "${backup_file}"
            ;;
        *)
            echo "Usage: $0 {list|postgres|media} [backup_file]"
            exit 1
            ;;
    esac
}

main "$@"
