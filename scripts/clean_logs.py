#!/usr/bin/env python3
"""
清理旧的日志文件

使用方法:
python scripts/clean_logs.py [days]

如果不指定天数，默认删除7天前的日志文件
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# 获取项目根目录
project_root = Path(__file__).parent.parent
logs_dir = project_root / "data" / "logs"

def clean_old_logs(days=7):
    """
    清理指定天数前的日志文件
    
    Args:
        days: 保留的天数，默认7天
    """
    if not logs_dir.exists():
        print(f"日志目录不存在: {logs_dir}")
        return
    
    # 计算截止时间
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    # 统计
    deleted_files = 0
    total_size = 0
    
    print(f"清理 {days} 天前的日志文件...")
    print(f"日志目录: {logs_dir}")
    
    # 遍历日志文件
    for log_file in logs_dir.glob("*.log"):
        if log_file.stat().st_mtime < cutoff_time:
            file_size = log_file.stat().st_size
            total_size += file_size
            log_file.unlink()
            deleted_files += 1
            print(f"已删除: {log_file.name}")
    
    # 显示统计信息
    if deleted_files > 0:
        print(f"\n清理完成! 共删除 {deleted_files} 个文件, 释放空间 {total_size / 1024 / 1024:.2f} MB")
    else:
        print("没有需要清理的文件")

def main():
    # 获取天数参数
    days = 7
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            print("错误: 天数必须是整数")
            sys.exit(1)
    
    # 执行清理
    clean_old_logs(days)

if __name__ == "__main__":
    main()