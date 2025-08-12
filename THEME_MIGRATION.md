# Theme Migration Guide

This update adds purple theming and dark/light mode support to the DirectAdmin Email Forwarder application.

## Changes Made

### 1. Color Scheme
- Changed primary color from blue to purple (`#6f42c1` for light mode, `#8e44ad` for dark mode)
- Updated navigation bar to use purple tones
- All buttons and links now use purple color scheme

### 2. Dark Mode Support
- Added CSS custom properties (variables) for theme support
- Created dark mode color palette
- Added theme toggle in Settings page

### 3. Database Changes
- Added `theme_preference` column to `user` table
- Stores user's preferred theme ('light' or 'dark')
- Defaults to 'light' theme for new and existing users

## Installation

### For Existing Installations

1. **Run the database migration script:**
   ```bash
   python add_theme_column.py
   ```
   This will add the `theme_preference` column to existing user accounts.

2. **Restart the application:**
   ```bash
   # If using Docker
   docker-compose restart
   
   # If running directly
   # Stop and restart your Flask application
   ```

### For New Installations
No additional steps needed - the database will be created with the new column automatically.

## Features

### Theme Toggle
- Located in Settings page under "Appearance" section
- Toggle switch to change between light and dark themes
- Changes apply immediately
- Preference is saved to the database and persists across sessions

### Purple Color Scheme
- Navigation bar: Dark purple (`#4a2c70` for light mode, `#2d1b45` for dark mode)
- Primary buttons: Purple (`#6f42c1` for light mode, `#8e44ad` for dark mode)
- Links and accents: Purple theme throughout

### Dark Mode
- Dark background colors for better readability in low light
- Inverted text colors while maintaining good contrast
- All components support both light and dark themes

## Technical Details

### CSS Variables Used
```css
:root {
  --primary-color: #6f42c1;
  --primary-hover: #5a359a;
  --background-color: #f5f5f5;
  --surface-color: #ffffff;
  --text-color: #333333;
  --nav-background: #4a2c70;
  /* ... and more */
}

[data-theme="dark"] {
  --primary-color: #8e44ad;
  --background-color: #1a1a1a;
  --surface-color: #2d2d2d;
  --text-color: #e0e0e0;
  --nav-background: #2d1b45;
  /* ... and more */
}
```

### Database Schema Addition
```sql
ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light';
```

### API Endpoints
- `GET /settings/api/da-config` - Returns user's theme preference along with other config
- `POST /settings/api/theme` - Updates user's theme preference

## Troubleshooting

### Migration Script Issues
If the migration script fails:
1. Check database connectivity
2. Ensure the application is not running during migration
3. Manually add the column:
   ```sql
   ALTER TABLE user ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'light';
   UPDATE user SET theme_preference = 'light' WHERE theme_preference IS NULL;
   ```

### Theme Not Applying
1. Clear browser cache
2. Check if user is logged in
3. Verify the `data-theme` attribute is set on the `<body>` element
4. Check browser console for JavaScript errors

## Compatibility
- All modern browsers support CSS custom properties
- Falls back gracefully to light theme if JavaScript is disabled
- Mobile responsive design maintained for both themes
