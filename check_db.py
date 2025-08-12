#!/usr/bin/env python3
"""
Startup script to ensure database is ready and has all required columns.
This can be run before starting the application to prevent crashes.
"""

import sys
import os
import sqlite3

def check_and_fix_database():
    """Check if database has required columns and add them if missing"""
    try:
        # Try to find the database file
        possible_db_paths = [
            'instance/database.db',
            'database.db', 
            'app.db',
            'instance/app.db'
        ]
        
        db_path = None
        for path in possible_db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if not db_path:
            print("No existing database found - will be created on first run.")
            return True
        
        print(f"Checking database at: {db_path}")
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print("User table doesn't exist yet - will be created on first run.")
            conn.close()
            return True
        
        # Check if theme_preference column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'theme_preference' not in columns:
            print("Adding missing theme_preference column...")
            cursor.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
            cursor.execute("UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL")
            conn.commit()
            print("✅ Added theme_preference column successfully.")
        else:
            print("✅ theme_preference column already exists.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error checking database: {e}")
        return False

if __name__ == "__main__":
    print("Checking database compatibility...")
    success = check_and_fix_database()
    if success:
        print("Database is ready!")
        sys.exit(0)
    else:
        print("Database check failed!")
        sys.exit(1)
