#!/bin/bash
# Database backup script

BACKUP_DIR="/backups/legal_review"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DB_NAME="${POSTGRES_DB:-legal_review}"
DB_USER="${POSTGRES_USER:-reviewer}"
DB_HOST="${DB_HOST:-postgres}"

mkdir -p "$BACKUP_DIR"

echo "Starting database backup at $(date)"

# Create backup
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

if [ $? -eq 0 ]; then
    echo "✓ Backup completed: backup_$TIMESTAMP.sql.gz"
    
    # Upload to S3 if configured
    if [ ! -z "$AWS_S3_BUCKET" ]; then
        aws s3 cp "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz" "s3://$AWS_S3_BUCKET/backups/"
        echo "✓ Backup uploaded to S3"
    fi
    
    # Clean up old backups (keep 30 days)
    find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +30 -delete
    echo "✓ Old backups cleaned up"
else
    echo "✗ Backup failed"
    exit 1
fi
