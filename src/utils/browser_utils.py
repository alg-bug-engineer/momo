"""
浏览器操作工具模块
"""

import asyncio
import time
from typing import List, Optional


async def find_working_selector(page, selectors: List[str], timeout: int = 10000) -> Optional[str]:
    """
    尝试多个选择器，返回第一个有效的选择器
    
    Args:
        page: Playwright页面对象
        selectors: 选择器列表
        timeout: 每个选择器的超时时间（毫秒）
        
    Returns:
        Optional[str]: 有效的选择器，如果都无效则返回None
    """
    for selector in selectors:
        try:
            await page.wait_for_selector(selector, timeout=timeout // 10)
            element = await page.query_selector(selector)
            if element and await element.is_visible():
                print(f"[DEBUG] ✓ 选择器有效: {selector}")
                return selector
        except:
            print(f"[DEBUG] ✗ 选择器无效: {selector}")
            continue
    
    return None


async def wait_for_content_stabilization(
    page, 
    content_selector: str, 
    max_timeout: int = 180000, 
    check_interval: int = 2000, 
    stable_count: int = 3
) -> bool:
    """
    等待内容稳定（不再变化）
    
    Args:
        page: Playwright页面对象
        content_selector: 内容选择器
        max_timeout: 最大超时时间（毫秒）
        check_interval: 检查间隔（毫秒）
        stable_count: 连续相同次数视为稳定
        
    Returns:
        bool: 是否成功等待到内容稳定
    """
    start_time = time.time()
    last_text = ""
    current_stable_count = 0
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > max_timeout / 1000.0:
            print("[WARNING] 等待内容稳定超时")
            return False
        
        try:
            current_text = await page.evaluate(f"""
                () => {{
                    const element = document.querySelector('{content_selector}');
                    return element ? element.innerText : '';
                }}
            """)
            
            if current_text == last_text:
                current_stable_count += 1
                if current_stable_count >= stable_count:
                    print("[DEBUG] ✓ 内容已稳定")
                    return True
            else:
                current_stable_count = 0
                last_text = current_text
            
            await asyncio.sleep(check_interval / 1000.0)
            
        except Exception as e:
            print(f"[DEBUG] 检查内容状态时出错: {e}，继续等待...")
            await asyncio.sleep(check_interval / 1000.0)


async def wait_for_images_loading(
    page,
    container_selector: str,
    image_selector: str = 'img[src]',
    max_timeout: int = 120000,
    check_interval: int = 1000
) -> bool:
    """
    等待图片加载完成
    
    Args:
        page: Playwright页面对象
        container_selector: 图片容器选择器
        image_selector: 图片元素选择器
        max_timeout: 最大超时时间（毫秒）
        check_interval: 检查间隔（毫秒）
        
    Returns:
        bool: 是否成功等待到图片加载完成
    """
    start_time = time.time()
    timeout_seconds = min(max_timeout / 1000.0, 30)
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print("[WARNING] 等待图片加载超时")
            return False
        
        try:
            # 检查是否有已加载的图片
            loaded_images_count = await page.locator(
                f'{container_selector} img.image.loaded'
            ).count()
            
            # 检查是否有任何图片（即使没有 loaded 类）
            all_images_count = await page.locator(
                f'{container_selector} {image_selector}'
            ).count()
            
            # 如果检测到已加载的图片，即使 loader 还在也认为完成
            if loaded_images_count > 0:
                print(f"[DEBUG] ✓ 检测到 {loaded_images_count} 张图片已加载完成")
                return True
            
            # 如果有图片但还没加载完成，继续等待
            if all_images_count > 0:
                loader_count = await page.locator(
                    f'{container_selector} .loader'
                ).count()
                if loader_count == 0:
                    print("[DEBUG] ✓ 所有 loader 已消失")
                    return True
                else:
                    print(f"[DEBUG] 检测到 {all_images_count} 张图片，还有 {loader_count} 个 loader，继续等待...")
            else:
                # 没有图片，继续等待
                pass
                
            await asyncio.sleep(check_interval / 1000.0)
            
        except Exception as e:
            print(f"[DEBUG] 检查图片状态时出错: {e}，继续等待...")
            await asyncio.sleep(check_interval / 1000.0)


async def verify_upload(
    page,
    attachment_selectors: List[str],
    timeout: int = 10
) -> bool:
    """
    验证文件是否已上传
    
    Args:
        page: Playwright页面对象
        attachment_selectors: 附件选择器列表
        timeout: 超时时间（秒）
        
    Returns:
        bool: 是否验证到上传成功
    """
    start_time = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        for selector in attachment_selectors:
            try:
                attachment = await page.query_selector(selector)
                if attachment:
                    is_visible = await attachment.is_visible()
                    if is_visible:
                        src = await attachment.get_attribute('src')
                        print(f"[DEBUG] ✓ 检测到图片附件: {selector}")
                        print(f"[DEBUG]   图片 src: {src[:100] if src else 'N/A'}")
                        return True
            except:
                continue
        
        await asyncio.sleep(0.5)
    
    print("[DEBUG] ✗ 未检测到图片附件")
    return False