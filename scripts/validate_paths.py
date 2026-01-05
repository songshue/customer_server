#!/usr/bin/env python3
"""
验证脚本路径引用是否正确
"""
import os
import sys

def check_file_exists(file_path):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        print(f"✓ {file_path}")
        return True
    else:
        print(f"✗ {file_path} - 文件不存在")
        return False

def main():
    """主验证函数"""
    print("开始验证脚本文件路径...")
    print("=" * 50)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base_dir)
    
    # 验证脚本文件
    scripts_to_check = [
        # 启动脚本
        os.path.join(base_dir, "startup", "start_backend.bat"),
        os.path.join(base_dir, "startup", "start_frontend.bat"),
        os.path.join(base_dir, "startup", "start_docker.bat"),
        
        # 数据库脚本
        os.path.join(base_dir, "database", "init_database.py"),
        os.path.join(base_dir, "database", "migrations", "initial_migration.py"),
        
        # 开发工具脚本
        os.path.join(base_dir, "development", "create_sample_pdf.py"),
        
        # SQL文件
        os.path.join(base_dir, "sql", "orders_table.sql"),
        os.path.join(base_dir, "sql", "policies", "退换货政策.txt"),
    ]
    
    print("检查脚本文件:")
    all_exist = True
    for script in scripts_to_check:
        if not check_file_exists(script):
            all_exist = False
    
    print("\n检查相关配置文件:")
    # 验证docker-compose.yml中的引用
    docker_compose_path = os.path.join(project_root, "docker-compose.yml")
    if os.path.exists(docker_compose_path):
        with open(docker_compose_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "../scripts/database/init_database.py" in content:
                print("✓ docker-compose.yml 中的路径引用正确")
            else:
                print("✗ docker-compose.yml 中的路径引用可能不正确")
                all_exist = False
    else:
        print("✗ docker-compose.yml 不存在")
        all_exist = False
    
    print("\n检查README.md中的引用:")
    readme_path = os.path.join(project_root, "README.md")
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if "scripts\\startup\\start_backend.bat" in content and "scripts\\startup\\start_frontend.bat" in content:
                print("✓ README.md 中的路径引用正确")
            else:
                print("✗ README.md 中的路径引用可能不正确")
                all_exist = False
    else:
        print("✗ README.md 不存在")
        all_exist = False
    
    print("\n" + "=" * 50)
    if all_exist:
        print("✅ 所有路径验证通过！")
        return 0
    else:
        print("❌ 部分路径验证失败，请检查上述错误")
        return 1

if __name__ == "__main__":
    sys.exit(main())