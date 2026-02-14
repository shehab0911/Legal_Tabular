#!/bin/bash
# Database restore script

BACKUP_FILE="$1"
DB_NAME="${POSTGRES_DB:-legal_review}"
DB_USER="${POSTGRES_USER:-reviewer}"
DB_HOST="${DB_HOST:-postgres}"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "✗ Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "Restoring database from $BACKUP_FILE..."

# Drop existing database (use with caution!)
read -p "This will drop the existing database. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Restore cancelled"
    exit 1
fi

# Restore backup
gunzip < "$BACKUP_FILE" | psql -h "$DB_HOST" -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "✓ Database restore completed"
else
    echo "✗ Database restore failed"
    exit 1
fi
