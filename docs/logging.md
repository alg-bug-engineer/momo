# 日志系统使用说明

## 概述

本项目集成了完整的日志系统，支持分级别日志记录和按session分割的日志文件。

## 日志文件位置

日志文件保存在 `data/logs` 目录下，每个session会生成两个日志文件：

- `{session_id}_run.log` - 完整的运行日志（包含所有级别）
- `{session_id}_error.log` - 错误日志（只包含WARNING及以上级别）

## 日志级别

- **DEBUG**: 调试信息，详细的执行流程
- **INFO**: 一般信息，重要的步骤和状态
- **WARNING**: 警告信息，可能的问题但不影响正常运行
- **ERROR**: 错误信息，操作失败但程序可继续
- **CRITICAL**: 严重错误，可能导致程序终止

## 在代码中使用日志

### 1. 获取日志记录器

```python
from src.utils.logger import get_logger, init_logger

# 在主程序中初始化日志系统
session_id = str(int(time.time()))
logger = init_logger(session_id)

# 在其他模块中获取日志记录器
logger = get_logger()
```

### 2. 记录日志

```python
logger.debug("这是调试信息")
logger.info("这是普通信息")
logger.warning("这是警告信息")
logger.error("这是错误信息")
logger.critical("这是严重错误信息")

# 记录异常（包含堆栈跟踪）
try:
    # 一些可能出错的操作
    result = risky_operation()
except Exception as e:
    logger.exception(f"操作失败: {str(e)}")
```

### 3. 在类中使用

```python
class MyClass:
    def __init__(self, session_id):
        self.session_id = session_id
        self.logger = get_logger(session_id)
    
    def do_something(self):
        self.logger.info("开始执行操作")
        # ...
```

## 日志格式

日志文件中的每条记录包含以下信息：

```
时间戳 - 记录器名称 - 日志级别 - 文件名:行号 - 消息内容
```

示例：

```
2026-01-09 14:20:30 - session_1767939630 - INFO - auto_manga_workflow.py:125 - 主题文件夹已创建: /path/to/theme_dir
```

## 日志文件管理

- 日志文件按session自动分割，便于追踪特定会话的执行流程
- 错误日志单独记录，便于快速定位问题
- 日志文件保存在`data/logs`目录，可以根据需要清理旧日志
- 每个session_id使用时间戳生成，确保唯一性

## 注意事项

1. 日志系统已在项目核心模块中集成，使用`main.py`启动时会自动初始化
2. 在新开发的模块中，请使用统一的日志接口，不要直接使用print
3. 对于重要的操作步骤，建议使用INFO级别记录
4. 对于调试信息，使用DEBUG级别
5. 异常处理时，使用logger.exception记录完整的异常信息