# 公众号封面生成 Skill

根据文章标题和正文生成微信公众号封面，提供手绘社论漫画、电影级写实科技两种风格，输出比例为 **2.35:1**。

## 使用

将本仓库下载为 `editorial-cover` 文件夹，放入 Codex 的 `~/.codex/skills/`，在新聊天中调用 `$editorial-cover`。

提供文章标题、正文与风格；写实风还可提供希望显示在封面上的文字。未提供封面文字时默认无字。需要边框时，指定资讯手绘、资讯极简或实测边框。

```text
使用 $editorial-cover 生成手绘风封面，添加资讯手绘边框。
文章标题：……
文章正文：……
```

```text
使用 $editorial-cover 生成写实风封面。
封面文字：……
文章标题：……
文章正文：……
```

图片由运行环境的图像生成能力制作；本仓库提供风格提示词、调用流程与边框合成脚本。需要可用的图像生成工具。

## 边框合成

需要 Python 3 和 Pillow。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
python3 scripts/compose_cover.py --input generated.png --border news-handdrawn --output cover-bordered.png --plain-output cover.png
```

一次调用 Skill 即自动连续完成生图、框内适配与加框，无需再次发出加框指令。脚本也只需运行一次，同时保存无边框与加框版。

加框时自动识别各款边框内部开口，默认等比铺满整个框内开口，裁切超出部分，不额外添加内边距；框外使用协调底色，避免主体越过边框。生图时在标识位置预留背景，主体保持在安全区域。只有明确接受留白并希望保留整张原图时使用 `--fit contain`。

可用边框参数为 `news-handdrawn`、`news-minimal`、`review`。默认输出 1880×800 PNG，保留原图，已有输出文件不会被覆盖。

## 文件

- `SKILL.md`：Skill 调用说明。
- `references/`：两份原始 Word、逐字提取的提示词和校验值。
- `assets/borders/`：三款原始透明边框。
- `scripts/`：图片比例规范与边框叠加脚本。
- `agents/`：Skill 显示信息。
- `gallery/`：手绘风作品展示。

原始提示词完整保留；本次文章内容及可选封面文字在调用时另行附加。

## 手绘风作品展示


### AI 科普动画工作室

![AI 科普动画工作室](gallery/example-01.png)

### AI星球正面碰撞，观众吃爆米花

![AI星球正面碰撞，观众吃爆米花](gallery/example-02.png)

### Fable与GPT太空对决

![Fable与GPT太空对决](gallery/example-04.png)

### WorkBuddy科学视频工坊

![WorkBuddy科学视频工坊](gallery/example-05.png)

### 国模一哥争夺战

![国模一哥争夺战](gallery/example-06.png)

### 星际碰撞与爆米花观众

![星际碰撞与爆米花观众](gallery/example-07.png)

### 深度对决：锦鲤池畔胜负局

![深度对决：锦鲤池畔胜负局](gallery/example-08.png)
