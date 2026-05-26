import os
import sys
import shutil
import zipfile
import argparse
from datetime import datetime

# Calculate base directories
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(UTILS_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "projects.db")
PROJECTS_DIR = os.path.join(DATA_DIR, "projects")
BACKUPS_DIR = os.path.join(DATA_DIR, "backups")

def get_db_files():
    """Return database file paths that should be backed up if they exist."""
    files = [DB_PATH]
    # Check for SQLite WAL/SHM files
    for ext in ["-wal", "-shm"]:
        path = DB_PATH + ext
        if os.path.exists(path):
            files.append(path)
    return files

def cmd_backup(args):
    dest_dir = args.dest or BACKUPS_DIR
    os.makedirs(dest_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.zip"
    backup_path = os.path.join(dest_dir, backup_filename)
    
    print(f"Starting backup to {backup_path}...")
    
    if not os.path.exists(DB_PATH) and not os.path.exists(PROJECTS_DIR):
        print("Warning: No database or projects found to backup.")
    
    try:
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Backup SQLite database file(s)
            db_files = get_db_files()
            for db_file in db_files:
                if os.path.exists(db_file):
                    arcname = os.path.basename(db_file)
                    zipf.write(db_file, arcname)
                    print(f"Added database: {arcname}")
            
            # 2. Backup projects folder assets
            if os.path.exists(PROJECTS_DIR):
                for root, dirs, files in os.walk(PROJECTS_DIR):
                    for file in files:
                        full_path = os.path.join(root, file)
                        # Compute relative path under PROJECTS_DIR
                        rel_path = os.path.relpath(full_path, PROJECTS_DIR)
                        arcname = os.path.join("projects", rel_path)
                        zipf.write(full_path, arcname)
                print("Added project file assets.")
                
        print(f"Success: Backup created successfully at {backup_path}")
        print(f"Size: {os.path.getsize(backup_path) / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"Error creating backup: {e}")
        # Clean up partial zip file if it exists
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except OSError:
                pass
        sys.exit(1)

def cmd_restore(args):
    zip_path = args.backup_file
    if not os.path.exists(zip_path):
        # Check if it exists in default backups dir
        alternative_path = os.path.join(BACKUPS_DIR, zip_path)
        if os.path.exists(alternative_path):
            zip_path = alternative_path
        else:
            print(f"Error: Backup file not found at '{zip_path}' or in default backups directory.")
            sys.exit(1)
            
    print(f"Preparing to restore from {zip_path}...")
    
    # Verify zip integrity/contents before executing restore
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            namelist = zipf.namelist()
            if not any(name.startswith("projects.db") or name.startswith("projects/") for name in namelist):
                print("Error: The backup archive does not seem to contain valid database or project files.")
                sys.exit(1)
    except zipfile.BadZipFile:
        print("Error: The specified backup file is not a valid zip archive or is corrupted.")
        sys.exit(1)
        
    # Perform pre-restore safety backup
    if not args.no_safety:
        print("Creating safety backup of current state before restoring...")
        safety_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_filename = f"pre_restore_safety_{safety_timestamp}.zip"
        safety_path = os.path.join(BACKUPS_DIR, safety_filename)
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        
        try:
            with zipfile.ZipFile(safety_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                db_files = get_db_files()
                for db_file in db_files:
                    if os.path.exists(db_file):
                        zipf.write(db_file, os.path.basename(db_file))
                if os.path.exists(PROJECTS_DIR):
                    for root, dirs, files in os.walk(PROJECTS_DIR):
                        for file in files:
                            full_path = os.path.join(root, file)
                            rel_path = os.path.relpath(full_path, PROJECTS_DIR)
                            zipf.write(full_path, os.path.join("projects", rel_path))
            print(f"Safety backup created at {safety_path}")
        except Exception as e:
            print(f"Warning: Could not create safety backup: {e}.")
            if not args.force:
                print("Restore aborted. Use --force to proceed without a safety backup.")
                sys.exit(1)
    
    # Restore operation
    try:
        # Delete existing db-wal and db-shm files to prevent sqlite state conflict
        for ext in ["-wal", "-shm"]:
            path = DB_PATH + ext
            if os.path.exists(path):
                os.remove(path)
                
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            # Extract database files
            for name in zipf.namelist():
                if name.startswith("projects.db"):
                    zipf.extract(name, DATA_DIR)
                    print(f"Restored database file: {name}")
            
            # Extract project directory files
            # To avoid merging files, we can wipe the existing projects dir if requested,
            # but standard zip extract overwrites. Let's wipe the existing projects folder
            # first to ensure clean state.
            if os.path.exists(PROJECTS_DIR):
                shutil.rmtree(PROJECTS_DIR)
            os.makedirs(PROJECTS_DIR, exist_ok=True)
            
            project_files_extracted = 0
            for name in zipf.namelist():
                if name.startswith("projects/"):
                    # Extract this specific file
                    zipf.extract(name, DATA_DIR)
                    project_files_extracted += 1
            print(f"Restored {project_files_extracted} project file assets.")
            
        print("Success: Restore completed successfully.")
    except Exception as e:
        print(f"Error during restore: {e}")
        print("It is highly recommended to restore using the pre-restore safety backup if files were corrupted.")
        sys.exit(1)

def cmd_list(args):
    dest_dir = args.dest or BACKUPS_DIR
    if not os.path.exists(dest_dir):
        print(f"Backup directory '{dest_dir}' does not exist.")
        return
        
    files = [f for f in os.listdir(dest_dir) if f.endswith(".zip")]
    if not files:
        print(f"No backup files found in {dest_dir}")
        return
        
    print(f"Available backups in {dest_dir}:")
    print(f"{'Filename':<40} | {'Modified Time':<20} | {'Size (MB)':<10}")
    print("-" * 76)
    
    for f in sorted(files, reverse=True):
        fpath = os.path.join(dest_dir, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%Y-%m-%d %H:%M:%S")
        size_mb = os.path.getsize(fpath) / (1024*1024)
        print(f"{f:<40} | {mtime:<20} | {size_mb:<10.2f}")

def main():
    parser = argparse.ArgumentParser(description="AI Novel Generator Backup & Restore Utility")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command to run")
    
    # Backup parser
    p_backup = subparsers.add_parser("backup", help="Create a backup zip file")
    p_backup.add_argument("--dest", help="Destination folder for the backup zip")
    
    # Restore parser
    p_restore = subparsers.add_parser("restore", help="Restore database and files from backup zip")
    p_restore.add_argument("backup_file", help="Path to backup zip file or name of file in backups folder")
    p_restore.add_argument("--no-safety", action="store_true", help="Skip creating a safety backup of current state before restore")
    p_restore.add_argument("--force", action="store_true", help="Force proceed if safety backup creation fails")
    
    # List parser
    p_list = subparsers.add_parser("list", help="List all backup files in destination")
    p_list.add_argument("--dest", help="Folder to list backups from")
    
    args = parser.parse_args()
    
    if args.command == "backup":
        cmd_backup(args)
    elif args.command == "restore":
        cmd_restore(args)
    elif args.command == "list":
        cmd_list(args)

if __name__ == "__main__":
    main()
