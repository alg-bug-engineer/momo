"""
浏览器控制器基类
"""

import asyncio
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
    
    async def connect_to_browser(self):
        """连接到已启动的 Chrome 浏览器"""
        print("[DEBUG] 连接到 Chrome 浏览器...")
        
        self.playwright = await async_playwright().start()
        
        try:
            print("[DEBUG] 连接 CDP 端点...")
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