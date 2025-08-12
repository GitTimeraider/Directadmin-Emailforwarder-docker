#!/usr/bin/env python3
"""
Temporary fix - removes theme_preference from model until migration is complete.
Run this script, then run your app, then run the migration, then restore the theme features.
"""

import os

def temporarily_disable_theme():
    """Temporarily comment out theme_preference from model"""
    model_file = 'app/models.py'
    
    if not os.path.exists(model_file):
        print(f"Model file {model_file} not found!")
        return False
    
    # Read current content
    with open(model_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Create backup
    with open(model_file + '.backup', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Created backup of models.py")
    
    # Remove theme-related code temporarily
    lines = content.split('\n')
    new_lines = []
    skip_theme_methods = False
    
    for line in lines:
        # Skip theme_preference column definition
        if 'theme_preference = db.Column' in line:
            new_lines.append('    # theme_preference = db.Column(db.String(20), default=\'light\', nullable=True)  # Temporarily disabled')
            continue
        
        # Mark start of theme methods to skip
        if 'def get_theme_preference(self):' in line:
            skip_theme_methods = True
            new_lines.append('    def get_theme_preference(self):')
            new_lines.append('        """Safely get theme preference - always returns light during migration"""')
            new_lines.append('        return \'light\'')
            new_lines.append('')
            continue
        
        # Skip theme method content but keep method signatures
        if skip_theme_methods:
            if line.strip().startswith('def ') and 'theme' not in line:
                skip_theme_methods = False
                new_lines.append(line)
            elif 'def set_theme_preference(self, theme):' in line:
                new_lines.append('    def set_theme_preference(self, theme):')
                new_lines.append('        """Safely set theme preference - disabled during migration"""')
                new_lines.append('        return False')
                new_lines.append('')
                continue
            elif not line.strip().startswith('def '):
                continue  # Skip theme method content
            else:
                skip_theme_methods = False
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write modified content
    with open(model_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print("✅ Temporarily disabled theme features in model")
    print("Now you can:")
    print("1. Start your application")
    print("2. Run: python add_theme_column.py")
    print("3. Run: python restore_theme.py")
    return True

if __name__ == "__main__":
    print("Temporarily disabling theme features to allow migration...")
    if temporarily_disable_theme():
        print("✅ Theme features temporarily disabled")
        print("Follow the steps above to complete the migration")
    else:
        print("❌ Failed to disable theme features")
