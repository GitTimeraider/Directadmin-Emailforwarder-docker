#!/usr/bin/env python3
"""
Safe database migration - adds theme_preference column and then updates the model.
Run this BEFORE starting the application.
"""

import sys
import os
import sqlite3

def add_theme_column_safe():
    """Safely add theme_preference column to the database"""
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
            print("No existing database found.")
            print("The application will create the database with the column on first run.")
            # Add the column to the model file
            add_column_to_model()
            return True
        
        print(f"Found database at: {db_path}")
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user'")
        if not cursor.fetchone():
            print("User table doesn't exist yet.")
            print("The application will create it with the column on first run.")
            conn.close()
            add_column_to_model()
            return True
        
        # Check if theme_preference column exists
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'theme_preference' not in columns:
            print("Adding theme_preference column to database...")
            cursor.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
            cursor.execute("UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL")
            conn.commit()
            print("✅ Added theme_preference column to database.")
        else:
            print("✅ theme_preference column already exists in database.")
        
        conn.close()
        
        # Now add the column to the model
        add_column_to_model()
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def add_column_to_model():
    """Add the theme_preference column definition to the User model"""
    try:
        model_file = 'app/models.py'
        if not os.path.exists(model_file):
            print(f"Model file {model_file} not found!")
            return False
        
        # Read the current model file
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if theme_preference column is already defined
        if 'theme_preference = db.Column' in content:
            print("✅ theme_preference column already defined in model.")
            return True
        
        # Find the right place to insert the column definition
        if '# Unique encryption key per user for DA password' in content:
            # Insert before the encryption_key line
            new_content = content.replace(
                '    # Unique encryption key per user for DA password\n    encryption_key = db.Column(db.String(255), nullable=True)',
                '    # User preferences\n    theme_preference = db.Column(db.String(20), default=\'light\', nullable=True)  # \'light\' or \'dark\'\n\n    # Unique encryption key per user for DA password\n    encryption_key = db.Column(db.String(255), nullable=True)'
            )
            
            if new_content != content:
                # Write the updated content
                with open(model_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print("✅ Added theme_preference column definition to model.")
                return True
        
        print("⚠️  Could not automatically add column to model - manual edit needed.")
        return False
        
    except Exception as e:
        print(f"Error updating model: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Safe Theme Migration for DirectAdmin Email Forwarder")
    print("=" * 60)
    print()
    
    success = add_theme_column_safe()
    
    if success:
        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("You can now start the application safely.")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ Migration failed!")
        print("Please check the errors above.")
        print("=" * 60)
        sys.exit(1)
