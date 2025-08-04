#!/usr/bin/env python3
"""
iCloud Photos Metadata Fix Script

Fixes timestamps and organizes/exported iCloud photo data.

Key Features:
- Corrects file timestamps using Apple CSV metadata (GMT)
- Works directly in base directories (no 'Photos' folder needed)
- Finds duplicates
- Organizes by year/month
- Supports dry-run and reporting

Usage:
    python fix_photo_metadata.py --help
"""

import os
import sys
import csv
import argparse
import shutil
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict, Counter


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
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def parse_apple_date(self, date_string):
        """Parse Apple's date format: 'Saturday September 16,2023 5:27 PM GMT'"""
        try:
            cleaned = ' '.join(date_string.split(' ')[1:-1])  # Skip weekday + GMT
            dt = datetime.strptime(cleaned, '%B %d,%Y %I:%M %p')
            return dt.replace(tzinfo=timezone.utc)
        except Exception as e:
            self.log(f"Error parsing date '{date_string}': {e}", 'ERROR')
            return None

    def set_file_timestamps(self, file_path, creation_date):
        """Set file modification timestamp"""
        if not creation_date:
            return False
        try:
            timestamp = creation_date.timestamp()

            if self.dry_run:
                self.log(f"DRY RUN: Would set {file_path} timestamp to {creation_date}")
                return True

            os.utime(file_path, (timestamp, timestamp))

            if sys.platform == 'darwin':
                os.system(f'SetFile -d "{creation_date.strftime("%m/%d/%Y %H:%M:%S")}" "{file_path}"')

            self.log(f"Fixed timestamp for {file_path.name}")
            return True

        except Exception as e:
            error_msg = f"Failed to set timestamp for {file_path}: {e}"
            self.log(error_msg, 'ERROR')
            self.stats['errors'].append(error_msg)
            return False

    def process_csv_file(self, csv_path):
        """Process a single CSV file and fix timestamps for photos in the same directory"""
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

                    file_path = csv_path.parent / img_name
                    if not file_path.exists():
                        self.log(f"File not found: {file_path}", 'WARNING')
                        continue

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
                    self.duplicates[file_checksum].append(file_info)

                    self.stats['files_processed'] += 1
                    if favorite:
                        self.stats['favorites'] += 1
                    if hidden:
                        self.stats['hidden_files'] += 1
                    if deleted:
                        self.stats['deleted_files'] += 1

                    if original_date and self.set_file_timestamps(file_path, original_date):
                        self.stats['timestamps_fixed'] += 1

        except Exception as e:
            error_msg = f"Error processing CSV {csv_path}: {e}"
            self.log(error_msg, 'ERROR')
            self.stats['errors'].append(error_msg)

    def process_all_directories(self):
        self.log("Starting to process all directories...")
#        pattern = "iCloud Fotos Teil * von 37"
#        directories = [item for item in self.base_path.iterdir() if item.is_dir() and "iCloud Fotos Teil" in item.name and "von 37" in item.name]
#        directories.sort()
        pattern = re.compile(r"iCloudPhotosPart\d+of\d+")
        directories = [item for item in self.base_path.iterdir() if item.is_dir() and pattern.match(item.name)]
        directories.sort()

        self.log(f"Found {len(directories)} directories to process")

        for directory in directories:
            csv_files = list(directory.glob("Photo Details*.csv"))
            if not csv_files:
                self.log(f"No CSV files found in {directory}", 'WARNING')
                continue
            for csv_file in csv_files:
                self.process_csv_file(csv_file)

        self.log("Finished processing all directories")
        self.print_summary()

    def find_duplicates(self):
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
        output_path = Path(output_dir)
        if not self.dry_run:
            output_path.mkdir(exist_ok=True)

        stats_file = output_path / "photo_statistics.json"
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

        duplicates = self.find_duplicates()
        if duplicates:
            dupes_file = output_path / "duplicates.json"
            if not self.dry_run:
                with open(dupes_file, 'w') as f:
                    json.dump(duplicates, f, indent=2, default=str)

        favorites = [f for f in self.processed_files if f['favorite']]
        if favorites:
            favorites_file = output_path / "favorites.json"
            if not self.dry_run:
                with open(favorites_file, 'w') as f:
                    json.dump(favorites, f, indent=2, default=str)

        deleted = [f for f in self.processed_files if f['deleted']]
        if deleted:
            deleted_file = output_path / "deleted_files.json"
            if not self.dry_run:
                with open(deleted_file, 'w') as f:
                    json.dump(deleted, f, indent=2, default=str)

        self.log(f"Generated reports in {output_path}")

    def print_summary(self):
        self.log("=== PROCESSING SUMMARY ===")
        self.log(f"Files processed: {self.stats['files_processed']}")
        self.log(f"Timestamps fixed: {self.stats['timestamps_fixed']}")
        self.log(f"Duplicates found: {self.stats['duplicates_found']}")
        self.log(f"Favorite files: {self.stats['favorites']}")
        self.log(f"Hidden files: {self.stats['hidden_files']}")
        self.log(f"Deleted files: {self.stats['deleted_files']}")
        self.log(f"Errors: {len(self.stats['errors'])}")
        if self.stats['errors']:
            for error in self.stats['errors'][:10]:
                self.log(f"  - {error}")


def main():
    parser = argparse.ArgumentParser(description="Fix iCloud Photos metadata and timestamps")
    parser.add_argument("path", help="Base path containing iCloud photo directories OR single directory")
    parser.add_argument("--single-dir", action="store_true", help="Process only specified directory")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without making changes")
    parser.add_argument("--organize", help="Organize files by date into specified output folder")
    parser.add_argument("--reports", help="Generate reports in specified folder")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path '{args.path}' does not exist")
        sys.exit(1)

    fixer = PhotoMetadataFixer(args.path, dry_run=args.dry_run, verbose=args.verbose)

    if args.single_dir:
        target_dir = Path(args.path)
        csv_files = list(target_dir.glob("Photo Details*.csv"))
        if not csv_files:
            print(f"Error: No CSV files found in {target_dir}")
            sys.exit(1)

        for csv_file in csv_files:
            fixer.process_csv_file(csv_file)

        fixer.print_summary()
    else:
        fixer.process_all_directories()

    if args.reports:
        fixer.generate_reports(args.reports)

    if args.organize:
        fixer.organize_by_date(args.organize)


if __name__ == "__main__":
    main()
