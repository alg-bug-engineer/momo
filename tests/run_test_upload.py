#!/usr/bin/env python3
"""
运行图片上传测试的辅助脚本
从项目根目录调用tests目录中的测试脚本
"""

import sys
import subprocess
from pathlib import Path

def main():
    """运行测试脚本"""
    project_root = Path(__file__).parent
    test_script = project_root / "tests" / "test_upload_image.py"
    
    # 使用subprocess运行测试脚本，并确保PYTHONPATH正确设置
    env = {
        **os.environ,
        'PYTHONPATH': str(project_root)
    }
    
    cmd = [sys.executable, str(test_script)]
    print(f"运行命令: {' '.join(cmd)}")
    print(f"工作目录: {project_root}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")
    
    try:
        result = subprocess.run(cmd, cwd=project_root, env=env)
        sys.exit(result.returncode)
    except Exception as e:
        print(f"运行测试脚本失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()