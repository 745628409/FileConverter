# MacOS Shot Finder（适配 macOS 10.14）


## 零、先确认你下载的是“完整项目”

如果终端提示 `No such file or directory`，通常是你当前目录不对，或者还没下载完整项目。

### 最稳妥步骤（复制执行）

```bash
# 1) 下载源码（示例）
git clone <你的仓库地址> FileConverter

# 2) 进入仓库根目录
cd FileConverter

# 3) 看看目录里有没有 MacOSShotFinder
ls

# 4) 一键启动（推荐）
./quick_start_macos.sh
```

如果第 3 步 `ls` 看不到 `MacOSShotFinder`，那就是下载内容不完整（或路径进错了）。

---

你要的“安装包”方案我已经补上了：可直接生成 `dmg`，双击后拖到 `Applications` 安装。

---

## 一、给最终用户（拿到安装包后）

1. 双击 `MacOSShotFinder-macOS10.14.dmg`
2. 把 `MacOSShotFinder.app` 拖进 `Applications`
3. 第一次打开如果被 Gatekeeper 拦截：
   - 系统设置 → 安全性与隐私 → 仍要打开

---

## 二、给你（如何自己打安装包）

### 1) 环境要求

- macOS 10.14+
- Python 3.8+
- ffmpeg / ffprobe（`brew install ffmpeg`）

### 2) 执行一键打包脚本

```bash
cd MacOSShotFinder
chmod +x build_macos_installer.sh
./build_macos_installer.sh
```

### 3) 打包产物

完成后安装包在：

```bash
MacOSShotFinder/release/MacOSShotFinder-macOS10.14.dmg
```

---

## 三、开发/调试启动

```bash
cd MacOSShotFinder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/app.py
```

---

## 四、支持的能力（当前版本）

- 导入视频并自动切镜头
- 每个镜头提取缩略图 + 时间点
- 可选台词转写（faster-whisper）
- 检索：支持“叙事台词 / 景别 / 角度 / 光影 / 动作段落”等关键词或自然语言

> 说明：
> - “演员级识别”“高精度特效分类”需要加专门模型，可在 `src/pipeline.py` 的 `build_feature_text` 和标签阶段继续扩展。


---

## 五、常见报错

### `-bash: cd: MacOSShotFinder: No such file or directory`

这表示你当前所在目录里没有 `MacOSShotFinder` 文件夹。可以这样做：

```bash
# 先进入 FileConverter 仓库根目录
cd /你的路径/FileConverter

# 再进入子目录
cd MacOSShotFinder
```

或者直接用仓库根目录的一键脚本（推荐）：

```bash
cd /你的路径/FileConverter
./build_shotfinder_dmg.sh
```

如果你不确定当前目录，可先执行：

```bash
pwd
ls
```
