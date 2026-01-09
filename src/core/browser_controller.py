"""
浏览器控制器基类
"""

import asyncio
import aiohttp
import json
from playwright.async_api import async_playwright
from src.config.settings import CHROME_CDP_URL, GEMINI_URL


class BrowserController:
    """浏览器控制器基类"""
    
    def __init__(self, cdp_url: str = CHROME_CDP_URL):
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def _get_websocket_url(self, http_url: str) -> str:
        """从 HTTP CDP 端点获取 WebSocket URL"""
        try:
            async with aiohttp.ClientSession() as session:
                # 尝试从 /json/version 获取 WebSocket URL
                version_url = f"{http_url.rstrip('/')}/json/version"
                try:
                    async with session.get(version_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            ws_url = data.get('webSocketDebuggerUrl')
                            if ws_url:
                                print(f"[DEBUG] 从 /json/version 获取到 WebSocket URL: {ws_url}")
                                return ws_url
                except Exception as e:
                    print(f"[DEBUG] 从 /json/version 获取失败: {e}")
                
                # 如果 /json/version 失败，尝试从 /json 获取
                list_url = f"{http_url.rstrip('/')}/json"
                try:
                    async with session.get(list_url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and len(data) > 0:
                                ws_url = data[0].get('webSocketDebuggerUrl')
                                if ws_url:
                                    print(f"[DEBUG] 从 /json 获取到 WebSocket URL: {ws_url}")
                                    return ws_url
                except Exception as e:
                    print(f"[DEBUG] 从 /json 获取失败: {e}")
        except Exception as e:
            print(f"[DEBUG] 获取 WebSocket URL 失败: {e}")
        
        # 如果无法获取，尝试构造 WebSocket URL
        if http_url.startswith('http://'):
            ws_url = http_url.replace('http://', 'ws://')
        elif http_url.startswith('https://'):
            ws_url = http_url.replace('https://', 'wss://')
        else:
            ws_url = http_url
        
        print(f"[DEBUG] 使用构造的 WebSocket URL: {ws_url}")
        return ws_url
    
    async def connect_to_browser(self):
        """连接到已启动的 Chrome 浏览器"""
        print("[DEBUG] 连接到 Chrome 浏览器...")
        
        self.playwright = await async_playwright().start()
        
        try:
            print("[DEBUG] 连接 CDP 端点...")
            # 如果 URL 是 HTTP/HTTPS，尝试获取 WebSocket URL
            if self.cdp_url.startswith('http://') or self.cdp_url.startswith('https://'):
                ws_url = await self._get_websocket_url(self.cdp_url)
                self.browser = await self.playwright.chromium.connect_over_cdp(ws_url)
            else:
                # 如果已经是 WebSocket URL，直接使用
                self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            print("[DEBUG] CDP 连接成功")
            
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                print("[DEBUG] 使用现有浏览器上下文")
            else:
                self.context = await self.browser.new_context()
                print("[DEBUG] 创建新上下文")
            
            pages = self.context.pages
            if pages:
                self.page = pages[0]
                print(f"[DEBUG] 使用现有页面: {self.page.url}")
            else:
                self.page = await self.context.new_page()
                print("[DEBUG] 创建新页面")
            
        except Exception as e:
            print(f"[ERROR] 连接浏览器失败: {e}")
            raise
    
    async def open_gemini(self):
        """打开 Gemini 官网"""
        print("[DEBUG] 导航到 Gemini...")
        try:
            await self.page.goto(GEMINI_URL, timeout=30000)
            await self.page.wait_for_load_state('domcontentloaded')
            print("[DEBUG] 页面加载完成")
        except Exception as e:
            print(f"[ERROR] 页面加载失败: {e}")
            raise
    
    async def close(self):
        """断开连接"""
        if self.browser:
            await self.browser.close()
            print("[DEBUG] 已断开连接")
        if self.playwright:
            await self.playwright.stop()