"""
路径处理工具模块
"""

import sys
from pathlib import Path


def get_project_root(current_file: str) -> Path:
    """
    获取项目根目录
    
    Args:
        current_file: 当前文件的路径（通常是 __file__）
        
    Returns:
        Path: 项目根目录的Path对象
    """
    current_path = Path(current_file).absolute()
    
    # 如果当前文件在项目根目录下，返回其父目录
    if current_path.name == "main.py" or (current_path.parent.name == "src" and current_path.name != "__init__.py"):
        return current_path.parent
    elif current_path.parent.name == "tests":
        # 如果在tests目录下，返回其上级目录的上级目录（项目根目录）
        return current_path.parent.parent
    elif current_path.parent.name == "src":
        # 如果在src目录下，返回其上级目录（项目根目录）
        return current_path.parent
    else:
        # 默认情况下，假设当前文件在项目根目录下
        return current_path.parent


def setup_python_path(current_file: str):
    """
    设置Python路径，确保可以导入项目模块
    
    Args:
        current_file: 当前文件的路径（通常是 __file__）
    """
    project_root = get_project_root(current_file)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root