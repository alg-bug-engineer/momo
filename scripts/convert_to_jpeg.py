#!/usr/bin/env python3
"""
将 data/images 目录下所有图片转换为 JPEG 格式，减小文件大小
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("错误: 需要安装 Pillow 库")
    print("请运行: pip install Pillow")
    sys.exit(1)

# 支持的图片格式
SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff', '.tif'}


def convert_image_to_jpeg(input_path: Path, output_path: Path, quality: int = 85):
    """
    将图片转换为 JPEG 格式
    
    Args:
        input_path: 输入图片路径
        output_path: 输出 JPEG 路径
        quality: JPEG 质量 (1-100)，默认 85
    """
    try:
        with Image.open(input_path) as img:
            # 如果图片有透明通道，转换为 RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存为 JPEG
            img.save(output_path, 'JPEG', quality=quality, optimize=True)
            return True
    except Exception as e:
        print(f"转换失败 {input_path}: {e}", file=sys.stderr)
        return False


def convert_images_in_directory(directory: str, quality: int = 85, delete_original: bool = False):
    """
    将目录下所有图片转换为 JPEG 格式
    
    Args:
        directory: 目标目录路径
        quality: JPEG 质量 (1-100)，默认 85
        delete_original: 是否删除原始文件，默认 False
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"错误: 目录不存在: {directory}")
        return
    
    if not dir_path.is_dir():
        print(f"错误: 不是目录: {directory}")
        return
    
    # 查找所有图片文件
    image_files = []
    for ext in SUPPORTED_FORMATS:
        image_files.extend(dir_path.rglob(f'*{ext}'))
        image_files.extend(dir_path.rglob(f'*{ext.upper()}'))
    
    if not image_files:
        print(f"在 {directory} 中未找到图片文件")
        return
    
    print(f"找到 {len(image_files)} 个图片文件")
    
    converted_count = 0
    skipped_count = 0
    failed_count = 0
    total_original_size = 0
    total_new_size = 0
    
    for img_path in image_files:
        # 跳过已经是 JPEG 格式的文件
        if img_path.suffix.lower() in ('.jpg', '.jpeg'):
            print(f"跳过（已是 JPEG）: {img_path}")
            skipped_count += 1
            continue
        
        # 生成输出文件名
        output_path = img_path.with_suffix('.jpg')
        
        # 如果输出文件已存在，跳过
        if output_path.exists():
            print(f"跳过（输出文件已存在）: {img_path} -> {output_path}")
            skipped_count += 1
            continue
        
        # 获取原始文件大小
        original_size = img_path.stat().st_size
        total_original_size += original_size
        
        # 转换图片
        print(f"转换: {img_path} -> {output_path}")
        if convert_image_to_jpeg(img_path, output_path, quality):
            # 获取新文件大小
            new_size = output_path.stat().st_size
            total_new_size += new_size
            
            size_reduction = original_size - new_size
            reduction_percent = (size_reduction / original_size * 100) if original_size > 0 else 0
            
            print(f"  ✓ 完成: {original_size / 1024:.2f} KB -> {new_size / 1024:.2f} KB "
                  f"(减少 {reduction_percent:.1f}%)")
            
            converted_count += 1
            
            # 如果指定删除原始文件
            if delete_original:
                try:
                    img_path.unlink()
                    print(f"  ✓ 已删除原始文件: {img_path}")
                except Exception as e:
                    print(f"  ⚠ 删除原始文件失败: {e}", file=sys.stderr)
        else:
            failed_count += 1
    
    # 打印统计信息
    print("\n" + "="*60)
    print("转换完成统计:")
    print(f"  成功转换: {converted_count} 个文件")
    print(f"  跳过: {skipped_count} 个文件")
    print(f"  失败: {failed_count} 个文件")
    if converted_count > 0:
        total_reduction = total_original_size - total_new_size
        total_reduction_percent = (total_reduction / total_original_size * 100) if total_original_size > 0 else 0
        print(f"  原始总大小: {total_original_size / 1024 / 1024:.2f} MB")
        print(f"  新总大小: {total_new_size / 1024 / 1024:.2f} MB")
        print(f"  总减少: {total_reduction / 1024 / 1024:.2f} MB ({total_reduction_percent:.1f}%)")
    print("="*60)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='将 data/images 目录下所有图片转换为 JPEG 格式，减小文件大小'
    )
    parser.add_argument(
        '--directory', '-d',
        type=str,
        default='data/images',
        help='目标目录路径（默认: data/images）'
    )
    parser.add_argument(
        '--quality', '-q',
        type=int,
        default=85,
        choices=range(1, 101),
        metavar='1-100',
        help='JPEG 质量，1-100（默认: 85）'
    )
    parser.add_argument(
        '--delete-original',
        action='store_true',
        help='转换后删除原始文件（默认: 不删除）'
    )
    
    args = parser.parse_args()
    
    # 确保目录路径是相对于项目根目录的
    if not os.path.isabs(args.directory):
        # 获取脚本所在目录的父目录（项目根目录）
        script_dir = Path(__file__).parent
        project_root = script_dir.parent
        directory = project_root / args.directory
    else:
        directory = Path(args.directory)
    
    convert_images_in_directory(
        str(directory),
        quality=args.quality,
        delete_original=args.delete_original
    )


if __name__ == '__main__':
    main()
