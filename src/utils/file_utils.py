"""
文件处理工具模块
"""

import os
import time
from pathlib import Path
from typing import List


def ensure_directory_exists(directory: str) -> Path:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Returns:
        Path: 目录的Path对象
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def save_text_to_file(content: str, filename: str = None, directory: str = 'data/sessions') -> str:
    """
    将文本内容保存到文件
    
    Args:
        content: 要保存的文本内容
        filename: 文件名，如果为None则使用时间戳生成
        directory: 保存目录，默认为"data"
        
    Returns:
        str: 保存的文件绝对路径
    """
    if filename is None:
        timestamp = int(time.time())
        filename = f"session_{timestamp}.txt"
    
    dir_path = ensure_directory_exists(directory)
    filepath = dir_path / filename
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[DEBUG] ✓ 文件已保存到: {filepath.absolute()}")
        return str(filepath.absolute())
    except Exception as e:
        print(f"[ERROR] 保存文件失败: {e}")
        raise


def load_text_from_file(filepath: str) -> str:
    """
    从文件加载文本内容
    
    Args:
        filepath: 文件路径
        
    Returns:
        str: 文件内容
    """
    file_path = Path(filepath)
    
    if not file_path.exists():
        raise Exception(f"文件不存在: {file_path.absolute()}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"[ERROR] 读取文件失败: {e}")
        raise


def extract_table_from_session(session_content: str) -> str:
    """
    从session文件内容中提取表格部分
    
    Args:
        session_content: session文件内容
        
    Returns:
        str: 提取的表格内容
    """
    try:
        parts = session_content.split("生成结果:")
        if len(parts) >= 2:
            result = parts[1].strip()
            # 移除开头的分隔线
            if result.startswith("=" * 80):
                result = result.split("\n", 1)[1] if "\n" in result else ""
            result = result.strip()
            
            if result:
                print(f"[DEBUG] ✓ 从 session 文件提取内容成功（长度: {len(result)} 字符）")
                return result
            else:
                raise Exception("Session 文件中没有找到生成结果内容")
        else:
            raise Exception("Session 文件格式不正确，未找到'生成结果'部分")
    except Exception as e:
        print(f"[ERROR] 解析 session 文件失败: {e}")
        raise


def get_image_files(directory: str) -> List[str]:
    """
    获取目录中的所有图片文件
    
    Args:
        directory: 目录路径
        
    Returns:
        List[str]: 图片文件路径列表
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    
    image_extensions = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']
    image_files = []
    
    for file_path in dir_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(str(file_path.absolute()))
    
    return image_files


def get_file_size(filepath: str) -> int:
    """
    获取文件大小
    
    Args:
        filepath: 文件路径
        
    Returns:
        int: 文件大小（字节）
    """
    try:
        return os.path.getsize(filepath)
    except:
        return 0


def get_absolute_path(filepath: str) -> str:
    """
    获取文件的绝对路径
    
    Args:
        filepath: 文件路径
        
    Returns:
        str: 绝对路径
    """
    return os.path.abspath(filepath)