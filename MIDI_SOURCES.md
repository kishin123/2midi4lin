# 2midi4lin 钢琴资源站汇总

> 本文档汇总了全网与钢琴相关的可下载资源站点，涵盖 MIDI 文件、音频录音、乐谱等类型，
> 按类别、可程序化接入难度、特征分类，用于指导下载器模块的源接入与调度策略。

## 难度标记

| 标记 | 含义 | 说明 |
|------|------|------|
| ✅ 简单 | requests 可直接爬 | 静态页面，直链下载，无需额外处理 |
| ⚠️ 中等 | 需额外处理 | 分页、简易 JS、自定义 Header、弹窗广告 |
| ❌ 困难 | 不适合程序接入 | Cloudflare、登录鉴权、接口加密、无直链 |
| 💀 已失效 | 无法访问 | 403 屏蔽、域名失效、长期超时 |

---

## 一、国内 MIDI 站点（华语流行、古风优先，中文歌名检索）

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| MidiShow | midishow.com | ⚠️ 中等 | 海量华语/动漫钢琴 MIDI，部分需积分登录 | 中文歌名 |
| 5nd 音乐网 MIDI | 5nd.com/midi | ✅ 简单 | 老牌国内 MIDI 站，大量伴奏/钢琴 MIDI | 中文歌名 |
| 虫虫钢琴网 | gangqinpu.com | ⚠️ 中等 | 钢琴谱社区，部分乐谱附带配套 MIDI | 中文歌名 + 钢琴 |
| 流行钢琴网 | popiano.org | ⚠️ 中等 | 国内老牌钢琴社区，改编钢琴 MIDI 资源 | 中文歌名 |

> **B站钢琴区**（bilibili.com）：大量 UP 主发布原创钢琴改编视频，有时在评论区或简介提供 MIDI 下载链接。非结构化源，不适合程序化搜索，但人工检索价值高。搜索建议：`曲名 + 钢琴 MIDI` 或 `曲名 + 谱`。

## 二、海外综合通用 MIDI 库（流行、影视、轻音乐通用）

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| **BitMidi** | bitmidi.com | ❌ 困难 | 全球超大 MIDI 库，支持中文搜索，**已攻克 CF** | 中英文均可 |
| **FreeMIDI.org** | freemidi.org | ✅ 简单 | 经典老牌 MIDI 归档站，**15 万+** 文件 | 英文歌名 |
| MIDIWorld | midiworld.com | ✅ 简单 | 静态页面，有 Piano 独立分类，爬虫范例多 | 英文歌名 |
| MidisFree | midisfree.com | ✅ 简单 | 轻量级站点，流行/动漫钢琴 MIDI | 英文歌名 |
| Carlo's MIDI | carlomidi.com | ⚠️ 中等 | 高质量钢琴独奏 MIDI | 英文歌名 |
| Non-Stop 2K | nonstop2k.com | ⚠️ 中等 | 现代流行、电影 OST 钢琴改编，有弹窗广告 | 英文歌名 |
| MidiDB | mididb.com | ✅ 简单 | 老牌检索站，补充冷门欧美曲目 | 英文歌名 |
| Midikaos | midikaos.com | ✅ 简单 | 复古归档，冷门老歌 MIDI，兜底用 | 英文歌名 |
| Midi Collection | midicollection.net | ✅ 简单 | 大量轻音乐、极简钢琴独奏（Yiruma / Einaudi 等） | 英文歌名 |

## 三、动漫 / 日系 / 游戏 MIDI 专项

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| **VGMusic** | vgmusic.com | ✅ 简单 | 游戏原声 MIDI 宝库，大量钢琴改编 BGM | 游戏名/动漫英文名 |
| ThePandaTooth | thepandatooth.com | ✅ 简单 | 高质量动漫、电影原声钢琴独奏 | 动漫英文名 |
| Ichigo's Sheet Music | ichigos.com | ⚠️ 中等 | 日系动漫、J-POP、吉卜力，可筛选 piano | 动漫名/日文罗马音 |
| Anison MIDI | anisonmidi.com | ✅ 简单 | 动画 OP/ED 专项 MIDI | 动漫英文名 |
| Hamienet | hamienet.com | ⚠️ 中等 | 欧美+日系影视、游戏 BGM 钢琴改编 | 英文歌名 |
| Zophar's Domain | zophar.net/midi | ✅ 简单 | 复古主机游戏 FC/SFC/PS 原生 MIDI | 游戏名称 |
| **Music is VFR** | musicisvfr.com | ⚠️ 中等 | 日系现代钢琴风格，**CC-BY 4.0 授权**，高质量人工编写 MIDI | 日文罗马音/曲名 |

## 四、古典钢琴 MIDI 专区（公版乐曲，合规性高）

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| Mutopia Project | mutopiaproject.org | ✅ 简单 | CC 授权古典乐谱 + MIDI，**可合规商用** | 作曲家、作品名 |
| Kunstderfuge | kunstderfuge.com | ✅ 简单 | 全球最大古典 MIDI 库之一，巴赫/贝多芬/肖邦/李斯特 | 作曲家、作品名 |
| **Piano-Midi.de** | piano-midi.de | ✅ 简单 | 402 首古典钢琴独奏，**已接入代码** | 作曲家、作品名 |
| Musopen | musopen.org | ⚠️ 中等 | 非营利古典音乐平台，MIDI + 录音 | 作曲家、作品名 |
| Classical MIDI Archives | classicalmidi.com | ✅ 简单 | 古典交响乐、钢琴独奏归档 | 作曲家、作品名 |
| **IMSLP** | imslp.org | ⚠️ 中等 | 全球最大公有领域乐谱库，23 万+ 作品，有 API | 作曲家、作品名 |

> **IMSLP 补充说明**：主业是 PDF 乐谱，MIDI 为次要上传，不是每首都有。有 MediaWiki + 专用 API，GitHub 上有多种语言封装库。下载需设置 `imslpdisclaimeraccepted=yes` cookie，非登录用户有 15s 延迟。不建议高频批量请求。

## 五、乐谱平台（可筛选钢琴独奏，部分支持导出 MIDI）

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| MuseScore | musescore.com | ❌ 困难 | 海量用户乐谱，免费账号需 Pro 才能下载 MIDI | piano solo |
| Flat.io | flat.io | ⚠️ 中等 | 在线制谱平台，部分乐谱免费导出 MIDI | piano solo |
| 8notes | 8notes.com | ⚠️ 中等 | 大量乐谱，部分附带 MIDI 下载链接 | piano |

## 六、半开放 / 需登录的 MIDI 社区

| 名称 | 域名 | 难度 | 特征 | 备注 |
|------|------|:----:|------|------|
| **Sheet Host** | sheet.host | ❌ 需登录 | 6025 张钢琴谱，Animenz/Cateen 等大神同人改编，日系二次元浓度极高 | 浏览公开但下载需登录（redirect 到 /account/login） |
| MidiShow | midishow.com | ⚠️ 需积分 | 国内最大 MIDI 社区，海量中文流行/古风/动漫 | 部分资源需积分或登录 |

## 七、冷门兜底 MIDI 站点（主源检索不到时轮询）

| 名称 | 域名 | 难度 | 特征 | 搜索提示 |
|------|------|:----:|------|----------|
| Midi Shrine | midishrine.com | ✅ 简单 | 独立音乐人、小众影视配乐 | 英文歌名 |
| GrooveMonkee | groovemonkee.com | ✅ 简单 | 流行、爵士钢琴伴奏/独奏 | 英文歌名 |
| Free Midi Files Download | freemidifilesdownload.com | ✅ 简单 | 老式静态目录站兜底 | 英文歌名 |
| MIDI Archive | midi-archive.com | ✅ 简单 | 复古 MIDI 归档直链 | 英文歌名 |
| Partners In Rhyme | partnersinrhyme.com/midi | ✅ 简单 | 影视纯音乐、钢琴素材 MIDI | 英文歌名 |
| Metalmidi | metalmidi.com | ✅ 简单 | 摇滚类，少量钢琴改编曲目 | 乐队名称 |

---

## 八、钢琴音频 / 录音资源（非 MIDI，供音频转录参考）

> 以下站点提供钢琴 MP3/WAV 录音，非 MIDI 文件。2midi4lin 本身是音频→MIDI 转录软件，
> 如需「搜音频→自动转录成 MIDI」功能，这些是有价值的源。

### 古典钢琴录音

| 名称 | 域名 | 可程序化 | 特征 |
|------|------|:--------:|------|
| **Piano-e-Competition** | piano-e-competition.com | ⚠️ 可爬 | 雅马哈国际钢琴比赛 Disklavier 高精度录音，力度/踏板极细腻，古典公版 |
| **Piano Society** | pianosociety.com | ✅ 简单 | 独立钢琴家录制的古典钢琴作品社区，元数据标注清晰，可免费下载 |
| **Musopen** | musopen.org | ⚠️ 中等 | 非营利古典音乐库，提供公有领域录音 + MIDI，页面结构规范 |
| **Internet Archive** | archive.org | ✅ **有官方 API** | 数十万首公有古典录音，`internetarchive` Python 包可直接检索+下载 |

### 免版税背景音乐（Royalty-Free BGM）

| 名称 | 域名 | 可程序化 | 特征 |
|------|------|:--------:|------|
| **Chosic** | chosic.com | ✅ 简单 | 专门无版权 BGM，有 Piano 标签，风格标签丰富（Emotional / Calm / Romantic），直链下载 |
| **Mixkit** | mixkit.co/free-stock-music/instrument/piano/ | ✅ 简单 | Envato 旗下免费素材站，高品质钢琴 MP3，下载链接在 DOM 中直出 |
| **Freesound** | freesound.org | ✅ **有官方 REST API** | 全球最大开源声音数据库，可搜 `piano-solo` / `piano-loop` 标签，返回 WAV/MP3 直链 |

---

## 九、已失效 / 付费站记录（供后续追踪）

| 名称 | 域名 | 状态 | 原因 |
|------|------|:----:|------|
| NinsheetMusic | ninsheetmusic.org | 💀 已失效 | 403 屏蔽 / 长期超时 |
| Jacob's Piano | jacobspiano.com | 💰 付费 | 商业乐谱站，无免费 MIDI 下载 |
| MIDIFILES.com | midifiles.com | 💰 付费 | 商业卡拉 OK MIDI 商店，每条 €9.83 |

---

## 当前已接入源

`src/downloader/sources.py` 中已实现并验证通过的源。**默认搜索只启用 3 个快速源**（`src/downloader/api.py` 中配置），慢源保留代码、不参与默认搜索：

### 默认搜索源（3 个，并发 ~1-4s 返回）

| 源 | 规模 | 难度 | 搜索速度 | 适合场景 |
|---|:----:|:----:|:--------:|----------|
| **BitMidi** 🥇 | 5 万+ | ❌ 困难（但已攻克） | ~0.8s | 游戏/流行/古典/钢琴，通用首选 |
| **FreeMIDI** | **15 万+** | ✅ 简单 | ~1-3s | 流行/摇滚/经典老歌，规模最大 |
| **MIDIsss** | ~200 首 | ⚠️ 中等 | ~1s | 音乐剧补位 |

### 保留代码、移出默认（慢 + 大目录）

| 源 | 规模 | 难度 | 说明 |
|---|:----:|:----:|------|
| **VGMusic（钢琴目录）** | 721 首 | ✅ 简单 | 游戏钢琴曲，缓存后 <1s，但大目录搜索慢 |
| **Piano-Midi.de** | 402 首 | ✅ 简单 | 古典钢琴（贝多芬/肖邦/莫扎特等），缓存后 <1s |

### MuseScore（URL 专用）

`MuseScoreSource`：粘贴乐谱链接走单独下载通道（`download_musescore_url`），不参与歌名搜索。

### 搜索效果实测（历史记录）

```
搜 "moonlight"  → 46 条结果：月光奏鸣曲 + Moonlight Serenade + Dancing in the Moonlight...
搜 "yesterday"  → 29 条结果：披头士经典
搜 "let it be"  → 4 条结果
搜 "beatles"    → 披头士 MIDI 合集
搜 "piano"      → 49 条结果：Piano Man、Romantic Piano 等
```

---

## 通用搜索技巧（各语言关键词）

```
英文: [曲名] + piano + MIDI
中文: [曲名] + 钢琴MIDI / [曲名] + 谱
日文: [曲名] + ピアノMIDI / [曲名] + 耳コピMIDI
```

- BitMidi / FreeMIDI 对英文曲名支持最好
- MidiShow / 虫虫钢琴 对中文曲名支持最好
- Ichigo's / Music is VFR 对日文曲名支持最好（罗马音）

---

## 推荐 MIDI 调度优先级

如需扩展更多源，按以下分组优先级轮询：

| 优先级 | 分组 | 包含源 | 说明 |
|:------:|------|--------|------|
| **1** | 中文优先 | MidiShow → 5nd → 虫虫钢琴 → 流行钢琴网 | 中文歌名检索 |
| **2** | 大容量海外 | BitMidi → FreeMIDI → MIDIWorld → MidisFree | 覆盖面最广 |
| **3** | 动漫/游戏 | ThePandaTooth → VGMusic → Ichigo's → Anison MIDI | 专项补位 |
| **4** | 古典专项 | Piano-Midi.de → Mutopia Project → Kunstderfuge → IMSLP | 公版合规 |
| **5** | 其余补充 | Non-Stop 2K、MidiDB、Midikaos、Midi Collection、Hamienet、Zophar's Domain | 多源覆盖 |
| **6** | 兜底冷门 | 剩余所有小众站点 | 最后轮询 |

---

## MIDI 过滤规则（建议内置）

```python
import mido

def is_piano_solo_midi(file_path):
    midi = mido.MidiFile(file_path)
    program_numbers = set()
    for track in midi.tracks:
        for msg in track:
            if msg.type == 'program_change':
                program_numbers.add(msg.program)
    # MIDI 标准中 0-7 是 Piano 族（0=Grand Piano）
    non_piano = [p for p in program_numbers if p > 7]
    if len(non_piano) == 0:
        return True, "纯钢琴 Solo"
    else:
        return False, f"包含其他乐器: {non_piano}"
```

- 标题含 `piano solo` / `piano` 优先
- 过滤含 `band`、`backing`、`full band` 的伴奏总谱
- 数据库记录 Track 数、Note 总数、乐器 Program Change，支持用户端筛选

---

## 开发约束

1. **法律合规**：所有爬虫仅限个人学习使用，禁止公开服务或商业用途；流行歌曲 MIDI 存在版权风险。
2. **困难站点处理**：BitMidi、MuseScore 等标记为困难的站点，放到轮询末尾或用已验证方案处理。
3. **请求间隔**：✅ 简单站点 ≥2s；⚠️ 中等 / ❌ 困难站点 ≥5s；开源 API（IMSLP / Internet Archive / Freesound）遵守其频率限制。
4. **不接入的类型**：
   - 研究数据集（MAESTRO / POP909 / Lakh / BiMMuDa）—— 需整体下载数 GB，不能当实时搜索源
   - 付费 API（Suno / Klangio）—— 免费开源工具不应依赖付费第三方
   - JS 渲染站（需 headless 浏览器）—— 增加打包体积与复杂度
5. **去重**：建议记录文件 MD5/SHA256 哈希，各站互相转载严重。

---

## 相关文件

- `src/downloader/sources.py` — 搜索源实现（FreeMIDISource / PianoMIDIDESource / BitMidiSource / MidisssSource / VGMusicSource / MuseScoreSource）
- `src/downloader/api.py` — MusicDownloader 协调类（默认搜索源 = bitmidi + freemidi + midisss，并发 + 整体限时）
- `src/downloader/config.py` — DOWNLOAD_DIR 统一 `~/Music/2midi4lin/downloads`
- `src/gui/api.py` — PyWebView API 类（search_midi / download_midi / download_musescore_url / open_browser）
- `src/gui/frontend/src/App.vue` — 下载面板前端（智能搜索栏：歌名 / URL 分流）

> 最后更新：2026-08-01
