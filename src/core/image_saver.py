"""
图片保存模块
"""

import os
import time
from pathlib import Path
import asyncio
from typing import List
from urllib.parse import urlparse

from src.utils.logger import get_logger


class ImageSaver:
    """图片保存类"""
    
    def __init__(self, page, session_id=None):
        self.page = page
        self.session_id = session_id
        self.logger = get_logger(session_id)
    
    async def save_all_images_sequentially(self, save_dir: str, total_batches: int) -> List[str]:
        """
        按顺序保存所有生成的图片容器到本地文件夹（使用数字序号命名）
        
        Args:
            save_dir: 保存目录
            total_batches: 总批次数（用于验证容器数量）
            
        Returns:
            List[str]: 保存的文件路径列表（按顺序，1.png, 2.png, ...）
        """
        self.logger.debug(f"准备按顺序保存所有图片到 {save_dir}...")
        
        # 创建保存目录
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"✓ 目录已创建/存在: {save_path.absolute()}")
        
        saved_files = []
        
        try:
            # 查找所有生成的图片容器（使用主容器选择器）
            container_selector = '.attachment-container.generated-images'
            containers = await self.page.query_selector_all(container_selector)
            
            if not containers:
                self.logger.warning("未找到生成的图片容器")
                return saved_files
            
            container_count = len(containers)
            self.logger.debug(f"找到 {container_count} 个图片容器（期望 {total_batches} 个）")
            
            if container_count != total_batches:
                self.logger.warning(f"容器数量 ({container_count}) 与批次数 ({total_batches}) 不一致，继续保存...")
            
            # 按顺序处理每个容器
            for idx, container in enumerate(containers, 1):
                try:
                    self.logger.debug(f"处理图片容器 {idx}/{container_count}...")
                    
                    # ==================== 新增修复代码 ====================
                    # 1. 强制滚动到当前容器，触发懒加载
                    try:
                        await container.scroll_into_view_if_needed()
                        # 额外等待一下，给浏览器渲染时间
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"[DEBUG] 滚动到容器 {idx} 失败: {e}")

                    # 2. 显式等待容器内的图片元素出现
                    try:
                        # 等待图片元素出现在 DOM 中且可见
                        # 注意：这里不能直接用 page.wait_for_selector，因为我们要限定在 container 内部
                        # 使用 wait_for 方法（如果 playwright 版本支持 element_handle.wait_for_selector）
                        # 或者简单的轮询检查
                        for _ in range(5): # 最多重试 5 次
                            img_check = await container.query_selector('img[src]')
                            if img_check:
                                break
                            await asyncio.sleep(1)
                    except Exception as wait_err:
                         print(f"[DEBUG] 等待图片元素出现出错: {wait_err}")
                    # ====================================================

                    # 首先尝试在容器内查找子容器（generated-image），如果没有则直接使用主容器
                    sub_container = None
                    sub_container_selectors = [
                        'generated-image',
                        '.generated-image',
                    ]
                    
                    for sub_selector in sub_container_selectors:
                        try:
                            sub_container = await container.query_selector(sub_selector)
                            if sub_container:
                                self.logger.debug(f"✓ 在容器 {idx} 中找到子容器: {sub_selector}")
                                break
                        except:
                            continue
                    
                    # 如果找到子容器，使用子容器；否则使用主容器
                    target_container = sub_container if sub_container else container
                    
                    # 方法1: 优先尝试点击下载按钮（获得原始清晰度）
                    download_success = False
                    try:
                        download_button = await self._find_download_button(target_container)
                        
                        if download_button:
                            # 使用 Playwright 的下载监听功能
                            self.logger.debug("点击下载按钮，使用浏览器原生下载...")
                            
                            # 监听下载事件
                            async with self.page.expect_download(timeout=30000) as download_info:
                                await download_button.click()
                            
                            download = await download_info.value
                            
                            # 获取文件扩展名
                            suggested_filename = download.suggested_filename
                            if suggested_filename:
                                ext = os.path.splitext(suggested_filename)[1] or '.png'
                            else:
                                ext = '.png'
                            
                            # 使用数字序号命名
                            filename = f"{idx}{ext}"
                            file_path = save_path / filename
                            await download.save_as(str(file_path))
                            
                            saved_files.append(str(file_path.absolute()))
                            self.logger.debug(f"✓ 图片已保存（原生下载）: {file_path.absolute()}")
                            download_success = True
                            
                    except Exception as download_btn_error:
                        self.logger.debug(f"下载按钮方式失败: {download_btn_error}")
                    
                    # 方法2: 如果下载按钮失败，尝试直接下载图片 URL
                    if not download_success:
                        try:
                            img_element = await target_container.query_selector('img[src]')
                            if not img_element:
                                raise Exception("未找到图片元素")
                            
                            img_src = await img_element.get_attribute('src')
                            if not img_src:
                                raise Exception("图片没有 src 属性")
                            
                            # 处理相对 URL
                            img_src = self._process_image_url(img_src)
                            
                            self.logger.debug(f"尝试直接下载图片 URL: {img_src[:80]}...")
                            
                            # 使用 Playwright 的 request API 下载
                            response = await self.page.request.get(img_src)
                            
                            if response.ok:
                                # 从 URL 获取文件扩展名
                                parsed_url = urlparse(img_src)
                                ext = os.path.splitext(parsed_url.path)[1] or '.png'
                                
                                # 使用数字序号命名
                                filename = f"{idx}{ext}"
                                file_path = save_path / filename
                                
                                content = await response.body()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                
                                saved_files.append(str(file_path.absolute()))
                                self.logger.debug(f"✓ 图片已保存（URL下载）: {file_path.absolute()}")
                                download_success = True
                            else:
                                raise Exception(f"下载失败，状态码: {response.status}")
                                
                        except Exception as url_error:
                            self.logger.debug(f"URL 下载失败: {url_error}")
                    
                    # 方法3: 如果都失败，使用截图作为兜底（清晰度较低）
                    if not download_success:
                        try:
                            self.logger.debug("使用截图方式作为兜底...")
                            img_element = await target_container.query_selector('img[src]')
                            if img_element:
                                # 使用数字序号命名
                                filename = f"{idx}.png"
                                file_path = save_path / filename
                                
                                await img_element.screenshot(path=str(file_path))
                                
                                saved_files.append(str(file_path.absolute()))
                                self.logger.debug(f"✓ 图片已保存（截图方式，清晰度较低）: {file_path.absolute()}")
                            else:
                                raise Exception("未找到图片元素")
                        except Exception as screenshot_error:
                            self.logger.error(f"截图方式也失败: {screenshot_error}")
                            self.logger.error(f"所有下载方式都失败，跳过图片容器 {idx}")
                            
                except Exception as e:
                    self.logger.error(f"处理图片容器 {idx} 时出错: {e}")
                    continue
            
            self.logger.debug(f"共保存 {len(saved_files)} 张图片（按顺序命名）")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"保存图片失败: {e}")
            return saved_files
    
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
        self.logger.debug(f"准备保存图片到 {save_dir}...")
        
        # 创建保存目录
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"✓ 目录已创建/存在: {save_path.absolute()}")
        
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
                        self.logger.debug(f"✓ 使用选择器找到 {len(containers)} 个图片容器: {selector}")
                        break
                except:
                    continue
            
            if not containers:
                self.logger.warning("未找到生成的图片容器")
                return saved_files
            
            self.logger.debug(f"找到 {len(containers)} 张图片，开始下载...")
            
            for idx, container in enumerate(containers):
                try:
                    self.logger.debug(f"处理图片 {idx + 1}/{len(containers)}...")
                    
                    # 方法1: 优先尝试点击下载按钮（获得原始清晰度）
                    download_success = False
                    try:
                        download_button = await self._find_download_button(container)
                        
                        if download_button:
                            # 使用 Playwright 的下载监听功能
                            self.logger.debug("点击下载按钮，使用浏览器原生下载...")
                            
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
                            self.logger.debug(f"✓ 图片已保存（原生下载）: {file_path.absolute()}")
                            download_success = True
                            
                    except Exception as download_btn_error:
                        self.logger.debug(f"下载按钮方式失败: {download_btn_error}")
                    
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
                            
                            self.logger.debug(f"尝试直接下载图片 URL: {img_src[:80]}...")
                            
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
                                self.logger.debug(f"✓ 图片已保存（URL下载）: {file_path.absolute()}")
                                download_success = True
                            else:
                                raise Exception(f"下载失败，状态码: {response.status}")
                                
                        except Exception as url_error:
                            self.logger.debug(f"URL 下载失败: {url_error}")
                    
                    # 方法3: 如果都失败，使用截图作为兜底（清晰度较低）
                    if not download_success:
                        try:
                            self.logger.debug("使用截图方式作为兜底...")
                            img_element = await container.query_selector('img[src]')
                            if img_element:
                                filename = f"image_{int(time.time())}_{idx + 1}.png"
                                file_path = save_path / filename
                                
                                await img_element.screenshot(path=str(file_path))
                                
                                saved_files.append(str(file_path.absolute()))
                                self.logger.debug(f"✓ 图片已保存（截图方式，清晰度较低）: {file_path.absolute()}")
                            else:
                                raise Exception("未找到图片元素")
                        except Exception as screenshot_error:
                            self.logger.error(f"截图方式也失败: {screenshot_error}")
                            self.logger.error(f"所有下载方式都失败，跳过图片 {idx + 1}")
                            
                except Exception as e:
                    self.logger.error(f"处理图片 {idx + 1} 时出错: {e}")
                    continue
            
            self.logger.debug(f"共保存 {len(saved_files)} 张图片")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"保存图片失败: {e}")
            return saved_files
    
    async def save_images_by_urls(self, save_dir: str, target_urls: List[str]) -> List[str]:
        """
        根据URL列表保存指定的图片到本地文件夹
        
        Args:
            save_dir: 保存目录
            target_urls: 目标图片URL列表
            
        Returns:
            List[str]: 保存的文件路径列表
        """
        self.logger.debug(f"准备保存 {len(target_urls)} 张指定URL的图片到 {save_dir}...")
        
        # 创建保存目录
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"✓ 目录已创建/存在: {save_path.absolute()}")
        
        saved_files = []
        target_urls_set = set(target_urls)
        
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
                        self.logger.debug(f"✓ 使用选择器找到 {len(containers)} 个图片容器: {selector}")
                        break
                except:
                    continue
            
            if not containers:
                self.logger.warning("未找到生成的图片容器")
                return saved_files
            
            # 遍历所有容器，只保存URL匹配的图片
            matched_count = 0
            for idx, container in enumerate(containers):
                try:
                    # 获取容器中的图片元素
                    img_element = await container.query_selector('img[src]')
                    if not img_element:
                        continue
                    
                    img_src = await img_element.get_attribute('src')
                    if not img_src:
                        continue
                    
                    # 处理相对URL，确保可以匹配
                    processed_url = self._process_image_url(img_src)
                    
                    # 检查这个URL是否在目标列表中（需要处理URL格式差异）
                    is_target = False
                    for target_url in target_urls:
                        # 处理目标URL
                        processed_target = self._process_image_url(target_url)
                        # 比较处理后的URL（去除可能的查询参数差异）
                        if processed_url == processed_target or processed_url in processed_target or processed_target in processed_url:
                            is_target = True
                            break
                    
                    if not is_target:
                        self.logger.debug(f"跳过图片 {idx + 1}（URL不匹配）")
                        continue
                    
                    matched_count += 1
                    self.logger.debug(f"处理目标图片 {matched_count}/{len(target_urls)}...")
                    
                    # 方法1: 优先尝试点击下载按钮（获得原始清晰度）
                    download_success = False
                    try:
                        download_button = await self._find_download_button(container)
                        
                        if download_button:
                            # 使用 Playwright 的下载监听功能
                            self.logger.debug("点击下载按钮，使用浏览器原生下载...")
                            
                            # 监听下载事件
                            async with self.page.expect_download(timeout=30000) as download_info:
                                await download_button.click()
                            
                            download = await download_info.value
                            
                            # 生成文件名
                            suggested_filename = download.suggested_filename
                            if not suggested_filename:
                                ext = '.png'  # 默认扩展名
                                suggested_filename = f"image_{int(time.time())}_{matched_count}{ext}"
                            
                            # 保存文件
                            file_path = save_path / suggested_filename
                            await download.save_as(str(file_path))
                            
                            saved_files.append(str(file_path.absolute()))
                            self.logger.debug(f"✓ 图片已保存（原生下载）: {file_path.absolute()}")
                            download_success = True
                            
                    except Exception as download_btn_error:
                        self.logger.debug(f"下载按钮方式失败: {download_btn_error}")
                    
                    # 方法2: 如果下载按钮失败，尝试直接下载图片 URL
                    if not download_success:
                        try:
                            self.logger.debug(f"尝试直接下载图片 URL: {processed_url[:80]}...")
                            
                            # 使用 Playwright 的 request API 下载
                            response = await self.page.request.get(processed_url)
                            
                            if response.ok:
                                # 从 URL 获取文件扩展名
                                parsed_url = urlparse(processed_url)
                                ext = os.path.splitext(parsed_url.path)[1] or '.jpg'
                                
                                filename = f"image_{int(time.time())}_{matched_count}{ext}"
                                file_path = save_path / filename
                                
                                content = await response.body()
                                with open(file_path, 'wb') as f:
                                    f.write(content)
                                
                                saved_files.append(str(file_path.absolute()))
                                self.logger.debug(f"✓ 图片已保存（URL下载）: {file_path.absolute()}")
                                download_success = True
                            else:
                                raise Exception(f"下载失败，状态码: {response.status}")
                                
                        except Exception as url_error:
                            self.logger.debug(f"URL 下载失败: {url_error}")
                    
                    # 方法3: 如果都失败，使用截图作为兜底（清晰度较低）
                    if not download_success:
                        try:
                            self.logger.debug("使用截图方式作为兜底...")
                            filename = f"image_{int(time.time())}_{matched_count}.png"
                            file_path = save_path / filename
                            
                            await img_element.screenshot(path=str(file_path))
                            
                            saved_files.append(str(file_path.absolute()))
                            self.logger.debug(f"✓ 图片已保存（截图方式，清晰度较低）: {file_path.absolute()}")
                        except Exception as screenshot_error:
                            self.logger.error(f"截图方式也失败: {screenshot_error}")
                            self.logger.error(f"所有下载方式都失败，跳过图片 {matched_count}")
                            
                except Exception as e:
                    self.logger.error(f"处理图片 {idx + 1} 时出错: {e}")
                    continue
            
            self.logger.debug(f"共保存 {len(saved_files)} 张目标图片（匹配到 {matched_count} 张）")
            return saved_files
            
        except Exception as e:
            self.logger.error(f"保存图片失败: {e}")
            return saved_files
    
    async def _find_download_button(self, container):
        """查找下载按钮"""
        from src.config.settings import SELECTORS
        
        download_button = None
        for btn_selector in SELECTORS["download_button"]:
            try:
                download_button = await container.query_selector(btn_selector)
                if download_button:
                    self.logger.debug(f"✓ 找到下载按钮: {btn_selector}")
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