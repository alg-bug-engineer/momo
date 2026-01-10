"""
自动漫画生成工作流控制器
"""

import asyncio
import os
import time
from pathlib import Path
from typing import List

import pyperclip

from src.core.browser_controller import BrowserController
from src.config.settings import (
    SELECTORS, 
    SCRIPT_PROMPT_TEMPLATE, 
    IMAGE_GENERATION_PROMPT,
    RESPONSE_TIMEOUT,
    UPLOAD_TIMEOUT,
    DEFAULT_IMAGE_PATH,
    DEFAULT_COVER_IMAGE_PATH,
    DEFAULT_IMAGES_DIR,
    DEFAULT_SESSIONS_DIR
)
from src.utils.browser_utils import find_working_selector, wait_for_content_stabilization, verify_upload
from src.utils.file_utils import (
    save_text_to_file, 
    load_text_from_file, 
    extract_table_from_session,
    get_absolute_path,
    get_file_size
)
from src.utils.logger import get_logger


class AutoMangaWorkflow(BrowserController):
    """自动漫画生成工作流控制器"""
    
    def __init__(self, concept: str = "大模型领域的幻觉", session_id: str = None):
        super().__init__()
        self.concept = concept
        self.session_id = session_id
        self.copied_table_content = None
        self.theme_name = None  # 主题名称
        self.theme_dir = None  # 主题文件夹路径
        self.logger = get_logger(session_id)
    
    def build_script_prompt(self) -> str:
        """构建漫画脚本生成提示词"""
        return SCRIPT_PROMPT_TEMPLATE.format(concept=self.concept)
    
    def build_panel_generation_prompt(self, start_panel: int, end_panel: int, is_first_batch: bool = False) -> str:
        """构建宫格生成提示词
        
        Args:
            start_panel: 起始宫格编号（如 1, 5, 9）
            end_panel: 结束宫格编号（如 4, 8, 12）
            is_first_batch: 是否是第一批次
            
        Returns:
            str: 宫格生成提示词
        """
        if is_first_batch:
            return f"\n\n严格参考附件的角色形象，根据漫画脚本的内容，生成P{start_panel}-P{end_panel} 的宫格漫画图片，务必保证角色形象一致，内容于脚本一致，最终输出竖版、宫格漫画图片。"
        else:
            return f"同样的要求，输出 P{start_panel}-P{end_panel} 宫格的竖版、漫画图片"
    
    async def generate_theme_name(self) -> str:
        """基于概念名生成主题名称（类似"强化学习求生记"）
        
        Returns:
            str: 主题名称
        """
        self.logger.debug("开始生成主题名称...")
        
        # 构建主题生成提示词
        theme_prompt = f"""请基于以下AI概念，生成一个简洁、有趣的漫画主题名称（类似"强化学习求生记"这样的格式）。

要求：
1. 主题名称应该简洁有力，朗朗上口
2. 可以结合概念的特点，添加"求生记"、"大冒险"、"奇遇记"等后缀
3. 长度控制在4-8个汉字
4. 只返回主题名称，不要其他解释

概念：{self.concept}

请直接输出主题名称："""
        
        try:
            # 发送主题生成请求
            await self.send_message(theme_prompt)
            
            # 等待响应生成
            if await self.wait_for_response():
                # 获取响应内容
                response_text = await self.page.evaluate("""
                    () => {
                        const responseContainer = document.querySelector('.response-container, .model-response, [data-test-id="model-response"]');
                        if (responseContainer) {
                            return responseContainer.innerText || responseContainer.textContent || '';
                        }
                        return '';
                    }
                """)
                
                # 提取主题名称（取第一行，去除空白字符）
                if response_text:
                    lines = response_text.strip().split('\n')
                    theme_name = lines[0].strip()
                    # 清理可能的标记符号
                    theme_name = theme_name.replace('主题名称：', '').replace('主题：', '').replace('：', '').strip()
                    # 如果包含引号，提取引号内容
                    if '"' in theme_name or '"' in theme_name or '「' in theme_name or '」' in theme_name:
                        import re
                        match = re.search(r'[""「]([^""」]+)[""」]', theme_name)
                        if match:
                            theme_name = match.group(1)
                    
                    # 限制长度
                    if len(theme_name) > 20:
                        theme_name = theme_name[:20]
                    
                    self.logger.debug(f"生成的主题名称: {theme_name}")
                    return theme_name
                else:
                    raise Exception("未获取到响应内容")
            else:
                raise Exception("等待响应超时")
                
        except Exception as e:
            self.logger.warning(f"生成主题名称失败: {e}，使用默认主题名称")
            # 如果生成失败，使用概念名作为默认主题
            default_theme = self.concept.replace('的', '').replace('领域', '').strip()
            if len(default_theme) > 10:
                default_theme = default_theme[:10]
            default_theme = f"{default_theme}漫画"
            return default_theme
    
    def create_theme_directory(self, theme_name: str) -> str:
        """创建主题文件夹，如果已存在则自动递增
        
        Args:
            theme_name: 主题名称
            
        Returns:
            str: 主题文件夹路径
        """
        # 清理主题名称，移除不允许的字符
        import re
        safe_theme_name = re.sub(r'[<>:"/\\|?*]', '', theme_name)
        safe_theme_name = safe_theme_name.strip()
        
        # 构建主题文件夹路径
        base_images_dir = get_absolute_path(DEFAULT_IMAGES_DIR)
        original_theme_dir = os.path.join(base_images_dir, safe_theme_name)
        theme_dir = original_theme_dir
        
        # 检查文件夹是否存在，如果存在则递增名称
        counter = 1
        while os.path.exists(theme_dir):
            self.logger.debug(f"文件夹已存在: {theme_dir}")
            # 尝试添加数字后缀
            new_name = f"{safe_theme_name}{counter}"
            theme_dir = os.path.join(base_images_dir, new_name)
            counter += 1
            
        # 创建文件夹
        Path(theme_dir).mkdir(parents=True, exist_ok=True)
        
        # 如果使用了递增名称，记录日志
        if theme_dir != original_theme_dir:
            self.logger.info(f"原文件夹 {original_theme_dir} 已存在，创建了新文件夹: {theme_dir}")
        else:
            self.logger.debug(f"主题文件夹已创建: {theme_dir}")
        
        return theme_dir
    
    async def send_message(self, query: str):
        """在输入框输入文本并发送
        
        使用 JavaScript 直接设置内容，避免打字机模式导致的换行触发发送问题
        """
        self.logger.debug(f"准备发送消息: {query[:100]}...")
        
        try:
            # 查找输入框
            selector = await find_working_selector(
                self.page, 
                SELECTORS["input_field"], 
                timeout=10000
            )
            
            if not selector:
                raise Exception("无法定位到输入框")
            
            # 获取输入框元素
            input_element = await self.page.query_selector(selector)
            if not input_element:
                raise Exception("无法找到输入框元素")
            
            # 点击输入框获得焦点
            self.logger.debug("点击输入框...")
            await input_element.click()
            await asyncio.sleep(0.3)
            
            # 方法1: 使用 JavaScript 直接设置内容（推荐，避免换行触发发送）
            self.logger.debug("使用 JavaScript 直接设置内容...")
            try:
                # 使用 JavaScript 直接设置 contenteditable 元素的内容
                await self.page.evaluate(
                    """(args) => {
                        const element = document.querySelector(args.selector);
                        if (element) {
                            // 设置新内容（使用 textContent 避免 HTML 转义问题）
                            element.textContent = args.text;
                            
                            // 触发输入事件，确保 Gemini 识别到内容变化
                            const inputEvent = new Event('input', { bubbles: true });
                            element.dispatchEvent(inputEvent);
                            
                            // 触发其他可能需要的事件
                            const changeEvent = new Event('change', { bubbles: true });
                            element.dispatchEvent(changeEvent);
                            
                            // 触发 composition 事件（某些编辑器需要）
                            const compositionStartEvent = new CompositionEvent('compositionstart', { bubbles: true });
                            element.dispatchEvent(compositionStartEvent);
                            
                            const compositionEndEvent = new CompositionEvent('compositionend', { bubbles: true, data: args.text });
                            element.dispatchEvent(compositionEndEvent);
                            
                            // 确保元素获得焦点
                            element.focus();
                        }
                    }""",
                    {"selector": selector, "text": query}
                )
                
                await asyncio.sleep(0.5)  # 等待内容设置完成
                self.logger.debug("✓ 内容已通过 JavaScript 设置")
                
            except Exception as js_error:
                self.logger.warning(f"JavaScript 设置内容失败: {js_error}，尝试备用方案...")
                
                # 方法2: 备用方案 - 使用剪贴板粘贴（避免打字机模式）
                self.logger.debug("使用剪贴板粘贴方式...")
                # 清空输入框
                await self.page.keyboard.press('Meta+a')
                await asyncio.sleep(0.1)
                await self.page.keyboard.press('Control+a')
                await asyncio.sleep(0.1)
                await self.page.keyboard.press('Backspace')
                await asyncio.sleep(0.2)
                
                # 设置剪贴板内容
                pyperclip.copy(query)
                await asyncio.sleep(0.2)
                
                # 粘贴（Mac 使用 Cmd+V，其他系统使用 Ctrl+V）
                await self.page.keyboard.press('Meta+v')
                await asyncio.sleep(0.3)
                await self.page.keyboard.press('Control+v')
                await asyncio.sleep(0.5)  # 等待粘贴完成
                self.logger.debug("✓ 内容已通过剪贴板粘贴")
            
            # 验证内容是否已正确设置（可选）
            try:
                current_content = await self.page.evaluate(f"""
                    (selector) => {{
                        const element = document.querySelector(selector);
                        return element ? element.textContent || element.innerText : '';
                    }}
                """, selector)
                
                if current_content.strip():
                    self.logger.debug(f"✓ 验证：输入框内容长度 {len(current_content)} 字符")
                else:
                    self.logger.warning("输入框内容为空，可能设置失败")
            except:
                pass  # 验证失败不影响主流程
            
            # 点击发送按钮发送消息
            self.logger.debug("查找并点击发送按钮...")
            send_button_selector = await find_working_selector(
                self.page,
                SELECTORS["send_button"],
                timeout=5000
            )
            
            if not send_button_selector:
                # 如果找不到发送按钮，尝试按回车作为备用方案
                self.logger.warning("无法定位发送按钮，尝试按回车发送...")
                await self.page.keyboard.press('Enter')
            else:
                # 获取发送按钮元素
                send_button = await self.page.query_selector(send_button_selector)
                if not send_button:
                    self.logger.warning("无法获取发送按钮元素，尝试按回车发送...")
                    await self.page.keyboard.press('Enter')
                else:
                    # 检查按钮是否可用（不是 disabled）
                    is_disabled = await self.page.evaluate("""
                        (selector) => {
                            const button = document.querySelector(selector);
                            return button ? (button.hasAttribute('aria-disabled') && button.getAttribute('aria-disabled') === 'true') || button.disabled : true;
                        }
                    """, send_button_selector)
                    
                    if is_disabled:
                        self.logger.warning("发送按钮不可用，尝试按回车发送...")
                        await self.page.keyboard.press('Enter')
                    else:
                        self.logger.debug(f"✓ 找到发送按钮: {send_button_selector}")
                        await send_button.click()
                        await asyncio.sleep(0.5)  # 等待发送完成
                        self.logger.debug("✓ 已点击发送按钮")
            
            await asyncio.sleep(0.5)  # 额外等待确保发送完成
            self.logger.debug("消息已发送")
            
        except Exception as e:
            self.logger.error(f"发送消息失败: {e}")
            raise
    
    async def wait_for_response(self) -> bool:
        """等待 Gemini 生成响应完成"""
        self.logger.debug("等待响应生成...")
        
        try:
            # 等待响应开始（检测到响应容器）
            await self.page.wait_for_selector(
                '.response-container, .model-response, [data-test-id="model-response"]',
                timeout=RESPONSE_TIMEOUT
            )
            self.logger.debug("✓ 检测到响应容器")
            
            # 等待响应完成
            response_selector = '.response-container, .model-response, [data-test-id="model-response"]'
            if await wait_for_content_stabilization(
                self.page,
                response_selector,
                max_timeout=RESPONSE_TIMEOUT
            ):
                self.logger.debug("✓ 响应内容已稳定，生成完成")
            else:
                self.logger.warning("等待响应内容稳定超时")
            
            # 额外等待一下，确保表格完全渲染
            await asyncio.sleep(2)
            self.logger.debug("✓ 响应生成完成")
            
            return True
            
        except Exception as e:
            self.logger.error(f"等待响应失败: {e}")
            return False
    
    async def copy_table_content(self) -> str:
        """找到并点击复制表格按钮，获取复制的内容"""
        self.logger.debug("准备复制表格内容...")
        
        try:
            # 尝试多种选择器定位复制按钮
            copy_button = None
            for selector in SELECTORS["copy_button"]:
                try:
                    self.logger.debug(f"尝试定位复制按钮: {selector}")
                    # 等待按钮出现
                    await self.page.wait_for_selector(selector, timeout=5000)
                    copy_button = await self.page.query_selector(selector)
                    if copy_button:
                        self.logger.debug(f"✓ 找到复制按钮: {selector}")
                        break
                except:
                    # 如果直接选择器失败，尝试通过父元素查找
                    try:
                        copy_button = await self.page.query_selector('button:has(mat-icon[fonticon="content_copy"])')
                        if copy_button:
                            self.logger.debug(f"✓ 通过父元素找到复制按钮")
                            break
                    except:
                        continue
            
            if not copy_button:
                # 最后尝试：通过文本内容查找
                self.logger.debug("尝试通过文本内容查找复制按钮...")
                copy_button_element = await self.page.locator('button:has-text("Copy table")').first
                if await copy_button_element.count() > 0:
                    self.logger.debug("✓ 通过文本定位找到复制按钮")
                    copy_button = copy_button_element
                else:
                    raise Exception("无法定位到复制按钮")
            
            # 点击复制按钮
            self.logger.debug("点击复制按钮...")
            await copy_button.click()
            await asyncio.sleep(1)  # 等待复制操作完成
            
            # 从剪贴板获取内容
            self.logger.debug("从剪贴板获取内容...")
            copied_content = pyperclip.paste()
            
            if copied_content:
                self.copied_table_content = copied_content
                self.logger.debug(f"✓ 成功复制表格内容（长度: {len(copied_content)} 字符）")
                self.logger.debug(f"内容预览: {copied_content[:200]}...")
                return copied_content
            else:
                raise Exception("剪贴板内容为空")
            
        except Exception as e:
            self.logger.error(f"复制表格失败: {e}")
            raise
    
    def save_to_file(self, query: str, response: str, filename: str = None) -> str:
        """保存查询和响应到本地 txt 文件"""
        content = f"""
{"=" * 80}
查询内容:
{"=" * 80}
{query}

{"=" * 80}
生成结果:
{"=" * 80}
{response}
"""
        return save_text_to_file(content, filename)
    
    def load_from_session_file(self, session_file: str) -> tuple:
        """从 session 文件读取生成结果（表格内容）和宫格数量
        
        Args:
            session_file: session 文件路径
            
        Returns:
            tuple: (生成结果（表格内容）, 宫格数量)
        """
        filepath = get_absolute_path(session_file)
        
        if not os.path.exists(filepath):
            raise Exception(f"Session 文件不存在: {filepath}")
        
        try:
            content = load_text_from_file(filepath)
            result, panel_count = extract_table_from_session(content)
            return result, panel_count
        except Exception as e:
            self.logger.error(f"读取 session 文件失败: {e}")
            raise
    
    async def click_new_chat(self):
        """点击 New chat 按钮打开新聊天窗口"""
        self.logger.debug("准备打开新聊天窗口...")
        
        try:
            # 查找 New chat 按钮
            new_chat_selector = await find_working_selector(
                self.page,
                SELECTORS["new_chat"],
                timeout=5000
            )
            
            if not new_chat_selector:
                # 尝试通过文本内容查找
                self.logger.debug("尝试通过文本内容查找 New chat 按钮...")
                new_chat_element = await self.page.locator('a:has-text("New chat")').first
                if await new_chat_element.count() > 0:
                    self.logger.debug("✓ 通过文本定位找到 New chat 按钮")
                    await new_chat_element.click()
                else:
                    raise Exception("无法定位到 New chat 按钮")
            else:
                # 获取New chat按钮元素
                new_chat_button = await self.page.query_selector(new_chat_selector)
                if not new_chat_button:
                    raise Exception("无法获取New chat按钮元素")
                
                # 点击 New chat 按钮
                self.logger.debug("点击 New chat 按钮...")
                await new_chat_button.click()
            
            await asyncio.sleep(2)  # 等待新聊天窗口加载
            
            # 等待新页面加载完成
            await self.page.wait_for_load_state('domcontentloaded')
            self.logger.debug("✓ 新聊天窗口已打开")
            
        except Exception as e:
            self.logger.error(f"打开新聊天窗口失败: {e}")
            raise
    
    async def select_create_images_tool(self):
        """点击 Tools 按钮并选择 Create Images 功能"""
        self.logger.debug("准备选择 Create Images 工具...")
        
        try:
            # 查找并点击 Tools 按钮
            tools_selector = await find_working_selector(
                self.page, 
                SELECTORS["tools_button"], 
                timeout=5000
            )
            
            if not tools_selector:
                raise Exception("无法定位到 Tools 按钮")
            
            # 获取Tools按钮元素
            tools_button = await self.page.query_selector(tools_selector)
            if not tools_button:
                raise Exception("无法获取Tools按钮元素")
            
            # 点击 Tools 按钮
            self.logger.debug("点击 Tools 按钮...")
            await tools_button.click()
            await asyncio.sleep(0.5)  # 等待菜单展开
            
            # 查找并点击 Create Images 选项
            create_images_selector = await find_working_selector(
                self.page, 
                SELECTORS["create_images"], 
                timeout=5000
            )
            
            if not create_images_selector:
                # 如果直接选择器失败，尝试通过文本内容查找
                self.logger.debug("尝试通过文本内容查找 Create Images...")
                create_images_element = await self.page.locator('text=Create Images').first
                if await create_images_element.count() > 0:
                    self.logger.debug("✓ 通过文本定位找到 Create Images")
                    await create_images_element.click()
                else:
                    raise Exception("无法定位到 Create Images 选项")
            else:
                # 获取Create Images元素
                create_images_element = await self.page.query_selector(create_images_selector)
                if not create_images_element:
                    raise Exception("无法获取Create Images元素")
                    
                # 点击 Create Images
                self.logger.debug("点击 Create Images...")
                await create_images_element.click()
            
            await asyncio.sleep(0.5)  # 等待工具切换完成
            self.logger.debug("Create Images 工具已选择")
            
        except Exception as e:
            self.logger.error(f"选择 Create Images 工具失败: {e}")
            raise
    
    async def upload_image(self, image_path: str):
        """上传图片到输入框"""
        abs_image_path = get_absolute_path(image_path)
        if not os.path.exists(abs_image_path):
            raise Exception(f"图片文件不存在: {abs_image_path}")
        
        print(f"\n{'='*80}")
        print(f"开始上传图片: {image_path}")
        print(f"{'='*80}\n")
        
        self.logger.info(f"图片绝对路径: {abs_image_path}")
        self.logger.info(f"文件大小: {get_file_size(abs_image_path)} bytes\n")
        
        # 使用综合策略上传图片
        from src.core.image_uploader import ImageUploader
        uploader = ImageUploader(self.page, self.session_id)
        success = await uploader.upload_with_strategies(abs_image_path)
        
        if not success:
            raise Exception("所有上传策略都失败了")
    
    async def send_multimodal_message(self, text: str):
        """发送多模态消息（包含图片和文本）"""
        self.logger.debug(f"准备发送多模态消息: {text[:100]}...")
        
        try:
            # 查找输入框
            selector = await find_working_selector(
                self.page, 
                SELECTORS["input_field"], 
                timeout=10000
            )
            
            if not selector:
                raise Exception("无法定位到输入框")
            
            # 获取输入框元素
            input_element = await self.page.query_selector(selector)
            if not input_element:
                raise Exception("无法找到输入框元素")
            
            # 点击输入框获得焦点
            self.logger.debug("点击输入框...")
            await input_element.click()
            await asyncio.sleep(0.3)
            
            # 使用 JavaScript 追加文本内容（不清空现有内容，可能包含图片）
            self.logger.debug("使用 JavaScript 追加内容...")
            await self.page.evaluate(
                """(args) => {
                    const element = document.querySelector(args.selector);
                    if (element) {
                        // 设置新内容（使用 textContent 避免 HTML 转义问题）
                        element.textContent = args.text;
                        
                        // 触发输入事件，确保 Gemini 识别到内容变化
                        const inputEvent = new Event('input', { bubbles: true });
                        element.dispatchEvent(inputEvent);
                        
                        // 触发其他可能需要的事件
                        const changeEvent = new Event('change', { bubbles: true });
                        element.dispatchEvent(changeEvent);
                        
                        // 触发 composition 事件（某些编辑器需要）
                        const compositionStartEvent = new CompositionEvent('compositionstart', { bubbles: true });
                        element.dispatchEvent(compositionStartEvent);
                        
                        const compositionEndEvent = new CompositionEvent('compositionend', { bubbles: true, data: args.text });
                        element.dispatchEvent(compositionEndEvent);
                        
                        // 确保元素获得焦点
                        element.focus();
                    }
                }""",
                {"selector": selector, "text": text}
            )
            
            await asyncio.sleep(0.5)  # 等待内容设置完成
            self.logger.debug("✓ 内容已通过 JavaScript 设置")
            
            # 点击发送按钮发送消息
            self.logger.debug("查找并点击发送按钮...")
            send_button_selector = await find_working_selector(
                self.page,
                SELECTORS["send_button"],
                timeout=5000
            )
            
            if not send_button_selector:
                # 如果找不到发送按钮，尝试按回车作为备用方案
                self.logger.warning("无法定位发送按钮，尝试按回车发送...")
                await self.page.keyboard.press('Enter')
            else:
                # 获取发送按钮元素
                send_button = await self.page.query_selector(send_button_selector)
                if not send_button:
                    self.logger.warning("无法获取发送按钮元素，尝试按回车发送...")
                    await self.page.keyboard.press('Enter')
                else:
                    # 检查按钮是否可用（不是 disabled）
                    is_disabled = await self.page.evaluate("""
                        (selector) => {
                            const button = document.querySelector(selector);
                            return button ? (button.hasAttribute('aria-disabled') && button.getAttribute('aria-disabled') === 'true') || button.disabled : true;
                        }
                    """, send_button_selector)
                    
                    if is_disabled:
                        self.logger.warning("发送按钮不可用，尝试按回车发送...")
                        await self.page.keyboard.press('Enter')
                    else:
                        self.logger.debug(f"✓ 找到发送按钮: {send_button_selector}")
                        await send_button.click()
                        await asyncio.sleep(0.5)  # 等待发送完成
                        self.logger.debug("✓ 已点击发送按钮")
            
            await asyncio.sleep(0.5)  # 额外等待确保发送完成
            self.logger.debug("多模态消息已发送")
            
        except Exception as e:
            self.logger.error(f"发送多模态消息失败: {e}")
            raise
    
    async def wait_for_images_generated(self, initial_image_count: int = 0, saved_image_urls: set = None) -> tuple:
        """等待图片生成完成
        
        Args:
            initial_image_count: 发送消息前的图片数量，用于检测新生成的图片
            saved_image_urls: 已保存的图片URL集合，用于排除已保存的图片
            
        Returns:
            tuple: (是否成功, 新生成的图片URL列表)
        """
        if saved_image_urls is None:
            saved_image_urls = set()
        
        self.logger.debug("等待图片生成...")
        
        try:
            # 导入ImageSaver用于URL处理
            from src.core.image_saver import ImageSaver
            saver = ImageSaver(self.page, self.session_id)
            
            # 等待新的响应容器出现（通过检测响应容器的数量变化）
            container_selector = '.attachment-container.generated-images'
            
            # 先等待一小段时间，确保消息已发送
            await asyncio.sleep(1)
            
            # 记录开始时间
            start_time = time.time()
            timeout_seconds = RESPONSE_TIMEOUT / 1000.0
            
            # 等待新的图片容器出现（通过检测容器数量增加）
            self.logger.debug(f"当前图片数量: {initial_image_count}，已保存图片数量: {len(saved_image_urls)}，等待新图片生成...")
            
            new_images_detected = False
            last_container_count = 0
            containers = []
            new_image_urls = []
            
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout_seconds:
                    self.logger.warning("等待新图片生成超时")
                    return (False, [])
                
                try:
                    # 获取所有图片容器
                    containers = await self.page.query_selector_all(container_selector)
                    current_container_count = len(containers)
                    
                    # 获取所有图片的URL
                    all_images = await self.page.query_selector_all(f'{container_selector} img[src]')
                    current_image_count = len(all_images)
                    
                    # 收集当前所有图片的URL（使用处理后的URL，确保格式一致）
                    current_image_urls = set()
                    for img in all_images:
                        try:
                            img_src = await img.get_attribute('src')
                            if img_src:
                                # 处理URL，确保格式一致
                                processed_url = saver._process_image_url(img_src)
                                current_image_urls.add(processed_url)
                        except:
                            continue
                    
                    # 找出新生成的图片URL（不在已保存列表中的）
                    new_urls = current_image_urls - saved_image_urls
                    
                    # 如果容器数量增加了，或者有新图片URL，说明有新的响应
                    if current_container_count > last_container_count or len(new_urls) > 0:
                        if current_container_count > last_container_count:
                            self.logger.debug(f"✓ 检测到新的图片容器（容器数量: {last_container_count} -> {current_container_count}）")
                            last_container_count = current_container_count
                        
                        if len(new_urls) > 0:
                            self.logger.debug(f"✓ 检测到 {len(new_urls)} 张新图片（不在已保存列表中）")
                            new_image_urls = list(new_urls)
                            new_images_detected = True
                            
                            # 检查最新容器中的图片是否已加载
                            if containers:
                                latest_container = containers[-1]
                                images_in_latest = await latest_container.query_selector_all('img[src]')
                                if len(images_in_latest) > 0:
                                    # 验证这些图片是否是新图片
                                    latest_urls = set()
                                    for img in images_in_latest:
                                        try:
                                            img_src = await img.get_attribute('src')
                                            if img_src:
                                                # 处理URL，确保格式一致
                                                processed_url = saver._process_image_url(img_src)
                                                if processed_url in new_urls:
                                                    latest_urls.add(processed_url)
                                        except:
                                            continue
                                    
                                    if len(latest_urls) > 0:
                                        self.logger.debug(f"✓ 最新容器中有 {len(latest_urls)} 张新图片")
                                        break
                    
                    # 短暂等待后继续检查
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    self.logger.debug(f"检查图片状态时出错: {e}，继续等待...")
                    await asyncio.sleep(0.5)
            
            if not new_images_detected or len(new_image_urls) == 0:
                self.logger.warning("未检测到新图片")
                return (False, [])
            
            # 等待新图片加载完成
            self.logger.debug("等待新图片加载完成...")
            from src.utils.browser_utils import wait_for_images_loading
            
            # 等待最新容器中的图片加载完成
            if containers and len(containers) > 0:
                # 使用最后一个容器（最新的响应）
                try:
                    # 通过JavaScript获取最后一个容器的选择器
                    latest_container_index = len(containers) - 1
                    latest_container_selector = f'{container_selector}:nth-of-type({latest_container_index + 1})'
                except:
                    latest_container_selector = container_selector
            else:
                latest_container_selector = container_selector
            
            if await wait_for_images_loading(
                self.page,
                latest_container_selector,
                max_timeout=RESPONSE_TIMEOUT
            ):
                self.logger.debug(f"✓ 新图片加载完成，共 {len(new_image_urls)} 张新图片")
                return (True, new_image_urls)
            else:
                self.logger.warning("新图片加载超时")
                return (False, [])
                
        except Exception as e:
            self.logger.error(f"等待图片生成失败: {e}")
            return (False, [])
    
    async def wait_for_all_batches_completed(self, total_batches: int, saved_image_urls: set, max_wait_time: int = 300):
        """等待所有批次生成完成
        
        Args:
            total_batches: 总批次数
            saved_image_urls: 已保存的图片URL集合（用于排除已存在的图片）
            max_wait_time: 最大等待时间（秒）
        """
        self.logger.debug(f"等待所有 {total_batches} 个批次生成完成...")
        
        container_selector = '.attachment-container.generated-images'
        start_time = time.time()
        wait_count = 0  # 等待次数计数器
        base_wait_interval = 3  # 基础等待间隔（秒）
        refresh_interval = 5  # 每5次等待后刷新一次
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_time:
                self.logger.warning(f"等待所有批次完成超时（{max_wait_time}秒）")
                break
            
            try:
                # 每隔一定次数后刷新页面
                if wait_count > 0 and wait_count % refresh_interval == 0:
                    self.logger.debug(f"已等待 {wait_count} 次，执行页面刷新...")
                    try:
                        await self.page.reload(wait_until='domcontentloaded')
                        self.logger.debug("页面刷新完成，等待页面稳定...")
                        await asyncio.sleep(2)  # 等待页面稳定
                    except Exception as refresh_error:
                        self.logger.warning(f"页面刷新失败: {refresh_error}，继续检查...")
                
                # 获取所有图片容器
                containers = await self.page.query_selector_all(container_selector)
                current_container_count = len(containers)
                
                # 获取所有图片的URL
                from src.core.image_saver import ImageSaver
                saver = ImageSaver(self.page, self.session_id)
                all_images = await self.page.query_selector_all(f'{container_selector} img[src]')
                
                # 收集所有图片URL（排除已存在的）
                current_image_urls = set()
                for img in all_images:
                    try:
                        img_src = await img.get_attribute('src')
                        if img_src:
                            processed_url = saver._process_image_url(img_src)
                            if processed_url not in saved_image_urls:
                                current_image_urls.add(processed_url)
                    except:
                        continue
                
                # 检查是否所有批次都已完成（容器数量应该等于批次数）
                if current_container_count >= total_batches:
                    self.logger.debug(f"✓ 检测到 {current_container_count} 个图片容器（期望 {total_batches} 个）")
                    
                    # 等待所有图片加载完成
                    from src.utils.browser_utils import wait_for_images_loading
                    if await wait_for_images_loading(
                        self.page,
                        container_selector,
                        max_timeout=RESPONSE_TIMEOUT
                    ):
                        self.logger.debug(f"✓ 所有批次图片已生成并加载完成")
                        return
                
                # 计算动态等待间隔（随着等待次数增加而增加，但不超过10秒）
                wait_interval = min(base_wait_interval + (wait_count // refresh_interval), 10)
                self.logger.debug(f"当前容器数量: {current_container_count}/{total_batches}，继续等待... (等待间隔: {wait_interval}秒)")
                await asyncio.sleep(wait_interval)
                wait_count += 1
                
            except Exception as e:
                # 计算动态等待间隔
                wait_interval = min(base_wait_interval + (wait_count // refresh_interval), 10)
                self.logger.debug(f"检查批次状态时出错: {e}，继续等待... (等待间隔: {wait_interval}秒)")
                await asyncio.sleep(wait_interval)
                wait_count += 1
    
    async def save_all_images_sequentially(self, save_dir: str, total_batches: int) -> List[str]:
        """按顺序保存所有生成的图片容器
        
        Args:
            save_dir: 保存目录
            total_batches: 总批次数（用于验证容器数量）
            
        Returns:
            List[str]: 保存的文件路径列表（按顺序）
        """
        from src.core.image_saver import ImageSaver
        saver = ImageSaver(self.page, self.session_id)
        return await saver.save_all_images_sequentially(save_dir, total_batches)
    
    async def save_generated_images(self, save_dir: str = DEFAULT_IMAGES_DIR, target_image_urls: List[str] = None) -> List[str]:
        """保存生成的图片到本地文件夹
        
        Args:
            save_dir: 保存目录
            target_image_urls: 目标图片URL列表，如果提供则只保存这些URL对应的图片
            
        Returns:
            List[str]: 保存的文件路径列表
        """
        from src.core.image_saver import ImageSaver
        saver = ImageSaver(self.page, self.session_id)
        if target_image_urls:
            # 只保存指定URL的图片
            return await saver.save_images_by_urls(save_dir, target_image_urls)
        else:
            # 保存所有图片（兼容旧逻辑）
            return await saver.save_all_images(save_dir)
    
    async def generate_cover_image(self, cover_image_path: str = DEFAULT_COVER_IMAGE_PATH, save_dir: str = None) -> str:
        """生成封面图片
        
        Args:
            cover_image_path: 封面模板图片路径
            save_dir: 保存目录，如果为None则使用主题文件夹
            
        Returns:
            str: 保存的封面图片路径，如果失败则返回None
        """
        if not self.theme_name:
            self.logger.warning("主题名称未设置，无法生成封面图片")
            return None
        
        print("\n" + "="*80)
        print("第四阶段：生成封面图片")
        print("="*80)
        
        try:
            # 先点击 New Chat，在新窗口进行生成
            print("\n" + "-"*80)
            print("步骤1: 打开新聊天窗口")
            print("-"*80)
            await self.click_new_chat()
            
            # 选择 Create Images 工具
            print("\n" + "-"*80)
            print("步骤2: 选择 Create Images 工具")
            print("-"*80)
            await self.select_create_images_tool()
            
            # 使用主题文件夹作为保存路径
            if save_dir is None:
                save_dir = self.theme_dir if self.theme_dir else DEFAULT_IMAGES_DIR
            
            # 构建封面生成提示词
            cover_query = f"根据生成的{self.theme_name}，总结一个主题，替换掉图中\"Vibe Coding 赛博朋克\"这个字符串，输出最终的图片。只能更改\"Vibe Coding 赛博朋克\"这个文字，其他的保持不变。去除右下角的水印。"
            
            self.logger.info(f"封面图片模板: {cover_image_path}")
            self.logger.info(f"主题名称: {self.theme_name}")
            self.logger.info(f"保存目录: {save_dir}")
            self.logger.info(f"封面生成提示词: {cover_query}")
            
            # 上传封面模板图片
            print("\n" + "-"*80)
            print("步骤3: 上传封面模板图片")
            print("-"*80)
            await self.upload_image(cover_image_path)
            await asyncio.sleep(1)  # 等待图片上传完成
            
            # 发送多模态消息（包含图片和文本）
            self.logger.debug("发送封面生成请求...")
            await self.send_multimodal_message(cover_query)
            await asyncio.sleep(2)  # 发送消息后滚动
            self.logger.debug("发送消息后滚动到底部，确保新生成的响应被渲染")
            # ==================== 新增修复代码 ====================
            # 发送消息后，强制页面滚动到底部，确保新生成的响应被渲染
            try:
                await self.page.keyboard.press('End')
            except:
                pass
            # ====================================================
            
            # 等待图片生成完成
            self.logger.debug("等待封面图片生成...")
            container_selector = '.attachment-container.generated-images'
            
            # 记录发送前的图片数量和URL
            initial_image_urls = set()
            try:
                existing_images = await self.page.query_selector_all(f'{container_selector} img[src]')
                initial_image_count = len(existing_images)
                self.logger.debug(f"发送前图片数量: {initial_image_count}")
                
                # 记录发送前的所有图片URL
                from src.core.image_saver import ImageSaver
                saver = ImageSaver(self.page, self.session_id)
                for img in existing_images:
                    try:
                        img_src = await img.get_attribute('src')
                        if img_src:
                            processed_url = saver._process_image_url(img_src)
                            initial_image_urls.add(processed_url)
                    except:
                        continue
            except:
                initial_image_count = 0
            
            # 等待新图片生成（使用更长的超时时间）
            self.logger.debug("等待封面图片生成（最多等待 180 秒）...")
            success, new_image_urls = await self.wait_for_images_generated(
                initial_image_count=initial_image_count,
                saved_image_urls=initial_image_urls  # 排除发送前已存在的图片
            )
            
            # 即使等待超时，也尝试保存已检测到的图片
            if len(new_image_urls) > 0:
                self.logger.debug(f"✓ 检测到 {len(new_image_urls)} 张新图片URL，尝试保存...")
                
                # 发送"下一步"消息，让页面自动滚动，渲染出最后一张图片
                try:
                    self.logger.debug("发送'下一步'消息，触发页面滚动...")
                    await self.send_message("下一步")
                    await asyncio.sleep(3)  # 等待3秒，让页面自动滚动并渲染图片
                    self.logger.debug("✓ 页面滚动完成")
                except Exception as e:
                    self.logger.warning(f"发送'下一步'消息失败: {e}，继续执行...")
                
                # 保存封面图片（即使加载超时也尝试保存）
                self.logger.debug("保存封面图片...")
                saved_files = await self.save_generated_images(save_dir, new_image_urls)
                
                if saved_files and len(saved_files) > 0:
                    # 封面图片应该只有一张，取第一张
                    cover_file = saved_files[0]
                    
                    # 重命名为 "封面.png"
                    cover_path = Path(cover_file)
                    cover_dir = cover_path.parent
                    new_cover_path = cover_dir / "封面.png"
                    
                    # 如果目标文件已存在，先删除
                    if new_cover_path.exists():
                        new_cover_path.unlink()
                    
                    # 重命名文件
                    cover_path.rename(new_cover_path)
                    self.logger.debug(f"✓ 封面图片已保存并重命名: {new_cover_path}")
                    return str(new_cover_path)
                else:
                    # 如果通过URL保存失败，尝试使用备用方法：直接保存最新容器中的图片
                    self.logger.warning("通过URL保存失败，尝试备用方法：直接保存最新容器中的图片...")
                    try:
                        containers = await self.page.query_selector_all(container_selector)
                        if containers:
                            latest_container = containers[-1]
                            # 使用 save_all_images_sequentially 的备用逻辑
                            from src.core.image_saver import ImageSaver
                            saver = ImageSaver(self.page, self.session_id)
                            # 尝试直接保存最新容器中的图片
                            saved_files = await saver.save_all_images(save_dir)
                            if saved_files:
                                # 取最后一张（应该是封面图片）
                                cover_file = saved_files[-1]
                                
                                # 重命名为 "封面.png"
                                cover_path = Path(cover_file)
                                cover_dir = cover_path.parent
                                new_cover_path = cover_dir / "封面.png"
                                
                                # 如果目标文件已存在，先删除
                                if new_cover_path.exists():
                                    new_cover_path.unlink()
                                
                                # 重命名文件
                                cover_path.rename(new_cover_path)
                                self.logger.debug(f"✓ 封面图片已保存并重命名（备用方法）: {new_cover_path}")
                                return str(new_cover_path)
                    except Exception as backup_error:
                        self.logger.warning(f"备用保存方法也失败: {backup_error}")
                    
                    self.logger.warning("封面图片生成成功但保存失败")
                    return None
            else:
                self.logger.warning("未检测到新生成的封面图片")
                return None
                
        except Exception as e:
            self.logger.error(f"生成封面图片失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def run(
        self, 
        concept: str = None, 
        demo_image_path: str = DEFAULT_IMAGE_PATH, 
        images_dir: str = DEFAULT_IMAGES_DIR,
        skip_script_generation: bool = False, 
        session_file: str = None,
        skip_to_cover: bool = False,
        theme_name: str = None
    ):
        """运行完整工作流
        
        Args:
            concept: AI 概念（如"大模型领域的幻觉"），如果不提供则使用初始化时的值
            demo_image_path: demo.png 图片路径，默认为当前目录下的 demo.png
            images_dir: 图片保存目录，默认为 "assets/images"
            skip_script_generation: 是否跳过脚本生成步骤，直接从 session 文件读取
            session_file: 当 skip_script_generation=True 时，指定要读取的 session 文件路径
            skip_to_cover: 是否跳过脚本和漫画生成，直接测试封面生成
            theme_name: 当 skip_to_cover=True 时，指定主题名称（用于封面生成）
        """
        if concept:
            self.concept = concept
        
        try:
            # 步骤1: 连接浏览器并打开 Gemini
            await self.connect_to_browser()
            await self.open_gemini()
            
            # 如果 skip_to_cover=True，直接进入封面生成
            if skip_to_cover:
                print("\n" + "="*80)
                print("跳过脚本和漫画生成，直接测试封面生成")
                print("="*80)
                
                # 设置主题名称（直接使用概念或提供的主题名称）
                if theme_name:
                    self.theme_name = theme_name
                elif self.concept:
                    # 直接使用概念名作为主题名称
                    self.theme_name = self.concept
                else:
                    self.theme_name = "测试主题漫画"
                
                # 创建主题文件夹
                self.theme_dir = self.create_theme_directory(self.theme_name)
                self.logger.info(f"✓ 主题名称: {self.theme_name}")
                self.logger.info(f"✓ 主题文件夹: {self.theme_dir}")
                
                # 直接生成封面图片（generate_cover_image 内部会处理 New Chat 和 Create Images 工具选择）
                save_dir = self.theme_dir if self.theme_dir else images_dir
                cover_file = await self.generate_cover_image(
                    cover_image_path=DEFAULT_COVER_IMAGE_PATH,
                    save_dir=save_dir
                )
                
                if cover_file:
                    self.logger.info(f"✓ 封面图片已生成并保存: {cover_file}")
                else:
                    self.logger.warning("封面图片生成失败")
                
                print("\n" + "="*80)
                print("✓ 封面生成测试完成！")
                print("="*80)
                return
            
            # 步骤2: 生成脚本或从文件读取
            panel_count = 0  # 宫格总数
            if skip_script_generation:
                # 跳过脚本生成，直接从 session 文件读取
                print("\n" + "="*80)
                print("步骤1: 从 session 文件读取脚本内容（跳过生成）")
                print("="*80)
                if not session_file:
                    raise Exception("skip_script_generation=True 时必须提供 session_file 参数")
                copied_content, panel_count = self.load_from_session_file(session_file)
                self.logger.debug(f"✓ 已从 session 文件读取内容，宫格数量: {panel_count}")
                
                # 如果跳过脚本生成，直接使用概念名作为主题
                print("\n" + "="*80)
                print("步骤2: 设置主题名称并创建主题文件夹")
                print("="*80)
                # 直接使用概念名作为主题名称
                self.theme_name = self.concept
                self.theme_dir = self.create_theme_directory(self.theme_name)
                self.logger.info(f"✓ 主题名称: {self.theme_name}")
                self.logger.info(f"✓ 主题文件夹: {self.theme_dir}")
            else:
                # 正常流程：生成脚本
                print("\n" + "="*80)
                print("步骤1: 生成漫画脚本")
                print("="*80)
                script_prompt = self.build_script_prompt()
                await self.send_message(script_prompt)
                
                # 步骤3: 等待响应生成
                print("\n" + "="*80)
                print("步骤2: 等待脚本生成")
                print("="*80)
                if await self.wait_for_response():
                    self.logger.debug("✓ 脚本生成完成")
                else:
                    self.logger.warning("脚本生成可能未完成，继续尝试复制")
                await asyncio.sleep(10)  # 避免错误检查按钮
                
                # 步骤4: 复制表格内容
                print("\n" + "="*80)
                print("步骤3: 复制表格内容")
                print("="*80)
                copied_content = await self.copy_table_content()
                
                # 计算宫格数量
                from src.utils.file_utils import count_panels_from_table
                panel_count = count_panels_from_table(copied_content)
                self.logger.debug(f"✓ 检测到宫格数量: {panel_count}")
                
                # 步骤5: 保存到文件
                print("\n" + "="*80)
                print("步骤4: 保存结果到文件")
                print("="*80)
                session_file = self.save_to_file(script_prompt, copied_content)
                
                # 步骤5.5: 生成主题名称并创建主题文件夹
                print("\n" + "="*80)
                print("步骤5: 生成主题名称并创建主题文件夹")
                print("="*80)
                # self.theme_name = await self.generate_theme_name()  # 暂时忽略，直接使用概念名
                self.theme_name = self.concept
                self.theme_dir = self.create_theme_directory(self.theme_name)
                self.logger.info(f"✓ 主题名称: {self.theme_name}")
                self.logger.info(f"✓ 主题文件夹: {self.theme_dir}")
            
            # 步骤6: 打开新聊天窗口
            print("\n" + "="*80)
            print("步骤5: 打开新聊天窗口")
            print("="*80)
            await self.click_new_chat()
            
            # 步骤7: 选择 Create Images 工具
            step_num = 6 if skip_script_generation else 6
            print("\n" + "="*80)
            print(f"步骤{step_num}: 选择 Create Images 工具")
            print("="*80)
            await self.select_create_images_tool()
            
            # 步骤8: 上传 demo.png 图片（只在第一次上传）
            step_num = 7 if skip_script_generation else 7
            print("\n" + "="*80)
            print(f"步骤{step_num}: 上传 demo.png 图片")
            print("="*80)
            await self.upload_image(demo_image_path)
            await asyncio.sleep(1)  # 等待图片上传完成
            
            # 步骤9-10: 循环生成宫格图片（每4个一组）
            print("\n" + "="*80)
            print(f"步骤{step_num + 1}: 开始循环生成宫格图片（总共 {panel_count} 个宫格）")
            print("="*80)
            
            # 计算需要生成的批次数量（每4个一组）
            total_batches = (panel_count + 3) // 4  # 向上取整
            self.logger.info(f"需要生成 {total_batches} 批次，每批次 4 个宫格")
            
            # 在循环开始前，收集所有现有图片的URL（这些是上传的demo图片等，不应该被保存）
            saved_image_urls = set()
            container_selector = '.attachment-container.generated-images'
            try:
                from src.core.image_saver import ImageSaver
                saver = ImageSaver(self.page, self.session_id)
                existing_images = await self.page.query_selector_all(f'{container_selector} img[src]')
                for img in existing_images:
                    try:
                        img_src = await img.get_attribute('src')
                        if img_src:
                            processed_url = saver._process_image_url(img_src)
                            saved_image_urls.add(processed_url)
                    except:
                        continue
                self.logger.debug(f"循环开始前，已收集 {len(saved_image_urls)} 个现有图片URL（这些图片不会被保存）")
            except:
                self.logger.debug("无法收集现有图片URL，使用空集合")
            
            # 第一阶段：发送所有批次的生成请求，只等待生成完成，不立即保存
            print("\n" + "-"*80)
            print("第一阶段：发送所有批次的生成请求")
            print("-"*80)
            
            for batch_index in range(total_batches):
                # 计算当前批次的宫格范围
                start_panel = batch_index * 4 + 1
                end_panel = min((batch_index + 1) * 4, panel_count)
                
                print("\n" + "-"*80)
                print(f"批次 {batch_index + 1}/{total_batches}: 生成 P{start_panel}-P{end_panel} 宫格")
                print("-"*80)
                
                # 构建提示词
                if batch_index == 0:
                    # 第一次：使用表格内容 + 提示词
                    panel_prompt = self.build_panel_generation_prompt(start_panel, end_panel, is_first_batch=True)
                    full_message = copied_content + panel_prompt
                else:
                    # 后续批次：只发送提示词（表格内容和图片已经在第一次发送了，保留在对话历史中）
                    panel_prompt = self.build_panel_generation_prompt(start_panel, end_panel, is_first_batch=False)
                    full_message = panel_prompt
                
                # 发送消息前，记录当前图片数量（用于检测新生成的图片）
                try:
                    existing_images = await self.page.query_selector_all(f'{container_selector} img[src]')
                    initial_image_count = len(existing_images)
                    self.logger.debug(f"发送消息前，当前图片数量: {initial_image_count}")
                except:
                    initial_image_count = 0
                    self.logger.debug("无法获取当前图片数量，使用默认值 0")
                
                # 发送消息（第一次使用多模态，后续批次只发送文本）
                self.logger.debug(f"发送生成请求: P{start_panel}-P{end_panel}")
                if batch_index == 0:
                    # 第一次：需要包含图片和表格，使用多模态消息
                    await self.send_multimodal_message(full_message)
                else:
                    # 后续批次：只发送文本提示词（图片和表格已在对话历史中）
                    await self.send_message(full_message)
                
                # 等待当前批次的图片生成完成（不保存）
                t1 = time.time()
                self.logger.debug(f"等待批次 {batch_index + 1} 图片生成...")
                success, new_image_urls = await self.wait_for_images_generated(
                    initial_image_count=initial_image_count,
                    saved_image_urls=saved_image_urls
                )
                
                if success and len(new_image_urls) > 0:
                    # 将新生成的图片URL加入已保存列表（用于后续批次检测）
                    saved_image_urls.update(new_image_urls)
                    self.logger.debug(f"✓ 批次 {batch_index + 1} 图片生成完成，检测到 {len(new_image_urls)} 张新图片")
                elif success:
                    self.logger.warning(f"批次 {batch_index + 1} 图片生成成功，但未检测到新图片URL")
                else:
                    self.logger.warning(f"批次 {batch_index + 1} (P{start_panel}-P{end_panel}) 图片生成超时或失败")
                t2 = time.time()
                print(f"批次 {batch_index + 1} 图片生成完成，耗时: {t2 - t1} 秒")
                if t2 - t1 > 20:
                    sleep_time = 2
                else:
                    sleep_time = 20
                # 如果不是最后一批，等待一下再继续
                if batch_index < total_batches - 1:
                    self.logger.debug(f"等待 {sleep_time} 秒后继续下一批次...")
                    await asyncio.sleep(sleep_time)
            
            # 发送"下一步"消息，让页面自动滚动，渲染出最后一张图片
            try:
                self.logger.debug("发送'下一步'消息，触发页面滚动...")
                await self.send_message("下一步")
                await asyncio.sleep(3)  # 等待3秒，让页面自动滚动并渲染图片
                self.logger.debug("✓ 页面滚动完成")
                
                # 刷新页面
                self.logger.debug("刷新页面...")
                await self.page.reload()
                await self.page.wait_for_load_state('domcontentloaded')
                self.logger.debug("✓ 页面刷新完成")
            except Exception as e:
                self.logger.warning(f"发送'下一步'消息或刷新页面失败: {e}，继续执行...")

            # 第二阶段：等待所有批次生成完成
            print("\n" + "="*80)
            print("第二阶段：等待所有批次生成完成")
            print("="*80)
            await self.wait_for_all_batches_completed(total_batches, saved_image_urls)
            
            # 第三阶段：统一检测所有图片容器，按顺序下载保存
            print("\n" + "="*80)
            print("第三阶段：统一检测并顺序保存所有图片")
            print("="*80)
            
            # 使用主题文件夹作为保存路径（如果已生成）
            save_dir = self.theme_dir if self.theme_dir else images_dir
            if self.theme_dir:
                self.logger.info(f"图片将保存到主题文件夹: {save_dir}")
            else:
                self.logger.info(f"图片将保存到默认文件夹: {save_dir}")
            
            saved_files = await self.save_all_images_sequentially(save_dir, total_batches)
            
            if saved_files:
                self.logger.debug(f"✓ 成功保存 {len(saved_files)} 张图片到 {save_dir}")
                for idx, file in enumerate(saved_files, 1):
                    print(f"  {idx}. {file}")
            else:
                self.logger.warning("未保存任何图片")
            
            # 第四阶段：生成封面图片
            if self.theme_name and self.theme_dir:
                cover_file = await self.generate_cover_image(
                    cover_image_path=DEFAULT_COVER_IMAGE_PATH,
                    save_dir=save_dir
                )
                if cover_file:
                    self.logger.info(f"✓ 封面图片已生成并保存: {cover_file}")
                else:
                    self.logger.warning("封面图片生成失败，但工作流继续完成")
            else:
                self.logger.warning("主题名称或主题文件夹未设置，跳过封面图片生成")
            
            print("\n" + "="*80)
            print(f"✓ 工作流完成！共生成 {total_batches} 批次，{panel_count} 个宫格")
            print("="*80)
            
        except Exception as e:
            self.logger.error(f"工作流执行失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close()


async def main():
    """主函数"""
    import sys
    
    # 检查是否提供了 session 文件参数
    skip_script = False
    session_file = None
    
    if len(sys.argv) > 1:
        # 如果提供了参数，假设是 session 文件路径
        session_file = sys.argv[1]
        skip_script = True
        print(f"将从 session 文件读取内容: {session_file}")
        print("跳过脚本生成步骤")
    else:
        # 正常流程：生成脚本
        concept = "大模型领域的幻觉"
        print(f"将生成新脚本，概念: {concept}")
    
    # 创建控制器并运行工作流
    if skip_script:
        workflow = AutoMangaWorkflow()  # 不需要 concept，因为跳过生成
        await workflow.run(skip_script_generation=True, session_file=session_file)
    else:
        concept = "大模型领域的幻觉"
        workflow = AutoMangaWorkflow(concept=concept)
        await workflow.run()


if __name__ == '__main__':
    asyncio.run(main())