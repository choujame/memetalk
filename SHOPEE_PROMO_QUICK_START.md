# 🎯 Shopee 促销图片生成 - 快速开始

## 📋 已准备的文件

脚本和输入文件已为您准备好：

```
memetalk/
├── shopee_promo_image_script.py    # 主脚本
├── input_file_12.jpeg               # 洗衣球产品合照 ✅
├── input_file_16.jpeg               # 蝦皮後台截圖 ✅
└── SHOPEE_PROMO_SCRIPT_README.md    # 详细文档
```

## 🚀 快速运行

### 方法 1: 本地计算机上运行（推荐）

**第 1 步: 安装依赖**
```bash
pip install Pillow
```

**第 2 步: 运行脚本**
```bash
cd /path/to/memetalk
python shopee_promo_image_script.py
```

**第 3 步: 检查输出**
```bash
ls -lh shopee_promo.png
```

### 方法 2: 使用绝对路径指定文件

```bash
python shopee_promo_image_script.py \
  /home/user/memetalk/input_file_12.jpeg \
  /home/user/memetalk/input_file_16.jpeg \
  /home/user/memetalk/shopee_promo.png
```

## 📊 脚本功能一览

这个脚本会自动生成一张**1080x1920 像素**（9:16 移动端比例）的促销海报，包含：

```
┌────────────────────────────────────┐
│   ✨ 促销海报布局                    │
├────────────────────────────────────┤
│                                    │
│    🧺 P&G 洗衣球产品合照             │ 
│                                    │
│  📝 日本 P&G 4D 洗衣球               │ (黄色)
│     箱購免運                         │
│                                    │
├────────────────────────────────────┤
│                                    │
│  🏷️  社群限定 9.3 折優惠券！         │ (红色)
│         ↗️ [後台截圖]                │
│      (促销信息区块)                 │
│                                    │
├────────────────────────────────────┤
│                                    │
│  👇 點擊下方連結領券購買 👇           │ (白色)
│                                    │
└────────────────────────────────────┘
```

## 🎨 设计特点

✅ **蝦皮品牌色** - 使用官方橘色 (#FF5722) 背景  
✅ **自动排版** - 根据图片尺寸自动调整缩放  
✅ **中文支持** - 完整支持繁体中文  
✅ **描边效果** - 所有文字都有黑色描边确保清晰  
✅ **指向箭头** - 红色箭头指向促销信息区块  
✅ **手机优化** - 完美适配 Instagram Stories、TikTok 等竖版格式  

## ⚙️ 命令行选项

```bash
# 使用默认文件名（必须在同一目录）
python shopee_promo_image_script.py

# 自定义输入和输出文件
python shopee_promo_image_script.py [产品图片] [後台截圖] [输出文件]

# 示例：
python shopee_promo_image_script.py \
  my_products.jpg \
  shopee_screenshot.png \
  final_promo.png
```

## 🔧 系统需求

- **Python**: 3.8 或更高版本
- **依赖包**: Pillow >= 11.0

## 📦 生成的文件

- **文件名**: `shopee_promo.png`
- **格式**: PNG (RGB)
- **尺寸**: 1080 × 1920 像素 (9:16)
- **文件大小**: 约 200-500 KB（取决于输入图片）

## ✨ 输出质量

生成的图片采用高质量导出（质量 = 95），适合：
- 📱 社交媒体分享（Instagram、TikTok、Facebook）
- 🖼️ 打印和广告素材
- 📧 邮件营销
- 💬 即时通讯应用分享

## 🐛 常见问题

**Q: 脚本报错找不到文件？**  
A: 确保 `input_file_12.jpeg` 和 `input_file_16.jpeg` 与脚本在同一目录，或使用绝对路径。

**Q: 文字显示不出来或乱码？**  
A: 可能是系统缺少中文字体。在 Ubuntu/Debian 上安装：
```bash
apt-get install fonts-noto-cjk
```

**Q: 可以修改文字颜色或背景色吗？**  
A: 可以！编辑脚本中的这些行：
```python
shopee_orange = (255, 87, 34)  # 背景色 (RGB)
fill=(255, 255, 0)              # 黄色文字
fill=(255, 0, 0)                # 红色文字
fill=(255, 255, 255)            # 白色文字
```

**Q: 生成的图片效果不满意？**  
A: 可以调整的参数：
- 输入图片分辨率（越高越好）
- 文字大小（编辑 `font_title`, `font_subtitle` 等）
- 排版比例（编辑 `product_height`, `backend_height` 等）

## 📝 输入文件说明

### input_file_12.jpeg（洗衣球产品合照）
- 应显示 P&G 4D 洗衣球的各种款式
- 推荐尺寸：1000x1000 px 或更大
- 将占用海报的上方 35% 区域

### input_file_16.jpeg（蝦皮後台截圖）
- 应显示商品页面的关键信息
- 理想情况包含：9.3 折、10.5% 分潤加碼、已售出 7,000+ 等
- 推荐尺寸：1080x400 px 或更大
- 将占用海报的中间 25% 区域

## 🎬 下一步

1. ✅ 准备好输入文件（已完成！）
2. 📦 在本地环境安装 Pillow
3. 🎨 运行脚本生成海报
4. 👀 检查输出效果
5. 📤 分享到社交媒体或用于广告

## 📞 技术支持

详细的脚本文档请参考：`SHOPEE_PROMO_SCRIPT_README.md`

脚本代码完全开源，可自由修改以适应您的需求！

---

**版本**: 1.0  
**最后更新**: 2026-06-30  
**开发语言**: Python 3.8+  
**必需库**: Pillow >= 11.0
