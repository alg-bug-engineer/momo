"""
图片上传模块
"""

import asyncio
import os
from typing import List

from src.config.settings import SELECTORS, UPLOAD_TIMEOUT
from src.utils.browser_utils import verify_upload
from src.utils.file_utils import get_absolute_path


class ImageUploader:
    """图片上传类"""
    
    def __init__(self, page):
        self.page = page
    
    async def upload_with_filechooser(self, image_path: str) -> bool:
        """
        策略1: 使用 Playwright 的 filechooser 监听器上传文件
        这是最推荐的方式,可以自动拦截文件选择对话框
        """
        print("\n[DEBUG] ========== 策略1: 使用 Playwright filechooser 监听器 ==========")
        
        abs_image_path = get_absolute_path(image_path)
        if not os.path.exists(abs_image_path):
            raise Exception(f"图片文件不存在: {abs_image_path}")
        
        print(f"[DEBUG] 图片绝对路径: {abs_image_path}")
        
        try:
            # 步骤1: 设置文件选择器监听器(在点击之前!)
            print("[DEBUG] 步骤1: 设置文件选择器监听器...")
            
            async with self.page.expect_file_chooser(timeout=UPLOAD_TIMEOUT) as fc_info:
                # 步骤2: 找到并点击上传按钮
                print("[DEBUG] 步骤2: 查找并点击上传按钮...")
                from src.utils.browser_utils import find_working_selector
                
                upload_button = None
                for selector in SELECTORS["upload_button"]:
                    try:
                        upload_button = await self.page.wait_for_selector(selector, timeout=5000)
                        if upload_button and await upload_button.is_visible():
                            print(f"[DEBUG]   ✓ 找到上传按钮: {selector}")
                            break
                    except:
                        continue
                
                if not upload_button:
                    raise Exception("无法找到上传按钮")
                
                await upload_button.click()
                await asyncio.sleep(1)
                
                # 步骤3: 点击 "Upload files" 选项
                print("[DEBUG] 步骤3: 查找并点击 'Upload files' 选项...")
                upload_files = None
                for selector in SELECTORS["upload_files"]:
                    try:
                        upload_files = await self.page.wait_for_selector(selector, timeout=3000)
                        if upload_files and await upload_files.is_visible():
                            print(f"[DEBUG]   ✓ 找到 'Upload files' 选项: {selector}")
                            break
                    except:
                        continue
                
                if not upload_files:
                    raise Exception("无法找到 'Upload files' 选项")
                
                await upload_files.click()
            
            # 步骤4: 监听器会自动捕获文件选择对话框,设置文件
            file_chooser = await fc_info.value
            print(f"[DEBUG] 步骤4: 捕获到文件选择器,设置文件...")
            await file_chooser.set_files(abs_image_path)
            print(f"[DEBUG]   ✓ 文件已设置: {abs_image_path}")
            
            # 步骤5: 等待并验证上传
            print("[DEBUG] 步骤5: 验证上传结果...")
            await asyncio.sleep(2)
            
            attachment_selectors = [
                'img[src*="blob"]',
                'img[src*="data:image"]',
                '.attachment-container img',
                '.uploaded-image',
                '[data-test-id*="attachment"]',
                '[data-test-id*="image"]',
                'img[alt*="upload"]',
                '.preview-image',
                '[class*="attachment"] img',
                '[class*="preview"] img',
                # Gemini 特定的选择器
                '.image-attachment',
                '[role="img"]',
                'img[draggable="false"]',
            ]
            
            uploaded = await verify_upload(self.page, attachment_selectors, timeout=10)
            
            if uploaded:
                print("[DEBUG] ✓ 策略1成功: 文件上传成功!")
                return True
            else:
                print("[DEBUG] ✗ 策略1失败: 未检测到上传结果")
                return False
                
        except Exception as e:
            print(f"[DEBUG] ✗ 策略1失败: {e}")
            return False
    
    async def upload_with_real_input(self, image_path: str) -> bool:
        """
        策略2: 查找并使用真实的文件输入框
        遍历所有文件输入框,尝试直接设置文件
        """
        print("\n[DEBUG] ========== 策略2: 查找并使用真实的文件输入框 ==========")
        
        abs_image_path = get_absolute_path(image_path)
        
        try:
            # 步骤1: 点击上传按钮,激活文件输入框
            print("[DEBUG] 步骤1: 点击上传按钮...")
            from src.utils.browser_utils import find_working_selector
            
            upload_button = None
            for selector in SELECTORS["upload_button"]:
                try:
                    upload_button = await self.page.wait_for_selector(selector, timeout=10000)
                    if upload_button and await upload_button.is_visible():
                        print(f"[DEBUG]   ✓ 找到上传按钮: {selector}")
                        break
                except:
                    continue
            
            if not upload_button:
                raise Exception("无法找到上传按钮")
            
            await upload_button.click()
            await asyncio.sleep(1)
            
            # 步骤2: 查找所有文件输入框(包括隐藏的)
            print("[DEBUG] 步骤2: 查找所有文件输入框...")
            all_inputs = await self.page.query_selector_all('input[type="file"]')
            print(f"[DEBUG]   找到 {len(all_inputs)} 个文件输入框")
            
            if len(all_inputs) == 0:
                print("[DEBUG] ✗ 未找到任何文件输入框")
                return False
            
            # 步骤3: 尝试每个输入框
            for i, file_input in enumerate(all_inputs):
                try:
                    print(f"\n[DEBUG] 步骤3.{i+1}: 尝试输入框 {i}...")
                    
                    # 检查输入框是否可用
                    is_disabled = await file_input.get_attribute('disabled')
                    if is_disabled:
                        print(f"[DEBUG]   输入框 {i} 被禁用,跳过")
                        continue
                    
                    # 获取输入框信息
                    accept = await file_input.get_attribute('accept')
                    print(f"[DEBUG]   输入框 {i} accept 属性: {accept}")
                    
                    # 使用 JavaScript 确保输入框可交互
                    await self.page.evaluate("""
                        (input) => {
                            input.style.display = 'block';
                            input.style.visibility = 'visible';
                            input.style.opacity = '1';
                            input.style.position = 'static';
                            input.style.pointerEvents = 'auto';
                        }
                    """, file_input)
                    
                    # 设置文件
                    print(f"[DEBUG]   设置文件到输入框 {i}...")
                    await file_input.set_input_files(abs_image_path)
                    
                    # 手动触发所有相关事件
                    await self.page.evaluate("""
                        (input) => {
                            const events = ['change', 'input', 'blur'];
                            events.forEach(eventType => {
                                const event = new Event(eventType, { bubbles: true, cancelable: true });
                                input.dispatchEvent(event);
                            });
                            
                            // 也尝试触发父元素的事件
                            if (input.parentElement) {
                                const changeEvent = new Event('change', { bubbles: true, cancelable: true });
                                input.parentElement.dispatchEvent(changeEvent);
                            }
                        }
                    """, file_input)
                    
                    print(f"[DEBUG]   ✓ 文件已设置并触发事件")
                    
                    # 等待并验证上传
                    await asyncio.sleep(2)
                    attachment_selectors = [
                        'img[src*="blob"]',
                        'img[src*="data:image"]',
                        '.attachment-container img',
                        '.uploaded-image',
                        '[data-test-id*="attachment"]',
                        '[data-test-id*="image"]',
                        'img[alt*="upload"]',
                        '.preview-image',
                        '[class*="attachment"] img',
                        '[class*="preview"] img',
                        # Gemini 特定的选择器
                        '.image-attachment',
                        '[role="img"]',
                        'img[draggable="false"]',
                    ]
                    
                    if await verify_upload(self.page, attachment_selectors, timeout=8):
                        print(f"[DEBUG] ✓ 策略2成功: 输入框 {i} 上传成功!")
                        return True
                    else:
                        print(f"[DEBUG]   输入框 {i} 未检测到上传结果,继续尝试...")
                        
                except Exception as e:
                    print(f"[DEBUG]   输入框 {i} 失败: {e}")
                    continue
            
            print("[DEBUG] ✗ 策略2失败: 所有输入框尝试失败")
            return False
            
        except Exception as e:
            print(f"[DEBUG] ✗ 策略2失败: {e}")
            return False
    
    async def upload_with_drag_drop(self, image_path: str) -> bool:
        """
        策略3: 使用拖拽方式上传
        模拟将文件拖放到上传区域
        """
        print("\n[DEBUG] ========== 策略3: 使用拖拽方式上传 ==========")
        
        abs_image_path = get_absolute_path(image_path)
        
        try:
            # 步骤1: 查找上传区域或输入框
            print("[DEBUG] 步骤1: 查找拖放区域...")
            drop_zone_selectors = [
                '.upload-card-button',
                '[class*="upload"]',
                '[data-test-id*="upload"]',
                'input[type="file"]',
                '[role="button"][aria-label*="upload"]',
            ]
            
            drop_zone = None
            for selector in drop_zone_selectors:
                try:
                    drop_zone = await self.page.query_selector(selector)
                    if drop_zone:
                        print(f"[DEBUG]   ✓ 找到拖放区域: {selector}")
                        break
                except:
                    continue
            
            if not drop_zone:
                print("[DEBUG] ✗ 未找到拖放区域")
                return False
            
            # 步骤2: 读取文件内容
            print("[DEBUG] 步骤2: 读取文件内容...")
            with open(abs_image_path, 'rb') as f:
                file_content = f.read()
            
            print(f"[DEBUG]   文件大小: {len(file_content)} bytes")
            
            # 步骤3: 使用 JavaScript 模拟拖放事件
            print("[DEBUG] 步骤3: 模拟拖放事件...")
            
            # 获取文件名
            file_name = os.path.basename(abs_image_path)
            
            # 使用 JavaScript 创建并触发拖放事件
            await self.page.evaluate("""
                async (args) => {
                    const { selector, fileName, fileContent } = args;
                    const element = document.querySelector(selector);
                    
                    if (!element) {
                        throw new Error('未找到目标元素');
                    }
                    
                    // 创建 File 对象
                    const byteArray = new Uint8Array(fileContent);
                    const blob = new Blob([byteArray], { type: 'image/png' });
                    const file = new File([blob], fileName, { type: 'image/png' });
                    
                    // 创建 DataTransfer 对象
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    
                    // 触发拖放事件序列
                    const events = ['dragenter', 'dragover', 'drop'];
                    
                    for (const eventType of events) {
                        const event = new DragEvent(eventType, {
                            bubbles: true,
                            cancelable: true,
                            dataTransfer: dataTransfer
                        });
                        element.dispatchEvent(event);
                    }
                }
            """, {
                'selector': drop_zone_selectors[0],
                'fileName': file_name,
                'fileContent': list(file_content)
            })
            
            print("[DEBUG]   ✓ 拖放事件已触发")
            
            # 步骤4: 验证上传
            await asyncio.sleep(2)
            attachment_selectors = [
                'img[src*="blob"]',
                'img[src*="data:image"]',
                '.attachment-container img',
                '.uploaded-image',
                '[data-test-id*="attachment"]',
                '[data-test-id*="image"]',
                'img[alt*="upload"]',
                '.preview-image',
                '[class*="attachment"] img',
                '[class*="preview"] img',
                # Gemini 特定的选择器
                '.image-attachment',
                '[role="img"]',
                'img[draggable="false"]',
            ]
            
            if await verify_upload(self.page, attachment_selectors, timeout=10):
                print("[DEBUG] ✓ 策略3成功: 拖拽上传成功!")
                return True
            else:
                print("[DEBUG] ✗ 策略3失败: 未检测到上传结果")
                return False
                
        except Exception as e:
            print(f"[DEBUG] ✗ 策略3失败: {e}")
            return False
    
    async def upload_with_strategies(self, image_path: str) -> bool:
        """
        使用多种策略上传图片
        
        Args:
            image_path: 图片路径
            
        Returns:
            bool: 是否上传成功
        """
        # 策略列表(按推荐优先级)
        strategies = [
            ("Playwright filechooser 监听器", self.upload_with_filechooser),
            ("真实文件输入框", self.upload_with_real_input),
            ("拖拽上传", self.upload_with_drag_drop),
        ]
        
        # 依次尝试每个策略
        for strategy_name, strategy_func in strategies:
            try:
                print(f"\n{'='*80}")
                print(f"尝试策略: {strategy_name}")
                print(f"{'='*80}")
                
                success = await strategy_func(image_path)
                
                if success:
                    print(f"\n{'='*80}")
                    print(f"✓ 上传成功! 使用策略: {strategy_name}")
                    print(f"{'='*80}\n")
                    return True
                else:
                    print(f"\n[INFO] 策略 '{strategy_name}' 未成功,尝试下一个策略...\n")
                    
            except Exception as e:
                print(f"\n[ERROR] 策略 '{strategy_name}' 出错: {e}")
                print("[INFO] 尝试下一个策略...\n")
                continue
        
        # 所有策略都失败
        print(f"\n{'='*80}")
        print("✗ 所有上传策略都失败了")
        print(f"{'='*80}\n")
        print("[建议]")
        print("1. 检查页面是否正确加载")
        print("2. 检查是否需要登录")
        print("3. 检查浏览器控制台是否有错误")
        print("4. 尝试手动上传一次,观察 DOM 变化")
        
        return False