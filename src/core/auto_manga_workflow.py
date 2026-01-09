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


class AutoMangaWorkflow(BrowserController):
    """自动漫画生成工作流控制器"""
    
    def __init__(self, concept: str = "大模型领域的幻觉"):
        super().__init__()
        self.concept = concept
        self.copied_table_content = None
    
    def build_script_prompt(self) -> str:
        """构建漫画脚本生成提示词"""
        return SCRIPT_PROMPT_TEMPLATE.format(concept=self.concept)
    
    async def send_message(self, query: str):
        """在输入框输入文本并发送
        
        使用 JavaScript 直接设置内容，避免打字机模式导致的换行触发发送问题
        """
        print(f"[DEBUG] 准备发送消息: {query[:100]}...")
        
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
            print("[DEBUG] 点击输入框...")
            await input_element.click()
            await asyncio.sleep(0.3)
            
            # 方法1: 使用 JavaScript 直接设置内容（推荐，避免换行触发发送）
            print("[DEBUG] 使用 JavaScript 直接设置内容...")
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
                print("[DEBUG] ✓ 内容已通过 JavaScript 设置")
                
            except Exception as js_error:
                print(f"[WARNING] JavaScript 设置内容失败: {js_error}，尝试备用方案...")
                
                # 方法2: 备用方案 - 使用剪贴板粘贴（避免打字机模式）
                print("[DEBUG] 使用剪贴板粘贴方式...")
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
                print("[DEBUG] ✓ 内容已通过剪贴板粘贴")
            
            # 验证内容是否已正确设置（可选）
            try:
                current_content = await self.page.evaluate(f"""
                    (selector) => {{
                        const element = document.querySelector(selector);
                        return element ? element.textContent || element.innerText : '';
                    }}
                """, selector)
                
                if current_content.strip():
                    print(f"[DEBUG] ✓ 验证：输入框内容长度 {len(current_content)} 字符")
                else:
                    print("[WARNING] 输入框内容为空，可能设置失败")
            except:
                pass  # 验证失败不影响主流程
            
            # 点击发送按钮发送消息
            print("[DEBUG] 查找并点击发送按钮...")
            send_button_selector = await find_working_selector(
                self.page,
                SELECTORS["send_button"],
                timeout=5000
            )
            
            if not send_button_selector:
                # 如果找不到发送按钮，尝试按回车作为备用方案
                print("[WARNING] 无法定位发送按钮，尝试按回车发送...")
                await self.page.keyboard.press('Enter')
            else:
                # 获取发送按钮元素
                send_button = await self.page.query_selector(send_button_selector)
                if not send_button:
                    print("[WARNING] 无法获取发送按钮元素，尝试按回车发送...")
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
                        print("[WARNING] 发送按钮不可用，尝试按回车发送...")
                        await self.page.keyboard.press('Enter')
                    else:
                        print(f"[DEBUG] ✓ 找到发送按钮: {send_button_selector}")
                        await send_button.click()
                        await asyncio.sleep(0.5)  # 等待发送完成
                        print("[DEBUG] ✓ 已点击发送按钮")
            
            await asyncio.sleep(0.5)  # 额外等待确保发送完成
            print("[DEBUG] 消息已发送")
            
        except Exception as e:
            print(f"[ERROR] 发送消息失败: {e}")
            raise
    
    async def wait_for_response(self) -> bool:
        """等待 Gemini 生成响应完成"""
        print("[DEBUG] 等待响应生成...")
        
        try:
            # 等待响应开始（检测到响应容器）
            await self.page.wait_for_selector(
                '.response-container, .model-response, [data-test-id="model-response"]',
                timeout=RESPONSE_TIMEOUT
            )
            print("[DEBUG] ✓ 检测到响应容器")
            
            # 等待响应完成
            response_selector = '.response-container, .model-response, [data-test-id="model-response"]'
            if await wait_for_content_stabilization(
                self.page,
                response_selector,
                max_timeout=RESPONSE_TIMEOUT
            ):
                print("[DEBUG] ✓ 响应内容已稳定，生成完成")
            else:
                print("[WARNING] 等待响应内容稳定超时")
            
            # 额外等待一下，确保表格完全渲染
            await asyncio.sleep(2)
            print("[DEBUG] ✓ 响应生成完成")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] 等待响应失败: {e}")
            return False
    
    async def copy_table_content(self) -> str:
        """找到并点击复制表格按钮，获取复制的内容"""
        print("[DEBUG] 准备复制表格内容...")
        
        try:
            # 尝试多种选择器定位复制按钮
            copy_button = None
            for selector in SELECTORS["copy_button"]:
                try:
                    print(f"[DEBUG] 尝试定位复制按钮: {selector}")
                    # 等待按钮出现
                    await self.page.wait_for_selector(selector, timeout=5000)
                    copy_button = await self.page.query_selector(selector)
                    if copy_button:
                        print(f"[DEBUG] ✓ 找到复制按钮: {selector}")
                        break
                except:
                    # 如果直接选择器失败，尝试通过父元素查找
                    try:
                        copy_button = await self.page.query_selector('button:has(mat-icon[fonticon="content_copy"])')
                        if copy_button:
                            print(f"[DEBUG] ✓ 通过父元素找到复制按钮")
                            break
                    except:
                        continue
            
            if not copy_button:
                # 最后尝试：通过文本内容查找
                print("[DEBUG] 尝试通过文本内容查找复制按钮...")
                copy_button_element = await self.page.locator('button:has-text("Copy table")').first
                if await copy_button_element.count() > 0:
                    print("[DEBUG] ✓ 通过文本定位找到复制按钮")
                    copy_button = copy_button_element
                else:
                    raise Exception("无法定位到复制按钮")
            
            # 点击复制按钮
            print("[DEBUG] 点击复制按钮...")
            await copy_button.click()
            await asyncio.sleep(1)  # 等待复制操作完成
            
            # 从剪贴板获取内容
            print("[DEBUG] 从剪贴板获取内容...")
            copied_content = pyperclip.paste()
            
            if copied_content:
                self.copied_table_content = copied_content
                print(f"[DEBUG] ✓ 成功复制表格内容（长度: {len(copied_content)} 字符）")
                print(f"[DEBUG] 内容预览: {copied_content[:200]}...")
                return copied_content
            else:
                raise Exception("剪贴板内容为空")
            
        except Exception as e:
            print(f"[ERROR] 复制表格失败: {e}")
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
    
    def load_from_session_file(self, session_file: str) -> str:
        """从 session 文件读取生成结果（表格内容）
        
        Args:
            session_file: session 文件路径
            
        Returns:
            str: 生成结果（表格内容）
        """
        filepath = get_absolute_path(session_file)
        
        if not os.path.exists(filepath):
            raise Exception(f"Session 文件不存在: {filepath}")
        
        try:
            content = load_text_from_file(filepath)
            result = extract_table_from_session(content)
            return result
        except Exception as e:
            print(f"[ERROR] 读取 session 文件失败: {e}")
            raise
    
    async def click_new_chat(self):
        """点击 New chat 按钮打开新聊天窗口"""
        print("[DEBUG] 准备打开新聊天窗口...")
        
        try:
            # 查找 New chat 按钮
            new_chat_selector = await find_working_selector(
                self.page,
                SELECTORS["new_chat"],
                timeout=5000
            )
            
            if not new_chat_selector:
                # 尝试通过文本内容查找
                print("[DEBUG] 尝试通过文本内容查找 New chat 按钮...")
                new_chat_element = await self.page.locator('a:has-text("New chat")').first
                if await new_chat_element.count() > 0:
                    print("[DEBUG] ✓ 通过文本定位找到 New chat 按钮")
                    await new_chat_element.click()
                else:
                    raise Exception("无法定位到 New chat 按钮")
            else:
                # 获取New chat按钮元素
                new_chat_button = await self.page.query_selector(new_chat_selector)
                if not new_chat_button:
                    raise Exception("无法获取New chat按钮元素")
                
                # 点击 New chat 按钮
                print("[DEBUG] 点击 New chat 按钮...")
                await new_chat_button.click()
            
            await asyncio.sleep(2)  # 等待新聊天窗口加载
            
            # 等待新页面加载完成
            await self.page.wait_for_load_state('domcontentloaded')
            print("[DEBUG] ✓ 新聊天窗口已打开")
            
        except Exception as e:
            print(f"[ERROR] 打开新聊天窗口失败: {e}")
            raise
    
    async def select_create_images_tool(self):
        """点击 Tools 按钮并选择 Create Images 功能"""
        print("[DEBUG] 准备选择 Create Images 工具...")
        
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
            print("[DEBUG] 点击 Tools 按钮...")
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
                print("[DEBUG] 尝试通过文本内容查找 Create Images...")
                create_images_element = await self.page.locator('text=Create Images').first
                if await create_images_element.count() > 0:
                    print("[DEBUG] ✓ 通过文本定位找到 Create Images")
                    await create_images_element.click()
                else:
                    raise Exception("无法定位到 Create Images 选项")
            else:
                # 获取Create Images元素
                create_images_element = await self.page.query_selector(create_images_selector)
                if not create_images_element:
                    raise Exception("无法获取Create Images元素")
                    
                # 点击 Create Images
                print("[DEBUG] 点击 Create Images...")
                await create_images_element.click()
            
            await asyncio.sleep(0.5)  # 等待工具切换完成
            print("[DEBUG] Create Images 工具已选择")
            
        except Exception as e:
            print(f"[ERROR] 选择 Create Images 工具失败: {e}")
            raise
    
    async def upload_image(self, image_path: str):
        """上传图片到输入框"""
        abs_image_path = get_absolute_path(image_path)
        if not os.path.exists(abs_image_path):
            raise Exception(f"图片文件不存在: {abs_image_path}")
        
        print(f"\n{'='*80}")
        print(f"开始上传图片: {image_path}")
        print(f"{'='*80}\n")
        
        print(f"[INFO] 图片绝对路径: {abs_image_path}")
        print(f"[INFO] 文件大小: {get_file_size(abs_image_path)} bytes\n")
        
        # 使用综合策略上传图片
        from src.core.image_uploader import ImageUploader
        uploader = ImageUploader(self.page)
        success = await uploader.upload_with_strategies(abs_image_path)
        
        if not success:
            raise Exception("所有上传策略都失败了")
    
    async def send_multimodal_message(self, text: str):
        """发送多模态消息（包含图片和文本）"""
        print(f"[DEBUG] 准备发送多模态消息: {text[:100]}...")
        
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
            print("[DEBUG] 点击输入框...")
            await input_element.click()
            await asyncio.sleep(0.3)
            
            # 使用 JavaScript 追加文本内容（不清空现有内容，可能包含图片）
            print("[DEBUG] 使用 JavaScript 追加内容...")
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
            print("[DEBUG] ✓ 内容已通过 JavaScript 设置")
            
            # 点击发送按钮发送消息
            print("[DEBUG] 查找并点击发送按钮...")
            send_button_selector = await find_working_selector(
                self.page,
                SELECTORS["send_button"],
                timeout=5000
            )
            
            if not send_button_selector:
                # 如果找不到发送按钮，尝试按回车作为备用方案
                print("[WARNING] 无法定位发送按钮，尝试按回车发送...")
                await self.page.keyboard.press('Enter')
            else:
                # 获取发送按钮元素
                send_button = await self.page.query_selector(send_button_selector)
                if not send_button:
                    print("[WARNING] 无法获取发送按钮元素，尝试按回车发送...")
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
                        print("[WARNING] 发送按钮不可用，尝试按回车发送...")
                        await self.page.keyboard.press('Enter')
                    else:
                        print(f"[DEBUG] ✓ 找到发送按钮: {send_button_selector}")
                        await send_button.click()
                        await asyncio.sleep(0.5)  # 等待发送完成
                        print("[DEBUG] ✓ 已点击发送按钮")
            
            await asyncio.sleep(0.5)  # 额外等待确保发送完成
            print("[DEBUG] 多模态消息已发送")
            
        except Exception as e:
            print(f"[ERROR] 发送多模态消息失败: {e}")
            raise
    
    async def wait_for_images_generated(self) -> bool:
        """等待图片生成完成"""
        print("[DEBUG] 等待图片生成...")
        
        try:
            # 等待图片容器出现
            container_selector = '.attachment-container.generated-images'
            await self.page.wait_for_selector(
                container_selector,
                timeout=RESPONSE_TIMEOUT
            )
            print("[DEBUG] ✓ 检测到图片容器")
            
            # 等待至少一张图片加载完成
            try:
                await self.page.wait_for_selector(
                    f'{container_selector} img.image.loaded',
                    timeout=RESPONSE_TIMEOUT
                )
                print("[DEBUG] ✓ 检测到至少一张图片已加载")
            except:
                # 如果找不到 loaded 类，尝试查找任何图片
                await self.page.wait_for_selector(
                    f'{container_selector} img[src]',
                    timeout=RESPONSE_TIMEOUT
                )
                print("[DEBUG] ✓ 检测到图片元素")
            
            # 等待图片加载完成
            from src.utils.browser_utils import wait_for_images_loading
            if await wait_for_images_loading(
                self.page,
                container_selector,
                max_timeout=RESPONSE_TIMEOUT
            ):
                print("[DEBUG] ✓ 图片加载完成")
                return True
            else:
                print("[WARNING] 图片加载超时")
                return False
                
        except Exception as e:
            print(f"[ERROR] 等待图片生成失败: {e}")
            return False
    
    async def save_generated_images(self, save_dir: str = DEFAULT_IMAGES_DIR) -> List[str]:
        """保存生成的图片到本地文件夹"""
        from src.core.image_saver import ImageSaver
        saver = ImageSaver(self.page)
        return await saver.save_all_images(save_dir)
    
    async def run(
        self, 
        concept: str = None, 
        demo_image_path: str = DEFAULT_IMAGE_PATH, 
        images_dir: str = DEFAULT_IMAGES_DIR,
        skip_script_generation: bool = False, 
        session_file: str = None
    ):
        """运行完整工作流
        
        Args:
            concept: AI 概念（如"大模型领域的幻觉"），如果不提供则使用初始化时的值
            demo_image_path: demo.png 图片路径，默认为当前目录下的 demo.png
            images_dir: 图片保存目录，默认为 "assets/images"
            skip_script_generation: 是否跳过脚本生成步骤，直接从 session 文件读取
            session_file: 当 skip_script_generation=True 时，指定要读取的 session 文件路径
        """
        if concept:
            self.concept = concept
        
        try:
            # 步骤1: 连接浏览器并打开 Gemini
            await self.connect_to_browser()
            await self.open_gemini()
            
            # 步骤2: 生成脚本或从文件读取
            if skip_script_generation:
                # 跳过脚本生成，直接从 session 文件读取
                print("\n" + "="*80)
                print("步骤1: 从 session 文件读取脚本内容（跳过生成）")
                print("="*80)
                if not session_file:
                    raise Exception("skip_script_generation=True 时必须提供 session_file 参数")
                copied_content = self.load_from_session_file(session_file)
                print("[DEBUG] ✓ 已从 session 文件读取内容")
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
                    print("[DEBUG] ✓ 脚本生成完成")
                else:
                    print("[WARNING] 脚本生成可能未完成，继续尝试复制")
                
                # 步骤4: 复制表格内容
                print("\n" + "="*80)
                print("步骤3: 复制表格内容")
                print("="*80)
                copied_content = await self.copy_table_content()
                
                # 步骤5: 保存到文件
                print("\n" + "="*80)
                print("步骤4: 保存结果到文件")
                print("="*80)
                session_file = self.save_to_file(script_prompt, copied_content)
            
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
            
            # 步骤8: 上传 demo.png 图片
            step_num = 7 if skip_script_generation else 7
            print("\n" + "="*80)
            print(f"步骤{step_num}: 上传 demo.png 图片")
            print("="*80)
            await self.upload_image(demo_image_path)
            await asyncio.sleep(1)  # 等待图片上传完成
            
            # 步骤9: 构建并发送多模态消息（表格内容 + 追加文本）
            step_num = 8 if skip_script_generation else 8
            print("\n" + "="*80)
            print(f"步骤{step_num}: 发送多模态消息（图片 + 表格 + 提示词）")
            print("="*80)
            full_message = copied_content + IMAGE_GENERATION_PROMPT
            await self.send_multimodal_message(full_message)
            
            # 步骤10: 等待图片生成并保存
            step_num = 9 if skip_script_generation else 9
            print("\n" + "="*80)
            print(f"步骤{step_num}: 等待图片生成并保存")
            print("="*80)
            if await self.wait_for_images_generated():
                saved_files = await self.save_generated_images(save_dir=images_dir)
                if saved_files:
                    print(f"[DEBUG] ✓ 成功保存 {len(saved_files)} 张图片到 {images_dir}")
                    for file in saved_files:
                        print(f"  - {file}")
                else:
                    print("[WARNING] 未保存任何图片")
            else:
                print("[WARNING] 图片生成超时或失败")
            
            print("\n" + "="*80)
            print("✓ 工作流完成！")
            print("="*80)
            
        except Exception as e:
            print(f"[ERROR] 工作流执行失败: {e}")
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
        print(f"[INFO] 将从 session 文件读取内容: {session_file}")
        print("[INFO] 跳过脚本生成步骤")
    else:
        # 正常流程：生成脚本
        concept = "大模型领域的幻觉"
        print(f"[INFO] 将生成新脚本，概念: {concept}")
    
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