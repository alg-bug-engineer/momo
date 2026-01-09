# Auto-Manga 自动漫画生成项目

这个项目通过自动化Chrome浏览器操作Gemini网站，实现自动生成漫画脚本并生成相应的漫画图片。

## 项目结构

```
auto-manga/
├── src/                      # 源代码目录
│   ├── __init__.py
│   ├── core/                  # 核心功能模块
│   │   ├── __init__.py
│   │   ├── browser_controller.py      # 浏览器控制器基类
│   │   ├── gemini_cdp_controller.py  # Gemini CDP 控制器
│   │   ├── auto_manga_workflow.py    # 自动漫画生成工作流
│   │   ├── image_uploader.py         # 图片上传模块
│   │   └── image_saver.py           # 图片保存模块
│   ├── utils/                  # 工具模块
│   │   ├── __init__.py
│   │   ├── browser_utils.py          # 浏览器操作工具
│   │   └── file_utils.py            # 文件处理工具
│   └── config/                 # 配置模块
│       ├── __init__.py
│       └── settings.py              # 项目配置设置
├── data/                      # 数据存储目录
│   ├── sessions/               # 会话文件目录
│   ├── images/                # 生成的图片目录
│   ├── configs/               # 配置文件目录
│   └── logs/                  # 日志文件目录
├── assets/                    # 资源文件目录
│   └── samples/               # 示例文件目录
├── tests/                     # 测试文件目录
│   └── test_upload_image.py     # 图片上传测试脚本
├── docs/                      # 文档目录
│   ├── prd.md                 # 产品需求文档
│   └── README.md              # 数据目录说明
├── backup/                    # 备份目录
├── main.py                    # 主入口脚本
├── requirements.txt           # 依赖包列表
└── README.md                 # 项目说明文档
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用前准备

1. 启动Chrome浏览器并开启远程调试：

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome_debug_profile"
```

2. 确保示例图片文件存在：`assets/samples/demo.png`

## 使用方法

### 运行完整工作流

```bash
python main.py
```

### 从已有session文件继续工作

```bash
python main.py session_1234567890.txt
```

### 仅测试图片上传功能

```bash
python test_upload_image.py
```

## 主要功能

1. **脚本生成**：向Gemini发送提示词，生成漫画脚本表格
2. **脚本保存**：将生成的脚本保存到本地文件
3. **图片生成**：在新窗口中使用Create Images工具生成漫画图片
4. **图片保存**：将生成的图片保存到本地文件夹

## 核心模块说明

### browser_controller.py
浏览器控制器基类，提供连接Chrome浏览器和打开Gemini网站的基本功能。

### auto_manga_workflow.py
自动漫画生成工作流的主控制器，协调整个漫画生成流程：
1. 连接浏览器并打开Gemini
2. 生成或加载脚本
3. 保存脚本到本地
4. 打开新聊天窗口
5. 选择Create Images工具
6. 上传示例图片
7. 发送多模态消息
8. 等待并保存生成的图片

### image_uploader.py
图片上传模块，提供多种上传策略：
1. Playwright filechooser监听器（推荐）
2. 真实文件输入框
3. 拖拽上传

### image_saver.py
图片保存模块，提供多种保存策略：
1. 浏览器原生下载（最高清晰度）
2. 直接下载图片URL
3. 元素截图（兜底方案）

### settings.py
项目配置文件，包含：
- Chrome远程调试配置
- Gemini网站配置
- 文件路径配置
- 超时配置
- 选择器配置
- 提示词模板

## 配置说明

大部分配置项在`src/config/settings.py`中，可以根据需要调整：
- Chrome远程调试端口
- 文件保存路径
- 超时时间
- 页面元素选择器
- 提示词模板

## 注意事项

1. 使用前需要启动Chrome远程调试
2. 确保网络连接正常
3. 可能需要登录Google账号
4. 首次运行可能需要手动确认浏览器权限