#!/usr/bin/env python3
"""
Restore theme features after migration is complete.
"""

import os

def restore_theme():
    """Restore theme features from backup"""
    model_file = 'app/models.py'
    backup_file = model_file + '.backup'
    
    if not os.path.exists(backup_file):
        print(f"Backup file {backup_file} not found!")
        return False
    
    # Restore from backup
    with open(backup_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    with open(model_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Restored theme features from backup")
    print("✅ Theme toggle should now work!")
    return True

if __name__ == "__main__":
    print("Restoring theme features...")
    if restore_theme():
        print("✅ Theme features restored successfully")
        print("You can now restart your application")
    else:
        print("❌ Failed to restore theme features")
