#!/usr/bin/env python3
"""Validate manifest database entries via CLI."""

import argparse
import sqlite3
from pathlib import Path
from typing import Any


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{title}")
    print("-" * len(title))


def query_db(db_path: Path, query: str, params: tuple = ()) -> list[tuple[Any, ...]]:
    """Execute a query and return results."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        return cursor.fetchall()


def format_rows(rows: list[tuple[Any, ...]], headers: list[str]) -> None:
    """Print rows in a formatted table."""
    if not rows:
        print("No data found.")
        return
    
    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(str(val)[:50]))  # Truncate long values
    
    # Print header
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(header_line)
    print("-" * len(header_line))
    
    # Print rows
    for row in rows:
        formatted = []
        for i, val in enumerate(row):
            val_str = str(val)[:50] if val is not None else "NULL"
            formatted.append(val_str.ljust(widths[i]))
        print(" | ".join(formatted))


def validate_manifest(db_path: Path) -> None:
    """Run all validation queries on the manifest database."""
    
    # Check if database exists
    if not db_path.exists():
        print(f"ERROR: Database not found: {db_path}")
        return
    
    print("=" * 50)
    print("Manifest Database Validation")
    print(f"Database: {db_path}")
    print("=" * 50)
    
    # 1. Total count
    print_section("1. TOTAL RECORDS COUNT")
    result = query_db(db_path, "SELECT COUNT(*) as total FROM manifest")
    print(f"Total records: {result[0][0]:,}")
    
    # 2. Status breakdown
    print_section("2. STATUS BREAKDOWN")
    rows = query_db(db_path, """
        SELECT 
            status,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM manifest), 2) as percentage
        FROM manifest 
        GROUP BY status 
        ORDER BY count DESC
    """)
    format_rows(rows, ["Status", "Count", "Percentage %"])
    
    # 3. File vs Directory
    print_section("3. FILE vs DIRECTORY")
    rows = query_db(db_path, """
        SELECT 
            CASE WHEN is_directory = 1 THEN 'Directories' ELSE 'Files' END as type,
            COUNT(*) as count
        FROM manifest 
        GROUP BY is_directory
    """)
    format_rows(rows, ["Type", "Count"])
    
    # 4. ACL Statistics
    print_section("4. ACL CAPTURE STATISTICS")
    rows = query_db(db_path, """
        SELECT 
            CASE WHEN acl_captured = 1 THEN 'ACL Captured' ELSE 'ACL Failed/Missing' END as acl_status,
            COUNT(*) as count
        FROM manifest 
        WHERE is_directory = 0
        GROUP BY acl_captured
    """)
    format_rows(rows, ["ACL Status", "Count"])
    
    # 5. Permission Errors
    print_section("5. PERMISSION ERRORS")
    rows = query_db(db_path, """
        SELECT COUNT(*) as count FROM manifest WHERE status = 'permission_denied'
    """)
    perm_count = rows[0][0]
    
    if perm_count > 0:
        print(f"Found {perm_count} permission errors:")
        rows = query_db(db_path, """
            SELECT file_path, error, is_directory 
            FROM manifest 
            WHERE status = 'permission_denied' 
            ORDER BY file_path 
            LIMIT 20
        """)
        format_rows(rows, ["File Path", "Error", "Is Dir"])
    else:
        print("No permission errors found.")
    
    # 6. Top 10 largest files
    print_section("6. TOP 10 LARGEST FILES")
    rows = query_db(db_path, """
        SELECT 
            file_name,
            parent_dir,
            ROUND(size / 1024.0 / 1024.0, 2) as size_mb
        FROM manifest 
        WHERE is_directory = 0 
        ORDER BY size DESC 
        LIMIT 10
    """)
    format_rows(rows, ["File Name", "Parent Dir", "Size (MB)"])
    
    # 7. Recently discovered
    print_section("7. RECENTLY DISCOVERED (Last 10)")
    rows = query_db(db_path, """
        SELECT 
            file_name,
            status,
            datetime(first_seen, 'localtime') as discovered_at
        FROM manifest 
        ORDER BY first_seen DESC 
        LIMIT 10
    """)
    format_rows(rows, ["File Name", "Status", "Discovered At"])
    
    # 8. Directory overview
    print_section("8. DIRECTORY TREE OVERVIEW (Top 20)")
    rows = query_db(db_path, """
        SELECT 
            parent_dir,
            COUNT(*) as file_count,
            SUM(CASE WHEN status = 'permission_denied' THEN 1 ELSE 0 END) as permission_errors
        FROM manifest 
        GROUP BY parent_dir 
        ORDER BY file_count DESC 
        LIMIT 20
    """)
    format_rows(rows, ["Parent Directory", "File Count", "Permission Errors"])
    
    # 9. Error summary
    print_section("9. ERROR SUMMARY")
    rows = query_db(db_path, """
        SELECT 
            status,
            error,
            COUNT(*) as count
        FROM manifest 
        WHERE error IS NOT NULL 
        GROUP BY status, error 
        ORDER BY count DESC 
        LIMIT 20
    """)
    format_rows(rows, ["Status", "Error", "Count"])
    
    # 10. Quick stats
    print_section("10. QUICK STATISTICS")
    stats = query_db(db_path, """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'discovered' THEN 1 ELSE 0 END) as discovered,
            SUM(CASE WHEN acl_captured = 1 THEN 1 ELSE 0 END) as acl_captured,
            SUM(CASE WHEN status = 'permission_denied' THEN 1 ELSE 0 END) as permission_denied,
            SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) as errors
        FROM manifest
    """)[0]
    
    print(f"Total records:       {stats[0]:>10,}")
    print(f"Discovered:          {stats[1]:>10,} ({stats[1]/stats[0]*100:.1f}%)")
    print(f"ACL captured:        {stats[2]:>10,} ({stats[2]/stats[0]*100:.1f}%)")
    print(f"Permission errors:   {stats[3]:>10,} ({stats[3]/stats[0]*100:.1f}%)")
    print(f"Other errors:        {stats[4]:>10,} ({stats[4]/stats[0]*100:.1f}%)")
    
    print("\n" + "=" * 50)
    print("Validation Complete!")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="Validate manifest database entries",
    )
    parser.add_argument(
        "db_path",
        nargs="?",
        type=Path,
        default=Path("manifest.db"),
        help="Path to SQLite database (default: manifest.db)",
    )
    
    args = parser.parse_args()
    validate_manifest(args.db_path)


if __name__ == "__main__":
    main()
