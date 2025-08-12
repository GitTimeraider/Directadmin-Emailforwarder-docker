#!/usr/bin/env python3
"""
Database migration script to add theme_preference column to existing users.
Run this script once to update the database schema.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User

def add_theme_column():
    """Add theme_preference column to users table if it doesn't exist"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if the column already exists by trying to query it
            result = db.session.execute("SELECT theme_preference FROM user LIMIT 1")
            print("Column 'theme_preference' already exists in the database.")
            return True
        except Exception as e:
            print(f"Column 'theme_preference' does not exist. Adding it now...")
            
            try:
                # Add the column with default value 'light'
                db.session.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
                db.session.commit()
                print("Successfully added 'theme_preference' column to user table.")
                
                # Update all existing users to have light theme by default
                users_updated = User.query.filter(User.theme_preference.is_(None)).update(
                    {'theme_preference': 'light'}, synchronize_session=False
                )
                db.session.commit()
                print(f"Updated {users_updated} existing users with default light theme.")
                
                return True
            except Exception as e:
                print(f"Error adding column: {e}")
                db.session.rollback()
                return False

if __name__ == "__main__":
    print("Adding theme_preference column to database...")
    success = add_theme_column()
    if success:
        print("Database migration completed successfully!")
        sys.exit(0)
    else:
        print("Database migration failed!")
        sys.exit(1)
