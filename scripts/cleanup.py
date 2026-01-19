#!/usr/bin/env python3
"""
Cleanup script to remove old structure files and folders.

This script removes:
1. Old module directories (replaced by chakravyuh/)
2. Old root files (moved to new locations)
3. Python cache directories
4. Duplicate files
"""
import os
import shutil
from pathlib import Path
from typing import List

BASE_DIR = Path(__file__).parent.parent


class CleanupManager:
    """Manages cleanup of old files and directories."""

    def __init__(self, dry_run: bool = True):
        """
        Initialize cleanup manager.

        Args:
            dry_run: If True, only show what would be deleted
        """
        self.dry_run = dry_run
        self.removed = []
        self.errors = []

    def remove_path(self, path: Path, description: str = "") -> bool:
        """
        Remove a file or directory.

        Args:
            path: Path to remove
            description: Description of what's being removed

        Returns:
            True if successful
        """
        if not path.exists():
            return False

        try:
            if self.dry_run:
                size = self._get_size(path)
                print(f"[DRY RUN] Would remove: {path} ({size}) {description}")
                self.removed.append((path, description, size))
                return True

            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

            size = self._get_size(path) if path.exists() else "0"
            print(f"✓ Removed: {path} {description}")
            self.removed.append((path, description, size))
            return True

        except Exception as e:
            error_msg = f"Error removing {path}: {e}"
            print(f"❌ {error_msg}")
            self.errors.append(error_msg)
            return False

    def _get_size(self, path: Path) -> str:
        """Get size of file or directory."""
        try:
            if path.is_file():
                return f"{path.stat().st_size / 1024:.1f}KB"
            else:
                total = sum(
                    f.stat().st_size for f in path.rglob("*") if f.is_file()
                )
                if total > 1024 * 1024:
                    return f"{total / (1024 * 1024):.1f}MB"
                elif total > 1024:
                    return f"{total / 1024:.1f}KB"
                else:
                    return f"{total}B"
        except Exception:
            return "unknown"

    def cleanup_old_modules(self):
        """Remove old module directories."""
        old_modules = [
            "api",
            "core",
            "connectors",
            "ingestion",
            "qa",
            "rag_retriever",
            "utils",
            "vectorstores",
            "verification",
        ]

        print("\n🗑️  Removing old module directories...")
        for module in old_modules:
            path = BASE_DIR / module
            if path.exists() and path.is_dir():
                self.remove_path(
                    path,
                    f"(replaced by chakravyuh/{module}/)",
                )

    def cleanup_old_root_files(self):
        """Remove old root files."""
        old_files = [
            "main.py",  # Now in scripts/ingestion/scrape_aws.py
            "openapi.yaml",  # Now in docs/api/openapi.yaml
            "config.yaml",  # Now in config/config.yaml
            "config.yaml.example",  # Now in config/config.example.yaml
            "config.yaml.hybrid",  # Duplicate/old config
        ]

        print("\n🗑️  Removing old root files...")
        for file in old_files:
            path = BASE_DIR / file
            if path.exists():
                self.remove_path(path, "(moved to new location)")

    def cleanup_cache_directories(self):
        """Remove Python cache directories."""
        print("\n🗑️  Removing Python cache directories...")
        for cache_dir in BASE_DIR.rglob("__pycache__"):
            if cache_dir.is_dir():
                self.remove_path(cache_dir, "(Python cache)")

    def cleanup_old_infrastructure(self):
        """Remove old infrastructure directories."""
        old_infra = [
            "docker_services",  # Now in infrastructure/docker/
        ]

        print("\n🗑️  Removing old infrastructure...")
        for infra in old_infra:
            path = BASE_DIR / infra
            if path.exists():
                self.remove_path(path, "(moved to infrastructure/)")

    def cleanup_duplicate_scripts(self):
        """Remove duplicate scripts."""
        duplicates = [
            "scripts/db_init.py",  # Duplicate of scripts/setup/init_db.py
        ]

        print("\n🗑️  Removing duplicate scripts...")
        for script in duplicates:
            path = BASE_DIR / script
            if path.exists():
                self.remove_path(path, "(duplicate)")

    def cleanup_backup_directory(self):
        """Remove backup directory if empty or not needed."""
        backup_dir = BASE_DIR / "backup"
        if backup_dir.exists():
            if not any(backup_dir.iterdir()):
                self.remove_path(backup_dir, "(empty backup directory)")
            else:
                print(f"⚠️  Skipping {backup_dir} (not empty)")

    def cleanup_old_documentation(self):
        """Consolidate documentation files."""
        # These can be moved to docs/ or removed if consolidated
        old_docs = [
            "REORGANIZATION_COMPLETE.md",
            "REORGANIZATION_SUMMARY.md",
            "FINAL_STRUCTURE_SUMMARY.md",
            "QUICK_START.md",  # Should be in docs/guides/
            "CLEANUP_ANALYSIS.md",  # Temporary analysis file
        ]

        print("\n📝 Consolidating documentation...")
        docs_dir = BASE_DIR / "docs" / "guides"
        docs_dir.mkdir(parents=True, exist_ok=True)

        for doc in old_docs:
            path = BASE_DIR / doc
            if path.exists():
                if doc == "QUICK_START.md":
                    # Move to docs/guides/
                    new_path = docs_dir / "quick_start.md"
                    if not self.dry_run:
                        shutil.move(str(path), str(new_path))
                        print(f"✓ Moved: {path} → {new_path}")
                    else:
                        print(f"[DRY RUN] Would move: {path} → {new_path}")
                else:
                    # Remove temporary docs
                    self.remove_path(path, "(temporary documentation)")

    def cleanup_data_directories(self, migrate: bool = False):
        """
        Handle old data directories.

        Args:
            migrate: If True, migrate data to new locations
        """
        data_migrations = {
            "aws_docs": "data/raw",
            "embedded_docs": "data/processed",
            "knowledge": "data/knowledge",
        }

        print("\n📦 Handling old data directories...")
        for old_dir, new_dir in data_migrations.items():
            old_path = BASE_DIR / old_dir
            new_path = BASE_DIR / new_dir

            if not old_path.exists():
                continue

            if migrate:
                if not self.dry_run:
                    new_path.parent.mkdir(parents=True, exist_ok=True)
                    if new_path.exists():
                        print(f"⚠️  {new_path} already exists, merging...")
                        # Merge contents
                        for item in old_path.iterdir():
                            dest = new_path / item.name
                            if dest.exists():
                                print(f"⚠️  Skipping {item.name} (already exists)")
                            else:
                                shutil.move(str(item), str(dest))
                    else:
                        shutil.move(str(old_path), str(new_path))
                    print(f"✓ Migrated: {old_path} → {new_path}")
                else:
                    print(f"[DRY RUN] Would migrate: {old_path} → {new_path}")
            else:
                print(f"⚠️  Skipping {old_path} (large directory, use --migrate-data to move)")

    def run(self, migrate_data: bool = False):
        """Run all cleanup operations."""
        print("=" * 60)
        print("Chakravyuh Project Cleanup")
        print("=" * 60)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print()

        self.cleanup_old_modules()
        self.cleanup_old_root_files()
        self.cleanup_cache_directories()
        self.cleanup_old_infrastructure()
        self.cleanup_duplicate_scripts()
        self.cleanup_backup_directory()
        self.cleanup_old_documentation()
        self.cleanup_data_directories(migrate=migrate_data)

        print("\n" + "=" * 60)
        print("Cleanup Summary")
        print("=" * 60)
        print(f"Items to remove: {len(self.removed)}")
        print(f"Errors: {len(self.errors)}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(f"  - {error}")

        if self.dry_run:
            total_size = sum(
                size for _, _, size in self.removed if isinstance(size, (int, float))
            )
            print(f"\n💡 Run with --execute to actually remove files")
            print(f"💡 Use --migrate-data to migrate data directories")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cleanup old project structure")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually remove files (default is dry run)",
    )
    parser.add_argument(
        "--migrate-data",
        action="store_true",
        help="Migrate data directories to new locations",
    )

    args = parser.parse_args()

    manager = CleanupManager(dry_run=not args.execute)
    manager.run(migrate_data=args.migrate_data)


if __name__ == "__main__":
    main()
