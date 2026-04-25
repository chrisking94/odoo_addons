#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odoo MCP Base Release Script
Usage: python release.py [version]
Example: python release.py 1.1.0
"""
import subprocess
import sys
from pathlib import Path


VERSIONS = ['15.0', '16.0', '17.0', '18.0']
MANIFEST_PATH = Path('mcp_base/__manifest__.py')


def run_command(cmd, cwd=None):
    """Run command and return result"""
    print(f"→ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def update_manifest_version(version):
    """Update version in manifest file"""
    content = MANIFEST_PATH.read_text(encoding='utf-8')
    
    # Replace version
    import re
    new_content = re.sub(
        r"'version':\s*'[^']+'",
        f"'version': '{version}'",
        content
    )
    
    MANIFEST_PATH.write_text(new_content, encoding='utf-8')
    print(f"✅ Version updated to: {version}")


def get_odoo_version(branch):
    """Get Odoo version from branch name"""
    return f"{branch}.1.0.0"


def main():
    if len(sys.argv) != 2:
        print("Usage: python release.py <version>")
        print("Example: python release.py 1.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    print(f"\n🚀 Starting release {new_version}\n")
    
    # 0. Check workspace status
    print("📋 Step 0: Checking workspace status")
    status = run_command("git status --porcelain")
    if status:
        print("❌ Error: Workspace has uncommitted changes, please commit or stash first")
        print(status)
        sys.exit(1)
    print("✅ Workspace is clean")
    
    # 1. Switch to main branch
    print("\n📋 Step 1: Switching to main branch")
    run_command("git checkout main")
    
    # 2. Pull latest code
    print("\n📋 Step 2: Pulling latest code")
    run_command("git pull origin main")
    
    # 3. Update main branch version
    print(f"\n📋 Step 3: Updating main branch version to {new_version}")
    
    # Check current version
    import re
    current_content = MANIFEST_PATH.read_text(encoding='utf-8')
    match = re.search(r"'version':\s*'([^']+)'", current_content)
    if match and match.group(1) == new_version:
        print(f"⚠️ Version is already {new_version}, skipping update")
    else:
        update_manifest_version(new_version)
        
        # 4. Commit main branch
        print("\n📋 Step 4: Committing main branch")
        run_command(f"git add {MANIFEST_PATH}")
        run_command(f'git commit -m "Release version {new_version}"')
        run_command("git push origin main")
    
    # 5. Merge to version branches and update versions
    for branch in VERSIONS:
        odoo_version = get_odoo_version(branch)
        print(f"\n{'='*60}")
        print(f"📋 Processing branch: {branch} (Odoo {odoo_version})")
        print('='*60)
        
        # Switch to branch
        run_command(f"git checkout {branch}")
        
        # Pull latest code
        run_command(f"git pull origin {branch}")
        
        # Merge main (handle conflicts automatically)
        print(f"→ Merging main into {branch}")
        try:
            run_command(f"git merge main --no-edit")
        except SystemExit:
            # If conflict, use main branch files but keep branch version
            print("⚠️ Conflict detected, using main branch files...")
            
            # Save current branch version
            current_content = MANIFEST_PATH.read_text(encoding='utf-8')
            import re
            match = re.search(r"'version':\s*'([^']+)'", current_content)
            if match:
                branch_version = match.group(1)
                print(f"   Saving branch version: {branch_version}")
            
            # Use main branch file
            run_command(f"git checkout main -- {MANIFEST_PATH}")
            
            # Restore branch version
            if match:
                update_manifest_version(branch_version)
            
            # For CI/CD file, also use main branch
            ci_file = Path('.github/workflows/test.yml')
            if ci_file.exists():
                run_command(f"git checkout main -- {ci_file}")
            
            # Add all files
            run_command("git add -A")
            run_command(f'git commit -m "Merge main into {branch}"')
        
        # Update version to Odoo version format
        print(f"→ Updating version to {odoo_version}")
        update_manifest_version(odoo_version)
        
        # Commit and push
        run_command(f"git add {MANIFEST_PATH}")
        run_command(f'git commit -m "Update version to {odoo_version} for Odoo {branch}"')
        run_command(f"git push origin {branch}")
        print(f"✅ Branch {branch} released successfully")
    
    # 6. Switch back to main
    print(f"\n{'='*60}")
    print("📋 Done! Switching back to main branch")
    print('='*60)
    run_command("git checkout main")
    
    print(f"\n🎉 Version {new_version} released successfully!")
    print(f"\nReleased branches:")
    for branch in VERSIONS:
        print(f"  - {branch}: {get_odoo_version(branch)}")
    print(f"  - main: {new_version}")
    print(f"\nCheck CI/CD status: https://github.com/chrisking94/odoo_addons/actions")


if __name__ == '__main__':
    main()
