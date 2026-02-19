#!/bin/bash
# Validate manifest database entries via CLI
# Usage: ./validate_manifest.sh [database_path]

DB_PATH="${1:-./manifest.db}"

echo "=================================="
echo "Manifest Database Validation"
echo "Database: $DB_PATH"
echo "=================================="
echo

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found: $DB_PATH"
    exit 1
fi

echo "1. TOTAL RECORDS COUNT:"
echo "------------------------"
sqlite3 "$DB_PATH" "SELECT COUNT(*) as total_records FROM manifest;"
echo

echo "2. STATUS BREAKDOWN:"
echo "---------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM manifest), 2) as percentage
FROM manifest 
GROUP BY status 
ORDER BY count DESC;
EOF
echo

echo "3. FILE vs DIRECTORY:"
echo "---------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    CASE WHEN is_directory = 1 THEN 'Directories' ELSE 'Files' END as type,
    COUNT(*) as count
FROM manifest 
GROUP BY is_directory;
EOF
echo

echo "4. ACL CAPTURE STATISTICS:"
echo "---------------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    CASE WHEN acl_captured = 1 THEN 'ACL Captured' ELSE 'ACL Failed/Missing' END as acl_status,
    COUNT(*) as count
FROM manifest 
WHERE is_directory = 0
GROUP BY acl_captured;
EOF
echo

echo "5. PERMISSION ERRORS (if any):"
echo "-------------------------------"
PERMISSION_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM manifest WHERE status = 'permission_denied';")
if [ "$PERMISSION_COUNT" -gt 0 ]; then
    echo "Found $PERMISSION_COUNT permission errors:"
    sqlite3 "$DB_PATH" <<EOF
SELECT file_path, error, is_directory 
FROM manifest 
WHERE status = 'permission_denied' 
ORDER BY file_path 
LIMIT 20;
EOF
else
    echo "No permission errors found."
fi
echo

echo "6. TOP 10 LARGEST FILES:"
echo "-------------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    file_name,
    parent_dir,
    ROUND(size / 1024.0 / 1024.0, 2) as size_mb
FROM manifest 
WHERE is_directory = 0 
ORDER BY size DESC 
LIMIT 10;
EOF
echo

echo "7. RECENTLY DISCOVERED FILES (Last 10):"
echo "----------------------------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    file_name,
    status,
    datetime(first_seen, 'localtime') as discovered_at
FROM manifest 
ORDER BY first_seen DESC 
LIMIT 10;
EOF
echo

echo "8. DIRECTORY TREE OVERVIEW:"
echo "----------------------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    parent_dir,
    COUNT(*) as file_count,
    SUM(CASE WHEN status = 'permission_denied' THEN 1 ELSE 0 END) as permission_errors
FROM manifest 
GROUP BY parent_dir 
ORDER BY file_count DESC 
LIMIT 20;
EOF
echo

echo "9. ERROR SUMMARY:"
echo "-----------------"
sqlite3 "$DB_PATH" <<EOF
SELECT 
    status,
    error,
    COUNT(*) as count
FROM manifest 
WHERE error IS NOT NULL 
GROUP BY status, error 
ORDER BY count DESC 
LIMIT 20;
EOF
echo

echo "=================================="
echo "Validation Complete!"
echo "=================================="
