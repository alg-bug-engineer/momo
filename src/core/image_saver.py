"""
图片保存模块
"""

import os
import time
from pathlib import Path
from typing import List
from urllib.parse import urlparse


class ImageSaver:
    """图片保存类"""
    
    def __init__(self, page):
        self.page = page
    
    async def save_all_images(self, save_dir: str) -> List[str]:
        """
        保存所有生成的图片到本地文件夹
        
        优先使用浏览器原生下载（点击下载按钮），获得原始清晰度
        如果失败，依次尝试 request API 和截图方式
        
        Args:
            save_dir: 保存目录
            
        Returns:
            List[str]: 保存的文件路径列表
        """
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
                        download_button = await self._find_download_button(container)
                        
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
                            img_src = self._process_image_url(img_src)
                            
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
    
    async def _find_download_button(self, container):
        """查找下载按钮"""
        from src.config.settings import SELECTORS
        
        download_button = None
        for btn_selector in SELECTORS["download_button"]:
            try:
                download_button = await container.query_selector(btn_selector)
                if download_button:
                    print(f"[DEBUG] ✓ 找到下载按钮: {btn_selector}")
                    break
            except:
                continue
        
        return download_button
    
    def _process_image_url(self, img_src):
        """处理图片URL，确保是完整的绝对URL"""
        if img_src.startswith('//'):
            img_src = 'https:' + img_src
        elif img_src.startswith('/'):
            img_src = 'https://gemini.google.com' + img_src
        return img_src