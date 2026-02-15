#!/usr/bin/env python3
"""
log-rotator: Lightweight log rotation with compression and retention.

Usage:
    python rotator.py <path_pattern> [--max-size SIZE] [--compress FORMAT] [--retain DAYS]
"""

import os
import sys
import gzip
import bz2
import shutil
import glob
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RotationPolicy:
    """Configuration for log rotation behavior."""
    max_size_mb: float = 100.0
    max_age_days: int = 30
    compress: str = 'gzip'  # 'gzip', 'bz2', or 'none'
    timestamp_format: str = '%Y%m%d_%H%M%S'
    backup_count: int = 10


@dataclass
class RotationResult:
    """Result of a single rotation operation."""
    source: str
    destination: str
    original_size: int
    compressed_size: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)


class LogRotator:
    """Main log rotation engine."""

    COMPRESSORS = {
        'gzip': ('.gz', gzip.open),
        'bz2': ('.bz2', bz2.open),
        'none': ('', None),
    }

    def __init__(self, policy: Optional[RotationPolicy] = None):
        self.policy = policy or RotationPolicy()
        self.results: List[RotationResult] = []

    def should_rotate(self, filepath: str) -> bool:
        """Check if a file needs rotation based on size policy."""
        path = Path(filepath)
        if not path.exists():
            return False
        size_mb = path.stat().st_size / (1024 * 1024)
        return size_mb >= self.policy.max_size_mb

    def rotate_file(self, filepath: str, dry_run: bool = False) -> Optional[RotationResult]:
        """Rotate a single log file."""
        path = Path(filepath)
        if not path.exists():
            return None

        timestamp = datetime.now().strftime(self.policy.timestamp_format)
        ext_suffix, compressor = self.COMPRESSORS.get(
            self.policy.compress, self.COMPRESSORS['none']
        )

        dest_name = f"{path.stem}.{timestamp}{path.suffix}{ext_suffix}"
        dest_path = path.parent / dest_name

        original_size = path.stat().st_size

        if dry_run:
            print(f"[DRY RUN] Would rotate: {path} -> {dest_path}")
            return RotationResult(str(path), str(dest_path), original_size)

        if compressor:
            with open(path, 'rb') as f_in:
                with compressor(str(dest_path), 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            compressed_size = dest_path.stat().st_size
        else:
            shutil.copy2(path, dest_path)
            compressed_size = None

        # Truncate original file
        with open(path, 'w') as f:
            f.truncate(0)

        result = RotationResult(str(path), str(dest_path), original_size, compressed_size)
        self.results.append(result)
        return result

    def rotate(self, pattern: str, dry_run: bool = False) -> List[RotationResult]:
        """Rotate all files matching a glob pattern."""
        results = []
        for filepath in sorted(glob.glob(pattern)):
            if self.should_rotate(filepath):
                result = self.rotate_file(filepath, dry_run)
                if result:
                    results.append(result)
        return results

    def cleanup_old(self, directory: str, dry_run: bool = False) -> int:
        """Remove archived logs older than retention policy."""
        cutoff = datetime.now() - timedelta(days=self.policy.max_age_days)
        removed = 0
        dir_path = Path(directory)

        for ext in ('.gz', '.bz2'):
            for path in dir_path.glob(f'*{ext}'):
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime < cutoff:
                    if dry_run:
                        print(f"[DRY RUN] Would delete: {path}")
                    else:
                        path.unlink()
                    removed += 1

        return removed

    def summary(self) -> str:
        """Generate a summary of all rotation operations."""
        total_original = sum(r.original_size for r in self.results)
        total_compressed = sum(r.compressed_size or r.original_size for r in self.results)
        ratio = (1 - total_compressed / total_original) * 100 if total_original > 0 else 0

        lines = [
            f"Rotated {len(self.results)} file(s)",
            f"Original total: {total_original / 1024 / 1024:.2f} MB",
            f"Compressed total: {total_compressed / 1024 / 1024:.2f} MB",
            f"Space saved: {ratio:.1f}%",
        ]
        return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Log rotation tool')
    parser.add_argument('pattern', help='Glob pattern for log files')
    parser.add_argument('--max-size', default='100M', help='Max file size before rotation (e.g. 50M)')
    parser.add_argument('--compress', choices=['gzip', 'bz2', 'none'], default='gzip')
    parser.add_argument('--retain', type=int, default=30, help='Days to keep archived logs')
    parser.add_argument('--dry-run', action='store_true', help='Preview without executing')

    args = parser.parse_args()

    size_mb = float(args.max_size.rstrip('MmGg'))
    if args.max_size.upper().endswith('G'):
        size_mb *= 1024

    policy = RotationPolicy(
        max_size_mb=size_mb,
        max_age_days=args.retain,
        compress=args.compress,
    )

    rotator = LogRotator(policy)
    results = rotator.rotate(args.pattern, dry_run=args.dry_run)

    if results:
        print(rotator.summary())
    else:
        print("No files needed rotation.")


if __name__ == '__main__':
    main()