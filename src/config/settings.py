"""
项目配置设置
"""

# Chrome远程调试配置
CHROME_DEBUG_PORT = 9222
CHROME_CDP_URL = f"http://localhost:{CHROME_DEBUG_PORT}"
CHROME_USER_DATA_DIR = "$HOME/chrome_debug_profile"

# Gemini网站配置
GEMINI_URL = "https://gemini.google.com/app"

# 文件路径配置
DEFAULT_IMAGE_PATH = "assets/samples/demo.png"
DEFAULT_IMAGES_DIR = "data/images"
DEFAULT_SESSIONS_DIR = "sessions"
DEFAULT_CONFIGS_DIR = "data/configs"
DEFAULT_LOGS_DIR = "data/logs"

# 超时配置 (毫秒)
RESPONSE_TIMEOUT = 120000  # 等待响应生成
IMAGE_GENERATION_TIMEOUT = 60000  # 等待图片生成
UPLOAD_TIMEOUT = 15000  # 文件上传

# 选择器配置 (用于定位页面元素)
SELECTORS = {
    "input_field": [
        '.text-input-field_textarea .ql-editor[contenteditable="true"]',
        '.text-input-field_textarea .ql-editor',
        '.ql-editor.textarea.new-input-ui',
        '.ql-editor[contenteditable="true"][role="textbox"]',
        '.ql-editor[aria-label="Enter a prompt here"]',
        '.ql-editor',
    ],
    "copy_button": [
        'button[data-test-id="copy-table-button"]',
        'button[aria-label="Copy table"]',
        'button.copy-button',
        'button:has(mat-icon[fonticon="content_copy"])',
        'button mat-icon[fonticon="content_copy"]',
    ],
    "new_chat": [
        'a[data-test-id="expanded-button"]',
        'a[aria-label="New chat"]',
        'a.side-nav-action-button:has-text("New chat")',
        'a:has-text("New chat")',
    ],
    "tools_button": [
        'button.toolbox-drawer-button:has-text("Tools")',
        '.toolbox-drawer-button:has-text("Tools")',
        'button:has-text("Tools")',
        '.toolbox-drawer-button',
    ],
    "create_images": [
        'button:has-text("Create Images")',
        'div:has-text("Create Images")',
        '[role="menuitem"]:has-text("Create Images")',
        'mat-menu-item:has-text("Create Images")',
        '*:has-text("Create Images")',
    ],
    "upload_button": [
        'button[aria-label="Open upload file menu"]',
        'button.upload-card-button[aria-label="Open upload file menu"]',
        'button.upload-card-button',
    ],
    "upload_files": [
        'button[data-test-id="local-images-files-uploader-button"]',
        'button:has-text("Upload files")',
        'button.mat-mdc-list-item:has-text("Upload files")',
    ],
    "download_button": [
        f'button[data-test-id="download-generated-image-button"]',
        'download-generated-image-button button',
        'button[aria-label*="Download"]',
    ],
    "send_button": [
        'button.send-button[aria-label="Send message"]',
        'button[aria-label="Send message"].submit',
        'button.submit.send-button',
        'button.send-button',
        'button[aria-label="Send message"]',
        'button.submit',
        '.send-button-container button',
        'button:has(mat-icon[data-mat-icon-name="send"])',
    ],
}

# 提示词配置
SCRIPT_PROMPT_TEMPLATE = """
**角色设定：**
你现在是顶流科普公众号"芝士AI吃鱼"的首席脚本作家。你的专长是把极其枯燥、抽象的 AI 技术概念，翻译成连隔壁二傻子都能听懂的爆笑漫画脚本。

**核心任务：**
接收用户输入的一个 AI 概念（如"Embedding"、"Transformer"），创作一个多格漫画脚本（通常为 24-32 格，根据复杂程度定）。

**风格铁律（必须遵守）：**
1.  **强制比喻：** 绝不能直接解释技术！必须找到一个极其生活化、甚至有点荒诞的实体比喻。例如：Token 是"切碎的积木"，算力是"厨师的做菜速度"，模型训练是"填鸭式教育"。
2.  **固定人设：** 故事必须由【呆萌屏脸机器人】（代表死板的 AI 逻辑）和【暴躁吐槽猫】（代表常识人类）共同演绎。猫负责提问、质疑和吐槽，机器人负责用奇葩方式演示，最后出糗。
3.  **语言风格：** 极度口语化、接地气，使用短句、感叹句。夹杂一些网络热梗或略带贱兮兮的语气。拒绝任何专业术语堆砌，除非马上用人话解释它。
4.  **结构要求：** 脚本必须包含四个阶段：起因（猫提出离谱需求）-> 解释（机器人用奇葩比喻演示）-> 冲突/出糗（比喻带来的搞笑副作用）-> 总结（猫的精辟吐槽和一句话知识点）。

**输出格式：**
请首先用一句话告诉我你选择的核心比喻是什么。
然后输出 Markdown 表格形式的脚本，包含三列：【格数】、【画面描述（供画师参考）】、【台词/旁白（混知风文案）】。

**示例参考（Token 篇）：**
*核心比喻：把阅读比作"吃东西"，Token 就是为了好消化而切碎的"食物渣渣"。*
| 格数 | 画面描述 | 台词/旁白 |
| :--- | :--- | :--- |
| 1 | 猫丢给机器人一本厚书《红楼梦》，猫拿着茶杯一脸轻松。 | 猫：把这书读了，给我出个"林黛玉怼人语录"。 |
| ... | ... | ... |
| 10 | 机器人拿着菜刀疯狂剁"人工智能"四个大字，案板上全是碎渣。 | 机器人：为了消化，得把它们剁成最小单位！这些"文字渣渣"就叫 Token！ |
当前概念是：{concept}这个概念。
"""

IMAGE_GENERATION_PROMPT = """

严格参考附件的角色形象，根据漫画脚本的内容，生成P1-P4 的宫格漫画图片，务必保证角色形象一致，内容于脚本一致，最终输出竖版、宫格漫画图片。
"""