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

## 三、演员识别（新增）

为了识别“某个演员镜头”，请在项目目录准备演员样本：

```text
<你的project目录>/actors/
  ├── actor_张三/
  │    ├── 1.jpg
  │    └── 2.jpg
  ├── actor_李四/
  │    ├── 1.jpg
  │    └── 2.jpg
```

然后重新执行 `index`。检索时可直接搜演员名，比如：
- `actor_张三 近景 反应镜头`
- `actor_李四 台词`

---

## 四、特效检索（新增）

当前已支持的特效标签：
- 火焰/爆炸特效
- 冷色科幻特效
- 烟雾/雾化特效
- 运动模糊/高速运动

可直接搜索：
- `爆炸 特效 动作段落`
- `烟雾 低角度`
- `科幻 蓝光`

---

## 五、检索准确度增强（新增）

当前检索采用**混合排序**，不再只看语义向量：
1. 语义向量相似度（sentence-transformers）
2. 关键词 TF-IDF 相似度
3. 结构化加权（演员命中/特效命中/关键词命中）

这样对“演员 + 特效 + 镜头语义”的组合查询准确度更高。

---

## 六、开发/调试启动

```bash
cd MacOSShotFinder
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/app.py
```
