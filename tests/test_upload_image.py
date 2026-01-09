#!/usr/bin/env python3
"""
单独测试图片上传功能
只执行到图片上传完成就终止
"""

#!/usr/bin/env python3
"""
单独测试图片上传功能
只执行到图片上传完成就终止
"""

import asyncio
import sys
import os
from pathlib import Path

# 确保可以导入项目模块
# 方法1: 尝试添加项目根目录到路径
project_root = Path(__file__).parent.parent  # tests目录的上级目录是项目根目录
sys.path.insert(0, str(project_root))

# 方法2: 尝试设置PYTHONPATH环境变量
if str(project_root) not in os.environ.get('PYTHONPATH', '').split(':'):
    os.environ['PYTHONPATH'] = f"{str(project_root)}:{os.environ.get('PYTHONPATH', '')}"

# 尝试导入
try:
    from src.core.auto_manga_workflow import AutoMangaWorkflow
except ImportError as e:
    print(f"导入失败: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python路径: {sys.path}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
    sys.exit(1)


async def debug_page_structure(workflow: AutoMangaWorkflow):
    """调试:打印页面上传相关元素的结构"""
    print("\n" + "="*80)
    print("调试信息:页面元素结构")
    print("="*80)
    
    # 1. 查找所有文件输入框
    all_inputs = await workflow.page.query_selector_all('input[type="file"]')
    print(f"\n[DEBUG] 文件输入框数量: {len(all_inputs)}")
    
    for i, inp in enumerate(all_inputs):
        try:
            html = await inp.evaluate("el => el.outerHTML")
            parent_html = await inp.evaluate("el => el.parentElement?.outerHTML.substring(0, 200)")
            is_visible = await inp.is_visible()
            is_disabled = await inp.get_attribute('disabled')
            print(f"\n输入框 {i}:")
            print(f"  可见: {is_visible}, 禁用: {is_disabled}")
            print(f"  HTML: {html[:200]}")
            print(f"  父元素: {parent_html}")
        except Exception as e:
            print(f"  [ERROR] 无法获取信息: {e}")
    
    # 2. 查找上传按钮的完整 HTML
    try:
        from src.config.settings import SELECTORS
        upload_btn = await workflow.page.query_selector(SELECTORS["upload_button"][0])
        if upload_btn:
            html = await upload_btn.evaluate("el => el.outerHTML")
            print(f"\n[DEBUG] 上传按钮 HTML:\n{html[:300]}")
    except Exception as e:
        print(f"[DEBUG] 无法获取上传按钮: {e}")
    
    # 3. 查找所有包含 "upload" 的元素
    try:
        upload_elements = await workflow.page.query_selector_all('[class*="upload"], [data-test-id*="upload"]')
        print(f"\n[DEBUG] 找到 {len(upload_elements)} 个包含 'upload' 的元素")
    except Exception as e:
        print(f"[DEBUG] 查找 upload 元素失败: {e}")
    
    print("="*80 + "\n")


async def test_upload_image():
    """主测试函数"""
    workflow = AutoMangaWorkflow()
    
    try:
        # 步骤1: 连接浏览器并打开 Gemini
        print("\n" + "="*80)
        print("步骤1: 连接浏览器并打开 Gemini")
        print("="*80)
        await workflow.connect_to_browser()
        await workflow.open_gemini()
        await asyncio.sleep(3)  # 等待页面完全加载
        
        # 步骤2: 选择 Create Images 工具(如果需要)
        print("\n" + "="*80)
        print("步骤2: 选择 Create Images 工具(可选)")
        print("="*80)
        try:
            await workflow.select_create_images_tool()
            await asyncio.sleep(1)
            print("[INFO] ✓ 已选择 Create Images 工具")
        except Exception as e:
            print(f"[INFO] 跳过工具选择: {e}")
        
        # 步骤3: 测试上传图片
        print("\n" + "="*80)
        print("步骤3: 测试上传 assets/samples/demo.png")
        print("="*80)
        
        # 运行调试检查
        print("[INFO] 运行调试检查...")
        await debug_page_structure(workflow)
        
        # 执行上传
        await workflow.upload_image("assets/samples/demo.png")
        
        print("\n" + "="*80)
        print("✓✓✓ 图片上传测试完全成功! ✓✓✓")
        print("="*80)
        
        # 保持浏览器打开,方便查看结果
        print("\n[INFO] 保持浏览器打开 15 秒,方便查看上传结果...")
        await asyncio.sleep(15)
        
    except Exception as e:
        print(f"\n[ERROR] 测试过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[INFO] 测试完成,浏览器将保持打开状态")
        print("[INFO] 请手动检查页面,确认上传结果")
        # 不关闭浏览器,让用户手动查看
        # await workflow.close()


if __name__ == '__main__':
    asyncio.run(test_upload_image())