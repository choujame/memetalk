#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shopee 促销图片自动化生成脚本
创建 9:16 比例的促销海报，展示 P&G 4D 洗衣球的优惠信息
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path


def create_arrow(draw, start_x, start_y, end_x, end_y, color="#FF0000", width=8):
    """
    绘制手绘风格箭头
    """
    # 绘制主线
    draw.line([(start_x, start_y), (end_x, end_y)], fill=color, width=width)

    # 绘制箭头头部（三角形）
    arrow_size = 30
    dx = end_x - start_x
    dy = end_y - start_y
    length = (dx**2 + dy**2)**0.5

    if length > 0:
        # 单位向量
        ux, uy = dx / length, dy / length
        # 垂直向量
        px, py = -uy, ux

        # 箭头三个顶点
        p1 = (end_x, end_y)
        p2 = (end_x - ux * arrow_size - px * arrow_size/2,
              end_y - uy * arrow_size - py * arrow_size/2)
        p3 = (end_x - ux * arrow_size + px * arrow_size/2,
              end_y - uy * arrow_size + py * arrow_size/2)

        draw.polygon([p1, p2, p3], fill=color)


def get_font(size, font_path=None):
    """
    获取 TTF 字体，如果系统中有中文字体
    """
    if font_path and os.path.exists(font_path):
        return ImageFont.truetype(font_path, size)

    # 尝试常见的中文字体路径
    font_candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttf",
        "/System/Library/Fonts/PingFang.ttc",  # macOS
        "C:\\Windows\\Fonts\\msyh.ttc",  # Windows
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

    # 默认字体
    try:
        return ImageFont.load_default()
    except:
        return None


def create_shopee_promo(
    product_image_path,
    backend_image_path,
    output_path="shopee_promo.png",
    width=1080,
    height=1920
):
    """
    创建 Shopee 促销图片

    Args:
        product_image_path: 洗衣球合照路径 (input_file_12.jpeg)
        backend_image_path: 蝦皮後台截圖路径 (input_file_16.jpeg)
        output_path: 输出文件路径
        width: 图片宽度 (像素)
        height: 图片高度 (像素，9:16 比例)
    """

    # 1. 创建背景 (蝦皮橘色)
    print("📸 创建背景...")
    shopee_orange = (255, 87, 34)  # #FF5722
    background = Image.new("RGB", (width, height), shopee_orange)
    draw = ImageDraw.Draw(background)

    # 2. 加载并处理产品图片（洗衣球）
    print(f"📦 加载产品图片: {product_image_path}")
    if not os.path.exists(product_image_path):
        print(f"⚠️  警告: 产品图片不存在 {product_image_path}")
        product_img = None
    else:
        product_img = Image.open(product_image_path).convert("RGBA")

        # 调整产品图片大小 (上方区域，约占 1/3)
        product_height = int(height * 0.35)
        ratio = product_height / product_img.height
        product_width = int(product_img.width * ratio)
        product_img = product_img.resize((product_width, product_height), Image.Resampling.LANCZOS)

        # 居中放置
        product_x = (width - product_width) // 2
        product_y = 80

        # 转换为 RGB 并粘贴
        product_rgb = Image.new("RGB", (product_width, product_height), shopee_orange)
        product_rgb.paste(product_img, (0, 0), product_img)
        background.paste(product_rgb, (product_x, product_y))
        print(f"✅ 产品图片已放置: 位置 ({product_x}, {product_y})")

    # 3. 添加产品标题文字 (黄色)
    print("✏️  添加产品标题...")
    font_title = get_font(72)
    title_text = "日本 P&G 4D 洗衣球"
    subtitle_text = "箱購免運"

    # 绘制标题，使用白色描边效果
    title_y = product_y + int(height * 0.35) + 30

    # 标题描边
    for offset_x in [-3, -2, -1, 0, 1, 2, 3]:
        for offset_y in [-3, -2, -1, 0, 1, 2, 3]:
            if offset_x != 0 or offset_y != 0:
                draw.text(
                    (width//2 + offset_x, title_y + offset_y),
                    title_text,
                    font=font_title,
                    fill=(0, 0, 0),
                    anchor="mm"
                )

    # 标题主文本 (黄色)
    draw.text(
        (width//2, title_y),
        title_text,
        font=font_title,
        fill=(255, 255, 0),  # 黄色
        anchor="mm"
    )

    # 副标题
    font_subtitle = get_font(56)
    subtitle_y = title_y + 100

    for offset_x in [-2, -1, 0, 1, 2]:
        for offset_y in [-2, -1, 0, 1, 2]:
            if offset_x != 0 or offset_y != 0:
                draw.text(
                    (width//2 + offset_x, subtitle_y + offset_y),
                    subtitle_text,
                    font=font_subtitle,
                    fill=(0, 0, 0),
                    anchor="mm"
                )

    draw.text(
        (width//2, subtitle_y),
        subtitle_text,
        font=font_subtitle,
        fill=(255, 255, 0),  # 黄色
        anchor="mm"
    )

    # 4. 加载并处理後台截圖
    print(f"📊 加载後台截圖: {backend_image_path}")
    if not os.path.exists(backend_image_path):
        print(f"⚠️  警告: 後台截圖不存在 {backend_image_path}")
        backend_img = None
    else:
        backend_img = Image.open(backend_image_path).convert("RGB")

        # 调整後台截圖大小 (中间区域)
        backend_height = int(height * 0.25)
        ratio = backend_height / backend_img.height
        backend_width = int(backend_img.width * ratio)
        backend_img = backend_img.resize((backend_width, backend_height), Image.Resampling.LANCZOS)

        # 居中放置
        backend_x = (width - backend_width) // 2
        backend_y = int(height * 0.58)

        background.paste(backend_img, (backend_x, backend_y))
        print(f"✅ 後台截圖已放置: 位置 ({backend_x}, {backend_y})")

        # 5. 绘制红色箭头指向後台截圖
        print("🎯 添加指向箭头...")
        arrow_start_x = width // 2 - 200
        arrow_start_y = backend_y - 150
        arrow_end_x = width // 2
        arrow_end_y = backend_y + 20

        create_arrow(draw, arrow_start_x, arrow_start_y, arrow_end_x, arrow_end_y,
                    color=(255, 0, 0), width=12)

    # 6. 添加优惠文字 (红色大字)
    print("🏷️  添加优惠文字...")
    font_promotion = get_font(68)
    promo_text = "社群限定 9.3 折優惠券！"
    promo_y = int(height * 0.48)

    # 添加描边效果
    for offset_x in [-3, -2, -1, 0, 1, 2, 3]:
        for offset_y in [-3, -2, -1, 0, 1, 2, 3]:
            if offset_x != 0 or offset_y != 0:
                draw.text(
                    (width//2 + offset_x, promo_y + offset_y),
                    promo_text,
                    font=font_promotion,
                    fill=(0, 0, 0),
                    anchor="mm"
                )

    # 主文本 (红色)
    draw.text(
        (width//2, promo_y),
        promo_text,
        font=font_promotion,
        fill=(255, 0, 0),  # 红色
        anchor="mm"
    )

    # 7. 添加底部引导文字
    print("👇 添加引导文字...")
    font_cta = get_font(48)
    cta_text = "點擊下方連結領券購買 👇"
    cta_y = height - 150

    # 描边
    for offset_x in [-2, -1, 0, 1, 2]:
        for offset_y in [-2, -1, 0, 1, 2]:
            if offset_x != 0 or offset_y != 0:
                draw.text(
                    (width//2 + offset_x, cta_y + offset_y),
                    cta_text,
                    font=font_cta,
                    fill=(255, 255, 255),
                    anchor="mm"
                )

    # 主文本 (白色)
    draw.text(
        (width//2, cta_y),
        cta_text,
        font=font_cta,
        fill=(255, 255, 255),
        anchor="mm"
    )

    # 8. 保存输出
    print(f"💾 保存输出: {output_path}")
    background.save(output_path, "PNG", quality=95)
    print(f"✨ 完成! 促销图片已生成: {output_path}")
    print(f"   尺寸: {width}x{height} (9:16 比例)")

    return output_path


if __name__ == "__main__":
    import sys

    # 默认文件路径
    input_product = "input_file_12.jpeg"
    input_backend = "input_file_16.jpeg"
    output_file = "shopee_promo.png"

    # 允许命令行参数覆盖
    if len(sys.argv) > 1:
        input_product = sys.argv[1]
    if len(sys.argv) > 2:
        input_backend = sys.argv[2]
    if len(sys.argv) > 3:
        output_file = sys.argv[3]

    # 检查输入文件
    print("🚀 Shopee 促销图片生成脚本")
    print("=" * 50)
    print(f"产品图片: {input_product}")
    print(f"後台截圖: {input_backend}")
    print(f"输出文件: {output_file}")
    print("=" * 50)

    # 创建促销图片
    try:
        create_shopee_promo(input_product, input_backend, output_file)
        print("\n✅ 成功!")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
