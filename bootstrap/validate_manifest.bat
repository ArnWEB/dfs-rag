@echo off
REM Validate manifest database entries via CLI (Windows)
REM Usage: validate_manifest.bat [database_path]

set DB_PATH=%~1
if "%DB_PATH%"=="" set DB_PATH=manifest.db

echo ==================================
echo Manifest Database Validation
echo Database: %DB_PATH%
echo ==================================
echo.

REM Check if database exists
if not exist "%DB_PATH%" (
    echo ERROR: Database not found: %DB_PATH%
    exit /b 1
)

echo 1. TOTAL RECORDS COUNT:
echo ------------------------
sqlite3 "%DB_PATH%" "SELECT COUNT(*) as total_records FROM manifest;"
echo.

echo 2. STATUS BREAKDOWN:
echo ---------------------
sqlite3 "%DB_PATH%" "SELECT status, COUNT(*) as count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM manifest), 2) as percentage FROM manifest GROUP BY status ORDER BY count DESC;"
echo.

echo 3. FILE vs DIRECTORY:
echo ---------------------
sqlite3 "%DB_PATH%" "SELECT CASE WHEN is_directory = 1 THEN 'Directories' ELSE 'Files' END as type, COUNT(*) as count FROM manifest GROUP BY is_directory;"
echo.

echo 4. ACL CAPTURE STATISTICS:
echo ---------------------------
sqlite3 "%DB_PATH%" "SELECT CASE WHEN acl_captured = 1 THEN 'ACL Captured' ELSE 'ACL Failed/Missing' END as acl_status, COUNT(*) as count FROM manifest WHERE is_directory = 0 GROUP BY acl_captured;"
echo.

echo 5. PERMISSION ERRORS (if any):
echo -------------------------------
for /f %%i in ('sqlite3 "%DB_PATH%" "SELECT COUNT(*) FROM manifest WHERE status = 'permission_denied';"') do set PERM_COUNT=%%i

if %PERM_COUNT% GTR 0 (
    echo Found %PERM_COUNT% permission errors:
    sqlite3 "%DB_PATH%" "SELECT file_path, error, is_directory FROM manifest WHERE status = 'permission_denied' ORDER BY file_path LIMIT 20;"
) else (
    echo No permission errors found.
)
echo.

echo 6. TOP 10 LARGEST FILES:
echo -------------------------
sqlite3 "%DB_PATH%" "SELECT file_name, parent_dir, ROUND(size / 1024.0 / 1024.0, 2) as size_mb FROM manifest WHERE is_directory = 0 ORDER BY size DESC LIMIT 10;"
echo.

echo 7. RECENTLY DISCOVERED FILES (Last 10):
echo ----------------------------------------
sqlite3 "%DB_PATH%" "SELECT file_name, status, datetime(first_seen, 'localtime') as discovered_at FROM manifest ORDER BY first_seen DESC LIMIT 10;"
echo.

echo 8. DIRECTORY TREE OVERVIEW:
echo ----------------------------
sqlite3 "%DB_PATH%" "SELECT parent_dir, COUNT(*) as file_count, SUM(CASE WHEN status = 'permission_denied' THEN 1 ELSE 0 END) as permission_errors FROM manifest GROUP BY parent_dir ORDER BY file_count DESC LIMIT 20;"
echo.

echo 9. ERROR SUMMARY:
echo -----------------
sqlite3 "%DB_PATH%" "SELECT status, error, COUNT(*) as count FROM manifest WHERE error IS NOT NULL GROUP BY status, error ORDER BY count DESC LIMIT 20;"
echo.

echo ==================================
echo Validation Complete!
echo ==================================
