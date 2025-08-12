#!/usr/bin/env python3
"""
Database migration script to add theme_preference column to existing users.
Run this script once to update the database schema.
"""

import sys
import os
import sqlite3

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_theme_column_direct():
    """Add theme_preference column directly using SQLite"""
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
            print("Database file not found. Trying Flask app method...")
            return add_theme_column_flask()
        
        print(f"Found database at: {db_path}")
        
        # Connect to SQLite database directly
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'theme_preference' in columns:
            print("Column 'theme_preference' already exists in the database.")
            conn.close()
            return True
        
        print("Adding 'theme_preference' column...")
        
        # Add the column
        cursor.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
        
        # Update existing users
        cursor.execute("UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL")
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'theme_preference' in columns:
            print("Successfully added 'theme_preference' column to user table.")
            
            # Count updated users
            cursor.execute("SELECT COUNT(*) FROM user WHERE theme_preference = 'light'")
            count = cursor.fetchone()[0]
            print(f"Updated {count} existing users with default light theme.")
            
            conn.close()
            return True
        else:
            print("Failed to add column.")
            conn.close()
            return False
            
    except Exception as e:
        print(f"Direct SQLite method failed: {e}")
        return add_theme_column_flask()

def add_theme_column_flask():
    """Add theme_preference column using Flask app context"""
    try:
        from app import create_app
        from app.models import db
        
        app = create_app()
        
        with app.app_context():
            # Check if the column already exists by trying to query it
            try:
                result = db.session.execute("SELECT theme_preference FROM user LIMIT 1")
                print("Column 'theme_preference' already exists in the database.")
                return True
            except Exception:
                print("Column 'theme_preference' does not exist. Adding it now...")
                
                try:
                    # Add the column with default value 'light'
                    db.session.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
                    db.session.commit()
                    print("Successfully added 'theme_preference' column to user table.")
                    
                    # Update all existing users to have light theme by default
                    db.session.execute("UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL")
                    db.session.commit()
                    
                    # Count updated users
                    result = db.session.execute("SELECT COUNT(*) FROM user WHERE theme_preference = 'light'")
                    count = result.fetchone()[0]
                    print(f"Updated {count} existing users with default light theme.")
                    
                    return True
                except Exception as e:
                    print(f"Error adding column: {e}")
                    db.session.rollback()
                    return False
                    
    except Exception as e:
        print(f"Flask method failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("DirectAdmin Email Forwarder - Theme Column Migration")
    print("=" * 60)
    print("Adding theme_preference column to database...")
    print()
    
    success = add_theme_column_direct()
    
    if success:
        print()
        print("=" * 60)
        print("✅ Database migration completed successfully!")
        print("You can now restart the application and use the theme toggle.")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Database migration failed!")
        print("Please check the error messages above and try again.")
        print("=" * 60)
        sys.exit(1)
