#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Odoo MCP Base 版本发布脚本
用法: python release.py [version]
示例: python release.py 1.1.0
"""
import subprocess
import sys
from pathlib import Path


VERSIONS = ['15.0', '16.0', '17.0', '18.0']
MANIFEST_PATH = Path('mcp_base/__manifest__.py')


def run_command(cmd, cwd=None):
    """运行命令并返回结果"""
    print(f"→ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"❌ 错误: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()


def update_manifest_version(version):
    """更新 manifest 文件中的版本号"""
    content = MANIFEST_PATH.read_text(encoding='utf-8')
    
    # 替换版本号
    import re
    new_content = re.sub(
        r"'version':\s*'[^']+'",
        f"'version': '{version}'",
        content
    )
    
    MANIFEST_PATH.write_text(new_content, encoding='utf-8')
    print(f"✅ 版本号已更新为: {version}")


def get_odoo_version(branch):
    """根据分支名获取 Odoo 版本号"""
    return f"{branch}.1.0.0"


def main():
    if len(sys.argv) != 2:
        print("用法: python release.py <新版本号>")
        print("示例: python release.py 1.1.0")
        sys.exit(1)
    
    new_version = sys.argv[1]
    
    print(f"\n🚀 开始发布版本 {new_version}\n")
    
    # 1. 确保在 main 分支
    print("📋 步骤 1: 切换到 main 分支")
    run_command("git checkout main")
    
    # 2. 拉取最新代码
    print("\n📋 步骤 2: 拉取最新代码")
    run_command("git pull origin main")
    
    # 3. 更新 main 分支版本号
    print(f"\n📋 步骤 3: 更新 main 分支版本号为 {new_version}")
    update_manifest_version(new_version)
    
    # 4. 提交 main 分支
    print("\n📋 步骤 4: 提交 main 分支")
    run_command(f"git add {MANIFEST_PATH}")
    run_command(f'git commit -m "Release version {new_version}"')
    run_command("git push origin main")
    
    # 5. 合并到各版本分支并更新版本号
    for branch in VERSIONS:
        odoo_version = get_odoo_version(branch)
        print(f"\n{'='*60}")
        print(f"📋 处理分支: {branch} (Odoo {odoo_version})")
        print('='*60)
        
        # 切换分支
        run_command(f"git checkout {branch}")
        
        # 合并 main
        print(f"→ 合并 main 到 {branch}")
        run_command(f"git merge main --no-edit")
        
        # 更新版本号
        print(f"→ 更新版本号为 {odoo_version}")
        update_manifest_version(odoo_version)
        
        # 提交并推送
        run_command(f"git add {MANIFEST_PATH}")
        run_command(f'git commit -m "Update version to {odoo_version} for Odoo {branch}"')
        run_command(f"git push origin {branch}")
    
    # 6. 切回 main 分支
    print(f"\n{'='*60}")
    print("📋 完成! 切回 main 分支")
    print('='*60)
    run_command("git checkout main")
    
    print(f"\n🎉 版本 {new_version} 发布成功!")
    print(f"\n发布的分支:")
    for branch in VERSIONS:
        print(f"  - {branch}: {get_odoo_version(branch)}")
    print(f"  - main: {new_version}")
    print(f"\n查看 CI/CD 状态: https://github.com/chrisking94/odoo_addons/actions")


if __name__ == '__main__':
    main()
