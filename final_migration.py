#!/usr/bin/env python3
"""
Final migration script - adds theme_preference column to User model dynamically.
Run this AFTER the application starts successfully.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def add_theme_column_final():
    """Add theme_preference column using SQLAlchemy"""
    try:
        from app.main import create_app
        from app.models import db, User
        
        print("Creating Flask app context...")
        app = create_app()
        
        with app.app_context():
            print("Checking if theme_preference column exists...")
            
            # Check if column already exists
            try:
                # Try to query the column
                result = db.session.execute("SELECT theme_preference FROM user LIMIT 1")
                print("✅ theme_preference column already exists!")
                
                # Now add it to the model dynamically
                if not hasattr(User, 'theme_preference'):
                    from sqlalchemy import Column, String
                    User.theme_preference = Column(String(20), default='light', nullable=True)
                    print("✅ Added theme_preference to User model!")
                
                return True
                
            except Exception as e:
                print(f"Column doesn't exist yet: {e}")
                print("Adding theme_preference column...")
                
                # Add the column to the database
                try:
                    db.session.execute("ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light'")
                    db.session.commit()
                    print("✅ Added theme_preference column to database!")
                    
                    # Update existing users
                    db.session.execute("UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL")
                    db.session.commit()
                    print("✅ Updated existing users with default theme!")
                    
                    # Add to model dynamically
                    from sqlalchemy import Column, String
                    User.theme_preference = Column(String(20), default='light', nullable=True)
                    print("✅ Added theme_preference to User model!")
                    
                    return True
                    
                except Exception as e:
                    print(f"Error adding column: {e}")
                    db.session.rollback()
                    return False
                    
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Final Theme Migration")
    print("=" * 60)
    print("Make sure your application is NOT running, then press Enter...")
    input()
    
    success = add_theme_column_final()
    
    if success:
        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("Now restart your application and the theme toggle will work!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ Migration failed!")
        print("=" * 60)
