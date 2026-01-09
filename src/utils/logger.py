"""
日志管理模块

提供统一的日志记录功能，支持分级别日志和按session分割的日志文件
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.config.settings import DEFAULT_LOGS_DIR, LOG_LEVEL


class SessionLogger:
    """基于会话的日志管理器"""
    
    def __init__(self, session_id: Optional[str] = None, log_dir: str = DEFAULT_LOGS_DIR):
        """
        初始化日志管理器
        
        Args:
            session_id: 会话ID，用作日志文件名前缀
            log_dir: 日志目录路径
        """
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建日志文件名
        self.run_log_file = self.log_dir / f"{self.session_id}_run.log"
        self.error_log_file = self.log_dir / f"{self.session_id}_error.log"
        
        # 设置日志记录器
        self._setup_loggers()
    
    def _setup_loggers(self):
        """设置运行日志和错误日志记录器"""
        # 将字符串日志级别转换为logging常量
        numeric_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
        
        # 创建主记录器（所有级别）
        self.logger = logging.getLogger(f"session_{self.session_id}")
        self.logger.setLevel(numeric_level)
        
        # 创建错误日志记录器（只记录WARNING及以上级别）
        self.error_logger = logging.getLogger(f"session_{self.session_id}_error")
        self.error_logger.setLevel(logging.WARNING)
        
        # 清除已有的处理器
        self.logger.handlers.clear()
        self.error_logger.handlers.clear()
        
        # 创建运行日志文件处理器
        run_handler = logging.FileHandler(self.run_log_file, encoding='utf-8')
        run_handler.setLevel(numeric_level)
        
        # 创建错误日志文件处理器
        error_handler = logging.FileHandler(self.error_log_file, encoding='utf-8')
        error_handler.setLevel(logging.WARNING)
        
        # 创建控制台处理器 - 仅添加到主日志记录器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        
        # 创建格式化器
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # 设置格式化器
        run_handler.setFormatter(detailed_formatter)
        error_handler.setFormatter(detailed_formatter)
        console_handler.setFormatter(console_formatter)
        
        # 添加处理器到主日志记录器
        self.logger.addHandler(run_handler)
        self.logger.addHandler(console_handler)
        
        # 只添加文件处理器到错误日志记录器，避免控制台重复
        self.error_logger.addHandler(error_handler)
    
    def debug(self, message: str):
        """记录调试信息"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """记录一般信息"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """记录警告信息"""
        self.logger.warning(message)
        self.error_logger.warning(message)
    
    def error(self, message: str):
        """记录错误信息"""
        self.logger.error(message)
        self.error_logger.error(message)
    
    def critical(self, message: str):
        """记录严重错误信息"""
        self.logger.critical(message)
        self.error_logger.critical(message)
    
    def exception(self, message: str):
        """记录异常信息（包含堆栈跟踪）"""
        self.logger.exception(message)
        self.error_logger.exception(message)


# 全局日志记录器实例
_global_logger: Optional[SessionLogger] = None


def get_logger(session_id: Optional[str] = None) -> SessionLogger:
    """获取或创建全局日志记录器"""
    global _global_logger
    if _global_logger is None or (session_id and _global_logger.session_id != session_id):
        _global_logger = SessionLogger(session_id=session_id)
    return _global_logger


def init_logger(session_id: str) -> SessionLogger:
    """初始化日志记录器并返回实例"""
    global _global_logger
    _global_logger = SessionLogger(session_id=session_id)
    return _global_logger


# 简化的日志函数，方便直接调用
def debug(message: str):
    """记录调试信息"""
    get_logger().debug(message)


def info(message: str):
    """记录一般信息"""
    get_logger().info(message)


def warning(message: str):
    """记录警告信息"""
    get_logger().warning(message)


def error(message: str):
    """记录错误信息"""
    get_logger().error(message)


def critical(message: str):
    """记录严重错误信息"""
    get_logger().critical(message)


def exception(message: str):
    """记录异常信息（包含堆栈跟踪）"""
    get_logger().exception(message)