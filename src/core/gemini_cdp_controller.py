"""
Gemini CDP 控制器
"""

import asyncio
import os
import time
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from src.core.browser_controller import BrowserController
from src.config.settings import SELECTORS, UPLOAD_TIMEOUT, IMAGE_GENERATION_TIMEOUT
from src.utils.browser_utils import find_working_selector, wait_for_images_loading, verify_upload


class GeminiCDPController(BrowserController):
    """Gemini CDP 控制器"""
    
    async def select_create_images_tool(self):
        """点击 Tools 按钮并选择 Create Images 功能"""
        print("[DEBUG] 准备选择 Create Images 工具...")
        
        try:
            # 查找并点击 Tools 按钮
            tools_button = await find_working_selector(
                self.page, 
                SELECTORS["tools_button"], 
                timeout=5000
            )
            
            if not tools_button:
                raise Exception("无法定位到 Tools 按钮")
            
            # 点击 Tools 按钮
            print("[DEBUG] 点击 Tools 按钮...")
            await self.page.click(tools_button)
            await asyncio.sleep(0.5)  # 等待菜单展开
            
            # 查找并点击 Create Images 选项
            create_images = await find_working_selector(
                self.page, 
                SELECTORS["create_images"], 
                timeout=5000
            )
            
            if not create_images:
                # 如果直接选择器失败，尝试通过文本内容查找
                print("[DEBUG] 尝试通过文本内容查找 Create Images...")
                create_images_element = await self.page.locator('text=Create Images').first
                if await create_images_element.count() > 0:
                    print("[DEBUG] ✓ 通过文本定位找到 Create Images")
                    await create_images_element.click()
                else:
                    raise Exception("无法定位到 Create Images 选项")
            else:
                # 点击 Create Images
                print("[DEBUG] 点击 Create Images...")
                await self.page.click(create_images)
            
            await asyncio.sleep(0.5)  # 等待工具切换完成
            print("[DEBUG] Create Images 工具已选择")
            
        except Exception as e:
            print(f"[ERROR] 选择 Create Images 工具失败: {e}")
            raise
    
    async def send_message(self, query: str):
        """在输入框输入文本并发送"""
        print(f"[DEBUG] 准备发送消息: {query}")
        
        try:
            # 查找输入框
            selector = await find_working_selector(
                self.page, 
                SELECTORS["input_field"], 
                timeout=10000
            )
            
            if not selector:
                raise Exception("无法定位到输入框")
            
            # 点击输入框
            print("[DEBUG] 点击输入框...")
            await self.page.click(selector)
            await asyncio.sleep(0.3)  # 等待输入框获得焦点
            
            # 清空输入框
            print("[DEBUG] 清空输入框...")
            # 全选（Mac 使用 Cmd+A，其他系统使用 Ctrl+A）
            await self.page.keyboard.press('Meta+a')  # Mac
            await asyncio.sleep(0.1)
            await self.page.keyboard.press('Control+a')  # Windows/Linux
            await asyncio.sleep(0.1)
            # 删除选中内容
            await self.page.keyboard.press('Backspace')
            await asyncio.sleep(0.2)
            
            # 输入文本
            print(f"[DEBUG] 输入文本: {query}")
            await self.page.type(selector, query, delay=50)
            
            # 按回车发送
            print("[DEBUG] 按回车发送...")
            await self.page.keyboard.press('Enter')
            print("[DEBUG] 消息已发送")
            
        except Exception as e:
            print(f"[ERROR] 发送消息失败: {e}")
            raise
    
    async def wait_for_images_generated(self) -> bool:
        """等待图片生成完成"""
        print("[DEBUG] 等待图片生成...")
        
        try:
            # 等待图片容器出现
            container_selector = '.attachment-container.generated-images'
            await self.page.wait_for_selector(
                container_selector,
                timeout=IMAGE_GENERATION_TIMEOUT
            )
            print("[DEBUG] ✓ 检测到图片容器")
            
            # 等待至少一张图片加载完成
            try:
                await self.page.wait_for_selector(
                    f'{container_selector} img.image.loaded',
                    timeout=IMAGE_GENERATION_TIMEOUT
                )
                print("[DEBUG] ✓ 检测到至少一张图片已加载")
            except:
                # 如果找不到 loaded 类，尝试查找任何图片
                await self.page.wait_for_selector(
                    f'{container_selector} img[src]',
                    timeout=IMAGE_GENERATION_TIMEOUT
                )
                print("[DEBUG] ✓ 检测到图片元素")
            
            # 等待图片加载完成
            if await wait_for_images_loading(
                self.page,
                container_selector,
                max_timeout=IMAGE_GENERATION_TIMEOUT
            ):
                print("[DEBUG] ✓ 图片加载完成")
                return True
            else:
                print("[WARNING] 图片加载超时")
                return False
                
        except Exception as e:
            print(f"[ERROR] 等待图片生成失败: {e}")
            return False
    
    async def save_generated_images(self, save_dir: str = "assets/images") -> List[str]:
        """保存生成的图片到本地文件夹"""
        print(f"[DEBUG] 准备保存图片到 {save_dir}...")
        
        # 创建保存目录
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        print(f"[DEBUG] ✓ 目录已创建/存在: {save_path.absolute()}")
        
        saved_files = []
        
        try:
            # 查找所有生成的图片容器
            container_selectors = [
                '.attachment-container.generated-images generated-image',
                '.generated-image',
            ]
            
            containers = []
            for selector in container_selectors:
                try:
                    container_elements = await self.page.query_selector_all(selector)
                    if container_elements:
                        containers = container_elements
                        print(f"[DEBUG] ✓ 使用选择器找到 {len(containers)} 个图片容器: {selector}")
                        break
                except:
                    continue
            
            if not containers:
                print("[WARNING] 未找到生成的图片容器")
                return saved_files
            
            print(f"[DEBUG] 找到 {len(containers)} 张图片，开始下载...")
            
            for idx, container in enumerate(containers):
                try:
                    print(f"[DEBUG] 处理图片 {idx + 1}/{len(containers)}...")
                    
                    # 方法1: 优先尝试点击下载按钮（获得原始清晰度）
                    download_success = False
                    try:
                        download_button = None
                        for btn_selector in SELECTORS["download_button"]:
                            try:
                                download_button = await container.query_selector(btn_selector)
                                if download_button:
                                    print(f"[DEBUG] ✓ 找到下载按钮: {btn_selector}")
                                    break
                            except:
                                continue
                        
                        if download_button:
                            # 使用 Playwright 的下载监听功能
                            print("[DEBUG] 点击下载按钮，使用浏览器原生下载...")
                            
                            # 监听下载事件
                            async with self.page.expect_download(timeout=30000) as download_info:
                                await download_button.click()
                            
                            download = await download_info.value
                            
                            # 生成文件名
                            suggested_filename = download.suggested_filename
                            if not suggested_filename:
                                ext = '.png'  # 默认扩展名
                                suggested_filename = f"image_{int(time.time())}_{idx + 1}{ext}"
                            
                            # 保存文件
                            file_path = save_path / suggested_filename
                            await download.save_as(str(file_path))
                            
                            saved_files.append(str(file_path.absolute()))
                            print(f"[DEBUG] ✓ 图片已保存（原生下载）: {file_path.absolute()}")
                            download_success = True
                            
                    except Exception as download_btn_error:
                        print(f"[DEBUG] 下载按钮方式失败: {download_btn_error}")
                    
                    # 方法2: 如果下载按钮失败，尝试直接下载图片 URL
                    if not download_success:
                        try:
                            img_element = await container.query_selector('img[src]')
                            if not img_element:
                                raise Exception("未找到图片元素")
                            
                            img_src = await img_element.get_attribute('src')
                            if not img_src:
                                raise Exception("图片没有 src 属性")
                            
                            # 处理相对 URL
                            if img_src.startswith('//'):
                                img_src = 'https:' + img_src
                            elif img_src.startswith('/'):
                                img_src = 'https://gemini.google.com' + img_src
                            
                            print(f"[DEBUG] 尝试直接下载图片 URL: {img_src[:80]}...")
                            
                            # 使用 Playwright 的 request API 下载
                            response = await self.page.request.get(img_src)
                            
                            if response.ok:
                                # 从 URL 获取文件扩展名
                                parsed_url = urlparse(img_src)
                                ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
                                
                                filename = f"image_{int(time.time())}_{idx + 1}{ext}"
                                file_path = save_path / filename
                                
                                content = await response.body()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                
                                saved_files.append(str(file_path.absolute()))
                                print(f"[DEBUG] ✓ 图片已保存（URL下载）: {file_path.absolute()}")
                                download_success = True
                            else:
                                raise Exception(f"下载失败，状态码: {response.status}")
                                
                        except Exception as url_error:
                            print(f"[DEBUG] URL 下载失败: {url_error}")
                    
                    # 方法3: 如果都失败，使用截图作为兜底（清晰度较低）
                    if not download_success:
                        try:
                            print("[DEBUG] 使用截图方式作为兜底...")
                            img_element = await container.query_selector('img[src]')
                            if img_element:
                                filename = f"image_{int(time.time())}_{idx + 1}.png"
                                file_path = save_path / filename
                                
                                await img_element.screenshot(path=str(file_path))
                                
                                saved_files.append(str(file_path.absolute()))
                                print(f"[DEBUG] ✓ 图片已保存（截图方式，清晰度较低）: {file_path.absolute()}")
                            else:
                                raise Exception("未找到图片元素")
                        except Exception as screenshot_error:
                            print(f"[ERROR] 截图方式也失败: {screenshot_error}")
                            print(f"[ERROR] 所有下载方式都失败，跳过图片 {idx + 1}")
                            
                except Exception as e:
                    print(f"[ERROR] 处理图片 {idx + 1} 时出错: {e}")
                    continue
            
            print(f"[DEBUG] 共保存 {len(saved_files)} 张图片")
            return saved_files
            
        except Exception as e:
            print(f"[ERROR] 保存图片失败: {e}")
            return saved_files
    
    async def run(self, query: str, use_create_images: bool = False, save_images: bool = True, images_dir: str = "assets/images"):
        """运行完整流程
        
        Args:
            query: 要发送的查询文本
            use_create_images: 是否使用 Create Images 工具
            save_images: 是否保存生成的图片（仅在 use_create_images=True 时有效）
            images_dir: 图片保存目录，默认为 "assets/images"
        """
        try:
            await self.connect_to_browser()
            await self.open_gemini()
            
            if use_create_images:
                await self.select_create_images_tool()
            
            await self.send_message(query)
            
            # 如果使用 Create Images 工具且需要保存图片，则等待图片生成并保存
            if use_create_images and save_images:
                if await self.wait_for_images_generated():
                    saved_files = await self.save_generated_images(save_dir=images_dir)
                    if saved_files:
                        print(f"[DEBUG] ✓ 成功保存 {len(saved_files)} 张图片到 {images_dir}")
                    else:
                        print("[WARNING] 未保存任何图片")
                else:
                    print("[WARNING] 图片生成超时或失败")
            
            print("[DEBUG] 任务完成")
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            await self.close()


async def main():
    """主函数"""
    controller = GeminiCDPController()
    # 使用 Create Images 工具并发送查询
    await controller.run("画一只猫输出图片", use_create_images=True)


if __name__ == '__main__':
    asyncio.run(main())