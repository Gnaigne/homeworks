#!/bin/bash

# Mini ASM Docker Deployment Script
# This script helps manage the Docker deployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Start all services
start_services() {
    print_info "Starting all services..."
    docker compose up -d
    print_success "Services started!"
    echo ""
    print_info "Waiting for services to be healthy..."
    sleep 5
    show_status
}

# Stop all services
stop_services() {
    print_info "Stopping all services..."
    docker compose down
    print_success "Services stopped!"
}

# Restart all services
restart_services() {
    print_info "Restarting all services..."
    docker compose restart
    print_success "Services restarted!"
    sleep 3
    show_status
}

# Show status of services
show_status() {
    print_info "Service Status:"
    docker compose ps
    echo ""
    
    # Check if services are healthy
    print_info "Health Checks:"
    
    # Check backend
    if curl -f -s http://localhost:8080/health > /dev/null 2>&1; then
        print_success "Backend API is healthy (http://localhost:8080)"
    else
        print_warning "Backend API is not responding (http://localhost:8080)"
    fi
    
    # Check frontend
    if curl -f -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Frontend is healthy (http://localhost:3000)"
    else
        print_warning "Frontend is not responding (http://localhost:3000)"
    fi
    
    # Check database
    if docker compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        print_success "Database is healthy (localhost:5432)"
    else
        print_warning "Database is not responding (localhost:5432)"
    fi
}

# Show logs
show_logs() {
    if [ -z "$1" ]; then
        print_info "Showing logs for all services (Ctrl+C to exit)..."
        docker compose logs -f
    else
        print_info "Showing logs for $1 (Ctrl+C to exit)..."
        docker compose logs -f "$1"
    fi
}

# Rebuild services
rebuild_services() {
    print_info "Rebuilding all services..."
    docker compose build --no-cache
    print_success "Services rebuilt!"
}

# Clean everything (including volumes)
clean_all() {
    print_warning "This will remove all containers, volumes, and data. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Cleaning up everything..."
        docker compose down -v
        print_success "Everything cleaned!"
    else
        print_info "Cancelled"
    fi
}

# Execute command in container
exec_command() {
    if [ -z "$1" ]; then
        print_error "Please specify a service: backend, frontend, or db"
        exit 1
    fi
    
    print_info "Opening shell in $1 container..."
    docker compose exec "$1" sh
}

# Database backup
backup_db() {
    BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
    print_info "Creating database backup: $BACKUP_FILE"
    docker compose exec -T db pg_dump -U postgres mini_asm > "$BACKUP_FILE"
    print_success "Backup created: $BACKUP_FILE"
}

# Database restore
restore_db() {
    if [ -z "$1" ]; then
        print_error "Please specify backup file"
        exit 1
    fi
    
    if [ ! -f "$1" ]; then
        print_error "Backup file not found: $1"
        exit 1
    fi
    
    print_warning "This will restore database from $1. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_info "Restoring database from $1..."
        docker compose exec -T db psql -U postgres mini_asm < "$1"
        print_success "Database restored!"
    else
        print_info "Cancelled"
    fi
}

# Test API
test_api() {
    print_info "Testing API endpoints..."
    echo ""
    
    # Health check
    print_info "Testing health endpoint..."
    if response=$(curl -s http://localhost:8080/health); then
        echo "$response" | grep -q "status" && print_success "Health check passed" || print_error "Health check failed or invalid JSON"
    else
        print_error "Health check failed (Connection Error)"
    fi
    
    echo ""
    
    # List assets
    print_info "Testing list assets endpoint..."
    if response=$(curl -s "http://localhost:8080/assets?page_size=1"); then
        echo "$response" | grep -q "items" && print_success "List assets passed" || print_error "List assets failed or invalid JSON"
    else
        print_error "List assets failed (Connection Error)"
    fi
}

# Show help
show_help() {
    echo "Mini ASM Docker Deployment Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       Start all services"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  status      Show service status"
    echo "  logs        Show logs (optionally specify service: backend, frontend, db)"
    echo "  rebuild     Rebuild all services"
    echo "  clean       Remove all containers and volumes"
    echo "  exec        Execute shell in container (specify: backend, frontend, or db)"
    echo "  backup      Create database backup"
    echo "  restore     Restore database from backup file"
    echo "  test        Test API endpoints"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 logs backend"
    echo "  $0 exec db"
    echo "  $0 backup"
    echo "  $0 restore backup_20240309_120000.sql"
}

# Main script logic
main() {
    check_docker
    
    case "$1" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$2"
            ;;
        rebuild)
            rebuild_services
            ;;
        clean)
            clean_all
            ;;
        exec)
            exec_command "$2"
            ;;
        backup)
            backup_db
            ;;
        restore)
            restore_db "$2"
            ;;
        test)
            test_api
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            if [ -z "$1" ]; then
                show_help
            else
                print_error "Unknown command: $1"
                echo ""
                show_help
                exit 1
            fi
            ;;
    esac
}

# Run main function
main "$@"
