# iCloud Photos Metadata Fix Script

A Python script for processing and fixing metadata for photos obtained through Apple's "Request a copy of your data" feature. When users request a copy of their iCloud Photos library from Apple, the photos are delivered as downloadable ZIP files. However, all photo and video files in these ZIP archives have incorrect creation and modification timestamps (set to when Apple created the ZIP files) rather than the original photo capture dates. This script uses the CSV metadata files included in each ZIP to restore the correct original timestamps and provides additional photo management features.

## Problem Statement

When you request a copy of your iCloud Photos data from Apple:
1. Apple provides your photos as multiple downloadable ZIP files
2. Each ZIP contains a "Photos" folder with photo/video files and CSV metadata files
3. All media files have timestamps set to the ZIP creation date, not the original photo dates
4. The CSV files contain the correct original metadata including creation dates, view counts, and other attributes
5. Files are organized in numbered folders (e.g., "iCloud Fotos Teil 1 von 37" for German users)

This script bridges the gap by reading the CSV metadata from your downloaded and extracted ZIP files and applying the correct original timestamps to the corresponding photo and video files.

## Features

### Core Functionality
- **Timestamp Correction**: Sets file creation and modification dates using original photo metadata
- **Batch Processing**: Processes multiple export directories automatically
- **Single Directory Mode**: Process individual directories for testing or selective updates
- **Dry Run Mode**: Preview changes without modifying files

### Additional Features
- **Duplicate Detection**: Identifies duplicate files using checksums from metadata
- **Statistics Generation**: Creates detailed reports about photo collections
- **Date Organization**: Optionally organizes photos into year/month directory structure
- **Deleted File Tracking**: Identifies files marked as deleted in iCloud
- **Favorites Management**: Tracks and reports favorite photos
- **Hidden File Detection**: Identifies hidden photos

## Requirements

- Python 3.6 or higher
- Standard library modules (no additional dependencies)
- Compatible with macOS, Linux, and Windows
- Requires CSV metadata files from iCloud export

## Usage

### Basic Usage

Process a single directory (recommended for testing):
```bash
python fix_photo_metadata.py "iCloud Fotos Teil 1 von 37" --single-dir --dry-run
```

Process all directories in the base path:
```bash
python fix_photo_metadata.py /path/to/icloud/export --dry-run
```

Apply changes (remove --dry-run):
```bash
python fix_photo_metadata.py "iCloud Fotos Teil 1 von 37" --single-dir
```

### Advanced Options

Generate comprehensive reports:
```bash
python fix_photo_metadata.py /path/to/export --reports ./reports --dry-run
```

Organize photos by date:
```bash
python fix_photo_metadata.py /path/to/export --organize ./organized_photos --dry-run
```

Verbose logging:
```bash
python fix_photo_metadata.py /path/to/export --verbose --dry-run
```

## Command Line Arguments

- `path`: Base directory containing iCloud photo exports or specific directory to process
- `--single-dir`: Process only the specified directory instead of all subdirectories
- `--dry-run`: Show what would be done without making actual changes
- `--organize DIR`: Copy files organized by date (YYYY/MM) to specified directory
- `--reports DIR`: Generate JSON reports in specified directory
- `--verbose, -v`: Enable detailed logging

## Expected Directory Structure

After downloading and extracting the ZIP files from Apple's data request, the script expects this structure:
```
iCloud Fotos Teil X von Y/
├── Photos/
│   ├── Photo Details.csv
│   ├── Photo Details-1.csv
│   ├── Photo Details-2.csv
│   ├── IMG_001.HEIC
│   ├── IMG_002.JPG
│   └── ...
```

## CSV Metadata Format

The script processes CSV files with these columns:
- `imgName`: Photo filename
- `fileChecksum`: File hash for duplicate detection
- `originalCreationDate`: Original photo creation date
- `favorite`: Whether photo is marked as favorite (yes/no)
- `hidden`: Whether photo is hidden (yes/no)
- `deleted`: Whether photo is marked as deleted (yes/no)
- `viewCount`: Number of times photo was viewed
- `importDate`: Date photo was imported to iCloud

## Generated Reports

When using `--reports`, the script generates:
- `photo_statistics.json`: Overall statistics and file type breakdown
- `duplicates.json`: List of duplicate files by checksum
- `favorites.json`: List of favorite photos
- `deleted_files.json`: List of files marked as deleted

## Safety Features

- **Dry Run Mode**: Preview all changes before applying them
- **Error Logging**: Comprehensive error tracking and reporting
- **Non-destructive**: Original files are preserved when using organization features
- **Validation**: Checks for required directories and files before processing

## Limitations

- Date parsing assumes Apple's specific date format
- macOS creation date setting uses `SetFile` command (requires Developer Tools)
- Large photo libraries may require significant processing time
- CSV files must be present and properly formatted

## Example Output

```
[2024-01-01 12:00:00] INFO: Processing CSV: Photos/Photo Details.csv
[2024-01-01 12:00:01] INFO: Fixed timestamp for IMG_001.HEIC
[2024-01-01 12:00:01] INFO: Fixed timestamp for IMG_002.JPG
[2024-01-01 12:00:02] INFO: === PROCESSING SUMMARY ===
[2024-01-01 12:00:02] INFO: Files processed: 150
[2024-01-01 12:00:02] INFO: Timestamps fixed: 148
[2024-01-01 12:00:02] INFO: Duplicates found: 3
[2024-01-01 12:00:02] INFO: Favorite files: 12
[2024-01-01 12:00:02] INFO: Errors: 2
```

## How to Request Your Data from Apple

To obtain your iCloud Photos data:
1. Go to [privacy.apple.com](https://privacy.apple.com)
2. Sign in with your Apple ID
3. Select "Request a copy of your data"
4. Choose "iCloud Photos" from the available data types
5. Apple will prepare your data and send download links via email
6. Download all ZIP files and extract them to a directory
7. Run this script on the extracted directories

## Contributing

This script was developed to solve a specific problem with Apple's iCloud Photos data export process. Contributions, bug reports, and feature requests are welcome.