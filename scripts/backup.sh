#!/bin/bash
#
# IOSP Backup Script
# Creates backups of database and media files
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/opt/iosp/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_TYPE="${1:-scheduled}"  # scheduled, pre-deploy, manual

# Database config (from environment)
DB_HOST="${DB_HOST:-db}"
DB_NAME="${POSTGRES_DB:-iosp_db}"
DB_USER="${POSTGRES_USER:-iosp_user}"
DB_PASSWORD="${POSTGRES_PASSWORD}"

# AWS S3 config (optional)
S3_BUCKET="${S3_BUCKET:-}"
AWS_REGION="${AWS_REGION:-eu-west-1}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Create backup directories
create_directories() {
    mkdir -p "${BACKUP_DIR}/postgres"
    mkdir -p "${BACKUP_DIR}/media"
    mkdir -p "${BACKUP_DIR}/redis"
}

# Backup PostgreSQL database
backup_postgres() {
    log_info "Starting PostgreSQL backup..."
    local backup_file="${BACKUP_DIR}/postgres/iosp_db_${BACKUP_TYPE}_${TIMESTAMP}.sql.gz"

    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${DB_HOST}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        --no-owner \
        --no-acl \
        -F c \
        | gzip > "${backup_file}"

    if [ -f "${backup_file}" ]; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log_info "PostgreSQL backup completed: ${backup_file} (${size})"
        echo "${backup_file}"
    else
        log_error "PostgreSQL backup failed!"
        return 1
    fi
}

# Backup media files
backup_media() {
    log_info "Starting media files backup..."
    local backup_file="${BACKUP_DIR}/media/iosp_media_${BACKUP_TYPE}_${TIMESTAMP}.tar.gz"
    local media_dir="/opt/iosp/media"

    if [ -d "${media_dir}" ]; then
        tar -czf "${backup_file}" -C "$(dirname ${media_dir})" "$(basename ${media_dir})"

        if [ -f "${backup_file}" ]; then
            local size=$(du -h "${backup_file}" | cut -f1)
            log_info "Media backup completed: ${backup_file} (${size})"
            echo "${backup_file}"
        else
            log_error "Media backup failed!"
            return 1
        fi
    else
        log_warn "Media directory not found, skipping..."
    fi
}

# Backup Redis (optional)
backup_redis() {
    log_info "Starting Redis backup..."
    local backup_file="${BACKUP_DIR}/redis/iosp_redis_${BACKUP_TYPE}_${TIMESTAMP}.rdb"

    # Trigger Redis BGSAVE
    docker compose exec -T redis redis-cli BGSAVE || true
    sleep 5

    # Copy dump file
    docker compose cp redis:/data/dump.rdb "${backup_file}" 2>/dev/null || {
        log_warn "Redis backup skipped (no dump file found)"
        return 0
    }

    if [ -f "${backup_file}" ]; then
        local size=$(du -h "${backup_file}" | cut -f1)
        log_info "Redis backup completed: ${backup_file} (${size})"
        echo "${backup_file}"
    fi
}

# Upload to S3 (if configured)
upload_to_s3() {
    local file="$1"

    if [ -n "${S3_BUCKET}" ]; then
        log_info "Uploading ${file} to S3..."
        aws s3 cp "${file}" "s3://${S3_BUCKET}/backups/$(basename ${file})" \
            --region "${AWS_REGION}" \
            --storage-class STANDARD_IA
        log_info "Upload completed"
    fi
}

# Clean old backups
cleanup_old_backups() {
    log_info "Cleaning backups older than ${RETENTION_DAYS} days..."

    find "${BACKUP_DIR}" -type f -mtime "+${RETENTION_DAYS}" -delete

    # Also clean from S3 if configured
    if [ -n "${S3_BUCKET}" ]; then
        # List and delete old files from S3
        aws s3 ls "s3://${S3_BUCKET}/backups/" --recursive \
            | awk -v date="$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d)" '$1 < date {print $4}' \
            | xargs -I {} aws s3 rm "s3://${S3_BUCKET}/{}" 2>/dev/null || true
    fi

    log_info "Cleanup completed"
}

# Send notification
send_notification() {
    local status="$1"
    local message="$2"

    # Slack notification (if configured)
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -s -X POST "${SLACK_WEBHOOK_URL}" \
            -H 'Content-type: application/json' \
            -d "{\"text\":\"IOSP Backup ${status}: ${message}\"}" \
            || log_warn "Failed to send Slack notification"
    fi
}

# Main backup function
main() {
    log_info "=== IOSP Backup Started (Type: ${BACKUP_TYPE}) ==="

    create_directories

    local postgres_backup=""
    local media_backup=""
    local redis_backup=""
    local errors=0

    # Run backups
    postgres_backup=$(backup_postgres) || ((errors++))
    media_backup=$(backup_media) || ((errors++))
    redis_backup=$(backup_redis) || ((errors++))

    # Upload to S3
    [ -n "${postgres_backup}" ] && upload_to_s3 "${postgres_backup}"
    [ -n "${media_backup}" ] && upload_to_s3 "${media_backup}"
    [ -n "${redis_backup}" ] && upload_to_s3 "${redis_backup}"

    # Cleanup
    cleanup_old_backups

    # Summary
    log_info "=== IOSP Backup Completed ==="
    log_info "PostgreSQL: ${postgres_backup:-SKIPPED}"
    log_info "Media: ${media_backup:-SKIPPED}"
    log_info "Redis: ${redis_backup:-SKIPPED}"

    if [ ${errors} -gt 0 ]; then
        send_notification "FAILED" "Backup completed with ${errors} errors"
        exit 1
    else
        send_notification "SUCCESS" "All backups completed successfully"
        exit 0
    fi
}

main "$@"
