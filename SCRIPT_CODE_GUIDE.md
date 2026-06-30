# 📘 Shopee 促销图片脚本代码解析

本文档详细说明脚本的结构和各个函数的作用，供进阶用户参考和定制。

## 🗂️ 脚本文件结构

```
shopee_promo_image_script.py
├── 导入库
├── create_arrow()          # 绘制箭头的函数
├── get_font()              # 获取中文字体的函数
├── create_shopee_promo()   # 核心函数（生成海报）
└── __main__ 块             # 命令行入口
```

## 🔍 核心函数详解

### 1. `create_arrow(draw, start_x, start_y, end_x, end_y, color, width)`

**用途**: 在图片上绘制指向箭头

**参数**:
- `draw`: PIL ImageDraw 对象
- `start_x`, `start_y`: 箭头起点坐标
- `end_x`, `end_y`: 箭头终点坐标
- `color`: 箭头颜色 (RGB 元组或十六进制字符串)，默认红色 `"#FF0000"`
- `width`: 箭头线宽，默认 8 像素

**原理**:
```
步骤 1: 计算箭头方向向量
步骤 2: 绘制主线（从起点到终点）
步骤 3: 绘制三角形箭头头部（三个顶点构成）
```

**示例修改**:
```python
# 改变箭头颜色为绿色
create_arrow(draw, 100, 100, 500, 500, color=(0, 255, 0), width=10)

# 改变箭头宽度为 15
create_arrow(draw, start_x, start_y, end_x, end_y, width=15)
```

### 2. `get_font(size, font_path=None)`

**用途**: 获取合适的 TTF 字体用于绘制中文文本

**参数**:
- `size`: 字体大小（像素）
- `font_path`: 自定义字体路径（可选）

**返回**: PIL Font 对象

**工作流程**:
```
1️⃣  如果提供了 font_path 且存在，使用该字体
2️⃣  否则，尝试预设的常见中文字体路径：
    - /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc (Linux)
    - /System/Library/Fonts/PingFang.ttc (macOS)
    - C:\\Windows\\Fonts\\msyh.ttc (Windows)
3️⃣  如果都不存在，使用系统默认字体
```

**自定义字体**:
```python
# 在脚本主函数中指定自定义字体
font_title = get_font(72, "/path/to/your/font.ttf")
```

**支持的字体格式**: `.ttf`, `.ttc`, `.otf`

### 3. `create_shopee_promo()` - 核心主函数

**签名**:
```python
def create_shopee_promo(
    product_image_path,      # 产品图片路径
    backend_image_path,      # 後台截圖路径
    output_path="shopee_promo.png",  # 输出路径
    width=1080,              # 画布宽度
    height=1920              # 画布高度（9:16 比例）
)
```

**执行步骤**:

#### 步骤 1: 创建基础背景
```python
background = Image.new("RGB", (width, height), shopee_orange)
draw = ImageDraw.Draw(background)
```
- 创建 1080×1920 的 RGB 图像
- 蝦皮橘色 RGB(255, 87, 34) 填充

#### 步骤 2: 加载和处理产品图片
```python
product_img = Image.open(product_image_path).convert("RGBA")

# 计算缩放比例（占 35% 高度）
product_height = int(height * 0.35)  # 672 像素
ratio = product_height / product_img.height
product_width = int(product_img.width * ratio)

# 调整大小并居中放置
product_img = product_img.resize((product_width, product_height))
product_x = (width - product_width) // 2
product_y = 80
```

#### 步骤 3: 添加标题文字（黄色 + 描边）
```python
# 黄色 RGB(255, 255, 0)
draw.text((...), "日本 P&G 4D 洗衣球", 
          font=font_title, fill=(255, 255, 0))
```

**描边实现**:
```python
# 先绘制黑色阴影（9 个位置）
for offset_x in [-3, -2, -1, 0, 1, 2, 3]:
    for offset_y in [-3, -2, -1, 0, 1, 2, 3]:
        draw.text((...), text, fill=(0, 0, 0))

# 再在正中心绘制彩色文字
draw.text((...), text, fill=(255, 255, 0))
```

#### 步骤 4: 加载和处理後台截圖
```python
backend_img = Image.open(backend_image_path).convert("RGB")

# 计算缩放比例（占 25% 高度）
backend_height = int(height * 0.25)  # 480 像素
backend_y = int(height * 0.58)       # 中间位置
```

#### 步骤 5: 绘制指向箭头
```python
create_arrow(draw, 
    start_x=width // 2 - 200,
    start_y=backend_y - 150,
    end_x=width // 2,
    end_y=backend_y + 20,
    color=(255, 0, 0),  # 红色
    width=12)
```

#### 步骤 6: 添加促销文字（红色）
```python
promo_text = "社群限定 9.3 折優惠券！"
draw.text((...), promo_text, fill=(255, 0, 0))
```

#### 步骤 7: 添加引导文字（白色）
```python
cta_text = "點擊下方連結領券購買 👇"
draw.text((...), cta_text, fill=(255, 255, 255))
```

#### 步骤 8: 保存输出
```python
background.save(output_path, "PNG", quality=95)
```

## 🎨 颜色参考

| 用途 | 颜色名称 | RGB 值 | 十六进制 |
|------|----------|--------|---------|
| 背景 | 蝦皮橘 | (255, 87, 34) | #FF5722 |
| 标题 | 纯黄 | (255, 255, 0) | #FFFF00 |
| 促销 | 纯红 | (255, 0, 0) | #FF0000 |
| 引导 | 纯白 | (255, 255, 255) | #FFFFFF |
| 描边 | 纯黑 | (0, 0, 0) | #000000 |

## 📐 尺寸和比例参考

| 元素 | 比例 | 绝对值 (1080x1920) |
|------|------|-------------------|
| 产品图片高度 | 35% | 672 px |
| 标题距顶部 | 上方 + 35% | ~752 px |
| 促销文字距顶部 | 48% | 921 px |
| 後台图片距顶部 | 58% | 1113 px |
| 後台图片高度 | 25% | 480 px |
| 引导文字距底部 | 150 px | 1770 px |

## 🔧 常见定制方案

### 方案 1: 改变背景色

```python
# 原始
shopee_orange = (255, 87, 34)

# 改为蓝色
shopee_blue = (33, 150, 243)
background = Image.new("RGB", (width, height), shopee_blue)
```

### 方案 2: 改变文字大小和位置

```python
# 在 create_shopee_promo() 中修改字体大小
font_title = get_font(92)  # 从 72 改为 92
font_subtitle = get_font(68)  # 从 56 改为 68
font_promotion = get_font(88)  # 从 68 改为 88
font_cta = get_font(56)  # 从 48 改为 56
```

### 方案 3: 改变图片占用的高度比例

```python
# 产品图片占 40%（默认 35%）
product_height = int(height * 0.40)

# 後台图片占 30%（默认 25%）
backend_height = int(height * 0.30)
```

### 方案 4: 改变图片位置（例如不居中）

```python
# 产品图片靠左对齐
product_x = 50  # 而不是 (width - product_width) // 2

# 後台图片靠右对齐
backend_x = width - backend_width - 50
```

### 方案 5: 添加新的文本元素

```python
# 在保存前添加（如版权信息）
font_small = get_font(24)
draw.text(
    (width - 200, height - 40),
    "© 2026 YourBrand",
    font=font_small,
    fill=(255, 255, 255),
    anchor="rm"  # 右下对齐
)
```

## 🐛 调试技巧

### 打印调试信息

编辑脚本主函数，添加：

```python
print(f"背景尺寸: {width}x{height}")
print(f"产品图片原尺寸: {product_img.width}x{product_img.height}")
print(f"产品图片目标尺寸: {product_width}x{product_height}")
print(f"产品位置: ({product_x}, {product_y})")
```

### 逐步生成测试版本

创建多个输出来测试每个步骤：

```python
# 在步骤 2 后保存一次
background.save("test_step2.png")

# 在步骤 5 后保存一次
background.save("test_step5.png")

# 最后保存完整版
background.save(output_path)
```

## 💡 高级技巧

### 技巧 1: 支持多种图片格式

脚本已支持 JPEG 和 PNG，代码中：
```python
product_img = Image.open(product_image_path).convert("RGBA")
```

可以进一步支持其他格式，如 WebP、GIF 等。

### 技巧 2: 添加图片滤镜

```python
from PIL import ImageFilter, ImageEnhance

# 增加对比度
enhancer = ImageEnhance.Contrast(product_img)
product_img = enhancer.enhance(1.2)

# 添加高斯模糊背景（仅示例）
product_img = product_img.filter(ImageFilter.GaussianBlur(radius=2))
```

### 技巧 3: 动态文字大小

根据文字长度自动调整字体大小：

```python
def get_dynamic_font_size(text_length, max_width):
    # 简单算法：根据文字长度和最大宽度计算合适的字体大小
    return max_width // (text_length * 0.7)
```

### 技巧 4: 批处理多张图片

```python
import os
from pathlib import Path

image_dir = "images/"
for product_file in Path(image_dir).glob("*.jpg"):
    create_shopee_promo(
        str(product_file),
        "backend_template.png",
        f"output_{product_file.stem}.png"
    )
```

## 📚 PIL 文档参考

关键的 PIL 类和方法：

- `Image.open(path)` - 打开图像文件
- `Image.new(mode, size, color)` - 创建新图像
- `.convert(mode)` - 转换颜色模式（RGBA、RGB 等）
- `.resize(size, resample)` - 调整大小
- `.save(file, format, quality)` - 保存文件
- `ImageDraw.Draw(image)` - 创建绘制对象
- `.text(xy, text, font, fill)` - 绘制文本
- `.line(xy, fill, width)` - 绘制直线
- `.polygon(xy, fill)` - 绘制多边形

## 🎓 学习资源

- [Pillow 官方文档](https://pillow.readthedocs.io/)
- [Python 图像处理教程](https://docs.python-guide.org/scenarios/imaging/)
- [PIL 中文字体指南](https://zhuanlan.zhihu.com/p/86235318)

---

**版本**: 1.0  
**难度级别**: 中级 (需要 Python 基础)  
**更新日期**: 2026-06-30
