# MacOS Shot Finder（适配 macOS 10.14）



## 隐私与联网说明（非常重要）

- 默认是**本地离线处理**：视频帧提取、镜头分析、演员识别、特效识别、检索都在本机完成。
- 代码已默认开启离线模式（`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`），不会主动联网下载模型。
- 这意味着：如果你本机还没有模型，会提示模型缺失，而不是自动上传视频或上传素材。

建议：生产环境中可直接断网使用，进一步确保素材安全。

---
## 核心能力（已增强）

1. 导入视频并自动切镜头。
2. 输出每个镜头缩略图 + 时间点。
3. 台词转写检索（可选，依赖 faster-whisper）。
4. 演员识别检索（参考图建库 + 多帧聚合）。
5. 特效检索（爆炸/科幻/烟雾/运动模糊 + 分数）。
6. 混合检索排序（语义向量 + TF-IDF + 演员/特效加权）。

---

## 一、快速开始

```bash
git clone <你的仓库地址> FileConverter
cd FileConverter
./quick_start_macos.sh
```

---

## 二、演员识别（高精度）

在你的 project 目录下放演员样本图：

```text
<project>/actors/
  ├── actor_张三/
  │    ├── 1.jpg
  │    └── 2.jpg
  └── actor_李四/
       ├── 1.jpg
       └── 2.jpg
```

建议每位演员至少放 5~20 张清晰正脸图。

---

## 三、命令行

### 高精度索引（默认）

```bash
python src/cli.py index --video /path/a.mp4 --project ./workspace/demo
```

### 快速索引（速度优先）

```bash
python src/cli.py index --video /path/a.mp4 --project ./workspace/demo --fast
```

### 检索

```bash
python src/cli.py search --project ./workspace/demo --query "actor_张三 爆炸 低角度"
```

---

## 四、GUI

```bash
python src/app.py
```

- 可勾选“高精度模式”后再建索引。
- 结果会显示：总分、语义分、关键词分、加权分、演员分数、特效分数。

---

## 五、打包安装包（dmg）

```bash
cd MacOSShotFinder
./build_macos_installer.sh
```

产物：

```text
MacOSShotFinder/release/MacOSShotFinder-macOS10.14.dmg
```

