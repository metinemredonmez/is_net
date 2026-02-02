#!/bin/bash
#
# IOSP Rollback Script
# Rolls back to previous deployment
#

set -euo pipefail

# Configuration
DEPLOY_DIR="${DEPLOY_DIR:-/opt/iosp}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

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

# Get previous image tags
get_previous_images() {
    log_info "Finding previous image versions..."

    # Get current running images
    local backend_current=$(docker compose -f "${COMPOSE_FILE}" ps -q backend | xargs docker inspect --format='{{.Image}}' 2>/dev/null || echo "")
    local frontend_current=$(docker compose -f "${COMPOSE_FILE}" ps -q frontend | xargs docker inspect --format='{{.Image}}' 2>/dev/null || echo "")

    echo "Current backend: ${backend_current}"
    echo "Current frontend: ${frontend_current}"

    # List available images
    echo ""
    echo "Available backend images:"
    docker images --format "{{.Repository}}:{{.Tag}} ({{.CreatedSince}})" | grep "iosp-backend" | head -5

    echo ""
    echo "Available frontend images:"
    docker images --format "{{.Repository}}:{{.Tag}} ({{.CreatedSince}})" | grep "iosp-frontend" | head -5
}

# Rollback to specific version
rollback_to_version() {
    local version="$1"

    log_warn "Rolling back to version: ${version}"
    read -p "Are you sure? (yes/no): " confirm
    if [ "${confirm}" != "yes" ]; then
        log_info "Rollback cancelled"
        return 0
    fi

    # Update compose file with previous version
    export TAG="${version}"

    log_info "Stopping current containers..."
    docker compose -f "${COMPOSE_FILE}" down

    log_info "Starting previous version..."
    docker compose -f "${COMPOSE_FILE}" up -d

    # Wait for health checks
    log_info "Waiting for services to be healthy..."
    sleep 30

    # Check health
    if docker compose -f "${COMPOSE_FILE}" ps | grep -q "unhealthy"; then
        log_error "Some services are unhealthy after rollback!"
        docker compose -f "${COMPOSE_FILE}" ps
        return 1
    fi

    log_info "Rollback completed successfully!"
}

# Rollback to last working pre-deploy backup
rollback_to_backup() {
    log_info "Looking for pre-deploy backups..."

    local latest_backup=$(ls -t /opt/iosp/backups/postgres/*pre-deploy*.sql.gz 2>/dev/null | head -1)

    if [ -z "${latest_backup}" ]; then
        log_error "No pre-deploy backup found!"
        return 1
    fi

    log_info "Found backup: ${latest_backup}"
    log_warn "This will restore the database to pre-deploy state!"

    read -p "Are you sure? (yes/no): " confirm
    if [ "${confirm}" != "yes" ]; then
        log_info "Rollback cancelled"
        return 0
    fi

    # Restore database
    ./restore.sh postgres "${latest_backup}"

    log_info "Database rollback completed!"
}

# Quick rollback - pull previous tag
quick_rollback() {
    log_info "Performing quick rollback to previous deployment..."

    # Get the second-latest image for each service
    local backend_prev=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "iosp-backend" | sed -n '2p')
    local frontend_prev=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep "iosp-frontend" | sed -n '2p')

    if [ -z "${backend_prev}" ] || [ -z "${frontend_prev}" ]; then
        log_error "Previous images not found. Cannot perform quick rollback."
        return 1
    fi

    log_info "Rolling back to:"
    log_info "  Backend: ${backend_prev}"
    log_info "  Frontend: ${frontend_prev}"

    # Update and restart
    docker compose -f "${COMPOSE_FILE}" down

    # Pull specific tags
    docker tag "${backend_prev}" "iosp-backend:rollback"
    docker tag "${frontend_prev}" "iosp-frontend:rollback"

    export TAG="rollback"
    docker compose -f "${COMPOSE_FILE}" up -d

    log_info "Quick rollback completed!"
}

# Show usage
usage() {
    echo "IOSP Rollback Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  list              List available versions and backups"
    echo "  version <tag>     Rollback to specific version tag"
    echo "  backup            Rollback database to pre-deploy backup"
    echo "  quick             Quick rollback to previous deployment"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 version v1.2.3"
    echo "  $0 backup"
    echo "  $0 quick"
}

# Main
main() {
    cd "${DEPLOY_DIR}"

    local command="${1:-}"

    case "${command}" in
        list)
            get_previous_images
            ;;
        version)
            local version="${2:-}"
            if [ -z "${version}" ]; then
                log_error "Please specify version"
                usage
                exit 1
            fi
            rollback_to_version "${version}"
            ;;
        backup)
            rollback_to_backup
            ;;
        quick)
            quick_rollback
            ;;
        *)
            usage
            exit 1
            ;;
    esac
}

main "$@"
