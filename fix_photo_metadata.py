#!/usr/bin/env python3
"""
iCloud Photos Metadata Fix Script

This script fixes file timestamps and provides additional features for managing
iCloud Photos exported from Apple's iCloud service.

Features:
- Fix file creation/modification timestamps using CSV metadata
- Duplicate detection using file checksums
- Organization by date into year/month folders
- Cleanup of deleted files
- Favorite collections management
- Statistics generation
- Dry-run mode for testing

Usage:
    python fix_photo_metadata.py --help
"""

import os
import sys
import csv
import argparse
import shutil
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict, Counter
import time


class PhotoMetadataFixer:
    def __init__(self, base_path, dry_run=False, verbose=False):
        self.base_path = Path(base_path)
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = {
            'files_processed': 0,
            'timestamps_fixed': 0,
            'duplicates_found': 0,
            'deleted_files': 0,
            'favorites': 0,
            'hidden_files': 0,
            'errors': []
        }
        self.duplicates = defaultdict(list)
        self.processed_files = []
        
    def log(self, message, level='INFO'):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
        
    def parse_apple_date(self, date_string):
        """Parse Apple's date format: 'Saturday September 16,2023 5:27 PM GMT'"""
        try:
            # Remove day of week and GMT
            date_part = date_string.split(',')[1].strip().replace(' GMT', '')
            # Parse the date
            return datetime.strptime(date_part, '%Y %I:%M %p')
        except Exception as e:
            self.log(f"Error parsing date '{date_string}': {e}", 'ERROR')
            return None
    
    def set_file_timestamps(self, file_path, creation_date):
        """Set file creation and modification timestamps"""
        if not creation_date:
            return False
            
        try:
            # Convert to timestamp
            timestamp = creation_date.timestamp()
            
            if self.dry_run:
                self.log(f"DRY RUN: Would set {file_path} timestamp to {creation_date}")
                return True
            
            # Set modification time
            os.utime(file_path, (timestamp, timestamp))
            
            # On macOS, also try to set creation time
            if sys.platform == 'darwin':
                os.system(f'SetFile -d "{creation_date.strftime("%m/%d/%Y %H:%M:%S")}" "{file_path}"')
            
            self.log(f"Fixed timestamp for {file_path.name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to set timestamp for {file_path}: {e}"
            self.log(error_msg, 'ERROR')
            self.stats['errors'].append(error_msg)
            return False
    
    def process_csv_file(self, csv_path, photos_dir):
        """Process a single CSV file and fix timestamps for photos in the directory"""
        self.log(f"Processing CSV: {csv_path}")
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    img_name = row['imgName']
                    file_checksum = row['fileChecksum']
                    favorite = row['favorite'] == 'yes'
                    hidden = row['hidden'] == 'yes'
                    deleted = row['deleted'] == 'yes'
                    original_date = self.parse_apple_date(row['originalCreationDate'])
                    view_count = int(row['viewCount'])
                    
                    # Find the actual file
                    file_path = photos_dir / img_name
                    
                    if not file_path.exists():
                        self.log(f"File not found: {file_path}", 'WARNING')
                        continue
                    
                    # Track file info
                    file_info = {
                        'path': str(file_path),
                        'name': img_name,
                        'checksum': file_checksum,
                        'favorite': favorite,
                        'hidden': hidden,
                        'deleted': deleted,
                        'original_date': original_date,
                        'view_count': view_count,
                        'size': file_path.stat().st_size
                    }
                    self.processed_files.append(file_info)
                    
                    # Track duplicates
                    self.duplicates[file_checksum].append(file_info)
                    
                    # Update stats
                    self.stats['files_processed'] += 1
                    if favorite:
                        self.stats['favorites'] += 1
                    if hidden:
                        self.stats['hidden_files'] += 1
                    if deleted:
                        self.stats['deleted_files'] += 1
                    
                    # Fix timestamp
                    if original_date and self.set_file_timestamps(file_path, original_date):
                        self.stats['timestamps_fixed'] += 1
                        
        except Exception as e:
            error_msg = f"Error processing CSV {csv_path}: {e}"
            self.log(error_msg, 'ERROR')
            self.stats['errors'].append(error_msg)
    
    def find_duplicates(self):
        """Find duplicate files based on checksums"""
        duplicates = {k: v for k, v in self.duplicates.items() if len(v) > 1}
        self.stats['duplicates_found'] = len(duplicates)
        
        if duplicates:
            self.log(f"Found {len(duplicates)} sets of duplicate files:")
            for checksum, files in duplicates.items():
                self.log(f"  Checksum {checksum}: {len(files)} files")
                for file_info in files:
                    self.log(f"    - {file_info['path']} ({file_info['size']} bytes)")
        
        return duplicates
    
    def organize_by_date(self, output_dir):
        """Organize files by date into year/month structure"""
        output_path = Path(output_dir)
        
        if not self.dry_run:
            output_path.mkdir(exist_ok=True)
        
        self.log(f"Organizing files by date in {output_path}")
        
        for file_info in self.processed_files:
            if not file_info['original_date']:
                continue
                
            date = file_info['original_date']
            year_month = f"{date.year}/{date.month:02d}"
            target_dir = output_path / year_month
            target_file = target_dir / file_info['name']
            
            if self.dry_run:
                self.log(f"DRY RUN: Would move {file_info['path']} to {target_file}")
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_info['path'], target_file)
                self.log(f"Copied {file_info['name']} to {year_month}/")
    
    def generate_reports(self, output_dir):
        """Generate various reports about the photo collection"""
        output_path = Path(output_dir)
        if not self.dry_run:
            output_path.mkdir(exist_ok=True)
        
        # Statistics report
        stats_file = output_path / "photo_statistics.json"
        
        # Add more detailed stats
        year_counts = Counter()
        file_type_counts = Counter()
        
        for file_info in self.processed_files:
            if file_info['original_date']:
                year_counts[file_info['original_date'].year] += 1
            
            ext = Path(file_info['name']).suffix.lower()
            file_type_counts[ext] += 1
        
        detailed_stats = {
            **self.stats,
            'years': dict(year_counts),
            'file_types': dict(file_type_counts),
            'total_size_gb': sum(f['size'] for f in self.processed_files) / (1024**3)
        }
        
        if not self.dry_run:
            with open(stats_file, 'w') as f:
                json.dump(detailed_stats, f, indent=2, default=str)
        
        # Duplicates report
        duplicates = self.find_duplicates()
        if duplicates:
            dupes_file = output_path / "duplicates.json"
            if not self.dry_run:
                with open(dupes_file, 'w') as f:
                    json.dump(duplicates, f, indent=2, default=str)
        
        # Favorites list
        favorites = [f for f in self.processed_files if f['favorite']]
        if favorites:
            favorites_file = output_path / "favorites.json"
            if not self.dry_run:
                with open(favorites_file, 'w') as f:
                    json.dump(favorites, f, indent=2, default=str)
        
        # Deleted files list
        deleted = [f for f in self.processed_files if f['deleted']]
        if deleted:
            deleted_file = output_path / "deleted_files.json"
            if not self.dry_run:
                with open(deleted_file, 'w') as f:
                    json.dump(deleted, f, indent=2, default=str)
        
        self.log(f"Generated reports in {output_path}")
    
    def process_all_directories(self):
        """Process all iCloud photo directories"""
        self.log("Starting to process all directories...")
        
        # Find all directories that match the pattern
        pattern = "iCloud Fotos Teil * von 37"
        directories = []
        
        for item in self.base_path.iterdir():
            if item.is_dir() and ("iCloud Fotos Teil" in item.name and "von 37" in item.name):
                directories.append(item)
        
        directories.sort()
        self.log(f"Found {len(directories)} directories to process")
        
        for directory in directories:
            photos_dir = directory / "Photos"
            if not photos_dir.exists():
                self.log(f"No Photos directory found in {directory}", 'WARNING')
                continue
            
            # Find CSV files
            csv_files = list(photos_dir.glob("Photo Details*.csv"))
            if not csv_files:
                self.log(f"No CSV files found in {photos_dir}", 'WARNING')
                continue
            
            # Process each CSV file
            for csv_file in csv_files:
                self.process_csv_file(csv_file, photos_dir)
        
        self.log("Finished processing all directories")
        self.print_summary()
    
    def print_summary(self):
        """Print processing summary"""
        self.log("=== PROCESSING SUMMARY ===")
        self.log(f"Files processed: {self.stats['files_processed']}")
        self.log(f"Timestamps fixed: {self.stats['timestamps_fixed']}")
        self.log(f"Duplicates found: {self.stats['duplicates_found']}")
        self.log(f"Favorite files: {self.stats['favorites']}")
        self.log(f"Hidden files: {self.stats['hidden_files']}")
        self.log(f"Deleted files: {self.stats['deleted_files']}")
        self.log(f"Errors: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            self.log("Errors encountered:")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                self.log(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Fix iCloud Photos metadata and timestamps")
    parser.add_argument("path", help="Base path containing iCloud photo directories OR specific directory to process")
    parser.add_argument("--single-dir", action="store_true", help="Process only the specified directory (not all subdirs)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--organize", help="Organize files by date into specified directory")
    parser.add_argument("--reports", help="Generate reports in specified directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' does not exist")
        sys.exit(1)
    
    fixer = PhotoMetadataFixer(args.path, dry_run=args.dry_run, verbose=args.verbose)
    
    # Process directories
    if args.single_dir:
        # Process just the specified directory
        photos_dir = Path(args.path) / "Photos"
        if not photos_dir.exists():
            print(f"Error: No 'Photos' directory found in {args.path}")
            sys.exit(1)
        
        csv_files = list(photos_dir.glob("Photo Details*.csv"))
        if not csv_files:
            print(f"Error: No CSV files found in {photos_dir}")
            sys.exit(1)
        
        for csv_file in csv_files:
            fixer.process_csv_file(csv_file, photos_dir)
        
        fixer.print_summary()
    else:
        # Process all directories
        fixer.process_all_directories()
    
    # Generate reports if requested
    if args.reports:
        fixer.generate_reports(args.reports)
    
    # Organize by date if requested
    if args.organize:
        fixer.organize_by_date(args.organize)


if __name__ == "__main__":
    main()