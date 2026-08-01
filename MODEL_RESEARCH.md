# 2midi4lin 模型研究与选型记录

> 本文档记录项目开发过程中的模型调研、测试评估、选型决策全过程，
> 用于防止上下文压缩丢失关键知识，也是后续模型迭代的参考基线。

## 一、核心任务定义

**目标：** 输入任意音频 → 输出钢琴独奏 MIDI（钢琴改编版 / Piano Cover）

这不是"音乐转录"（检测音频里有什么乐器在演奏什么音符），而是"钢琴改编生成"（理解音乐结构后编成适合钢琴弹的版本）。

两种任务的区别：

| 任务类型 | 输入 | 输出 | 代表模型 |
|---------|------|------|---------|
| **AMT**（自动音乐转录） | 任意音频 | MIDI（含多乐器、力度等） | MuScriptor, hFT-Transformer |
| **APC**（自动钢琴改编） | 任意音频 | **钢琴独奏 MIDI** | AMT-APC, Pop2Piano, PiCoGen, Etude |

---

## 二、调研过的模型清单

### 1. AMT-APC ✅ **最终选用**

| 维度 | 内容 |
|------|------|
| **论文** | arXiv 2409.14086, Kazuma Komiya (武藏野大学) |
| **代码** | github.com/310hz/amt-apc (MIT)，项目页 misya11p.github.io/amt-apc（作者 310hz / misya11p 同一人，misya11p 仓库会重定向到 310hz） |
| **定位** | 音频→钢琴改编 MIDI（APC 任务） |
| **架构** | hFT-Transformer, 5.8M 参数 |
| **ONNX 大小** | ~22MB (FP32) |
| **训练数据** | MAESTRO（古典钢琴预训练）+ 332 首歌 / 1,267 个 YouTube 钢琴 cover（微调，论文 v2 数据） |
| **风格控制** | level1/level2/level3，连续 24 维风格向量（onset rate / velocity / pitch 三种分布）控制力度和音符密度 |
| **推理速度** | 3.3s/segment (CPU, ONNX)，约比 PyTorch CPU 快 2x |
| **官方 Demo** | J-Pop（Mrs. GREEN APPLE「ライラック」, Ado「向日葵」） |

**官方定位（arXiv 2409.14086 v2，2026-07 更新）：**
- **任务定义**：APC = 从任意原始音频轨道生成钢琴翻奏 MIDI。**不是转录器**，是"风格化翻奏生成器"
- 输入不限于钢琴音频：官方 README 支持直接输入 YouTube 链接（含人声/乐队的整首混音），推理支持 `--style level1/2/3`
- 改编程度受训练数据影响（学的是 YouTube cover 的改编方式，不是逐音符忠实还原）
- **hFT-Transformer 是 Sony 的独立项目（ISMIR 2023），不是 AMT-APC 原创**：AMT-APC 把 Sony 代码复制进仓库（`models/hFT_Transformer/amt.py`），用 Sony 官方预训练权重初始化（论文原话 "publicly available pre-trained hFT-Transformer model"），为适配 512 帧序列在 MAESTRO 上额外微调 <1 epoch 后存为 `amt.pth`。即：`amt.pth` = Sony 官方权重 + 序列扩展适配微调，与 Sony 原版 `model_016_003.pkl` 同源但不等价

**本地 ONNX 化状态：**
- ONNX FP32 精度与 PyTorch 完全一致（最大误差 2.1e-4）
- 纯 numpy mel 谱替代 torchaudio，无 torch 依赖可打包
- INT8 量化被 style_vector 的广播模式阻塞（unsqueeze+repeat+gate）
- 包资源：apc.onnx (23MB) + mel_fb.npy (1MB) + 3 个 style_vector npy

**实测效果：**
| 输入类型 | 效果 | 原因 |
|---------|:----:|------|
| 钢琴独奏 | ✅ 优秀 | MAESTRO 训练数据覆盖好 |
| 流行歌曲（人声+伴奏） | ✅ 可接受 | 训练集 265 首同类数据 |
| **交响乐/管弦乐** | ❌ 差 | 训练集没出现过管弦乐频谱，频谱饱和无法提取有效音符 |
| 纯器乐（吉他等） | ⚠️ 一般 | 音色差异大，模型强行"当钢琴处理" |

### 2. PiCoGen v1

| 维度 | 内容 |
|------|------|
| **论文** | github.com/tanchihpin0517/PiCoGen |
| **定位** | 音频→钢琴 cover（APC 任务） |
| **依赖** | SheetSage（环境复杂，Python 3.8 + conda） |
| **状态** | 服务器 ~/projects/picogen_local/ 有代码，未深度测试 |
| **结论** | 环境复杂，模型质量未验证通过，未选用 |

### 3. MuScriptor

| 维度 | 内容 |
|------|------|
| **论文** | arXiv 2607.08168, Kyutai × Mirelo × IRCAM, 2026-07 |
| **代码** | github.com/muscriptor/muscriptor，权重 HuggingFace（CC BY-NC 4.0，非商用） |
| **定位** | **多乐器 AMT**（检测所有乐器音符），**不是 APC** |
| **架构** | Decoder-only Transformer（MT3 路线），small 103M / medium 307M / large 1.3B |
| **训练数据** | 1.45M 合成 MIDI 预训练 + 17 万首真实歌曲（11k 小时）微调 + RL 后训练 |
| **乐器** | MT3_FULL_PLUS 36 组乐器分类 |
| **评测** | 自建 D_Test（372 首多乐器混音）：Onset 60.4 / Frame 72.4 / Offset 48.6 / Multi 47.8（vs YourMT3+ 32.5/45.5/17.8/21.9）；**无 MAESTRO 钢琴专项评测** |
| **局限** | ① **输出无力度（velocity）**——官方明确 tokenizer 不保留力度，钢琴表现力丢失；② **无法表示同音高同乐器重叠音符**——钢琴 trill/同键快速连击会合并丢音；③ 人声不在乐器分类（转录不出人声旋律） |

**与 hFT-Transformer（amt.pth）钢琴还原能力对比：** 钢琴独奏场景 hFT-Transformer 完胜——钢琴专用 5.5M 专注 88 键（MAESTRO Note F1 97.44）、有完整 velocity、piano roll 表示无同键丢音；MuScriptor 是 36 乐器通用、无力度、同键合并，只适合"从混音里扒钢琴轨"的场景。**结论：钢琴忠实转录用 amt.pth，不用 MuScriptor。**

**实测（青花瓷）：**
- 转录出 8 轨（钢琴、吉他、贝斯、鼓等）
- **人声未被转录**——因为 MuScriptor 是乐器转录模型，人声不在乐器分类中
- 钢琴仅 238 个音符（占全部 1729 非鼓音符的 13.8%）
- 真正承载旋律的是 Acoustic Guitar（906 音符）
- 结论：**不适合 APC 任务，不适合有人声的流行歌曲——无法转录人声旋律**

**实测交响乐（HOYO-MiX 第八交响曲「千日同升」，136s 管弦乐，GPU RTX 3060）：**
- 转录出 6 个 channel，共 2330 音符
- 推理耗时：29s（GPU），远快于 CPU 的 230s

| Ch | 音符 | Program | 识别乐器 | 对应原曲 |
|:--:|:----:|:-------:|:---------|:---------|
| 0 | 653 | 29 Overdriven Guitar | 电吉他 | 原曲主旋律乐器 |
| 1 | 283 | 33 Electric Bass | 电贝斯 | 低音部分 |
| 2 | 326 | 48 String Ensemble | 弦乐合奏 | 弦乐组 |
| 3 | 97 | 52 Synth Brass | 合成铜管 | 铜管组 |
| 4 | 282 | 0 Acoustic Grand Piano | 大钢琴 | 原曲无钢琴，模型误识别 |
| 9 | 689 | — 打击乐 | 打击乐 | 节奏部分 |

- 钢琴轨仅 282 音符（2.1 note/s），比 AMT-APC 全曲 409 还少
- 钢琴+吉他+弦乐合计 1261 音符（9.5 note/s），密度约为钢琴曲的 1/4~1/3
- 结论：对无钢琴声部的交响乐，MuScriptor 能分析乐器构成（印证官方编制），但钢琴轨质量不足以直接作为钢琴 MIDI 输出

### 4. Pop2Piano

| 维度 | 内容 |
|------|------|
| **定位** | 音频→钢琴 cover（APC 任务） |
| **特点** | 能保留人声旋律（这是和纯 AMT 模型的关键区别） |
| **局限** | 编排质量受限，比 AMT-APC 差 |
| **结论** | AMT-APC 在论文评测中 Q_max 指标优于 Pop2Piano（0.035 vs 0.090） |

### 5. Etude

| 维度 | 内容 |
|------|------|
| **论文** | arXiv 2509.16522, ICASSP 2026, Tse-Yang Chen (台大) |
| **代码** | github.com/Xiugapurin/Etude |
| **定位** | 可控钢琴 cover 生成（APC 任务） |
| **架构** | 三阶段：Extract → Structuralize → Decode |
| **Extract** | **AMT-APC 架构改造版**（hFT-Transformer）：去 style vector、θmatrix 调密，鼓励输出"密集音符事件图"而非可演奏编曲 |
| **Structuralize** | Beat-Transformer 节拍检测（含小节/拍号）+ **音源分离辅助**（Spleeter 默认 / Demucs 备选；官方警告 Demucs 后端节拍准确率下降） |
| **Decode** | GPT-NeoX, 8 层, 8 头, hidden=512, **25.5M 参数**；Tiny-REMI token 表示；3 个相对风格属性（0~2，默认 1），`--decode-only` 可复用中间文件快速试风格 |
| **权重大小** | checkpoints 共 176MB |
| **硬件要求** | 官方写 16GB VRAM（针对训练），推理在 RTX 3060 12GB 可运行 |

**官方定位与架构要点：**
- **关键事实：Etude 的 Extractor 就是 AMT-APC 改的**——两者不是并列的两个模型，Etude = AMT-APC（Extract）+ 节拍框架（Structuralize）+ 生成式解码器（Decode）
- 核心卖点：显式提取节拍/小节框架 → **结构一致性强**（对得上原曲节奏），解决 AMT-APC/PiCoGen 节拍对不齐的问题
- 官方评测：主观听感**显著优于 SOTA，接近人类编曲**（针对流行歌场景）
- **官方自认短板**：Extractor 把源音频压成单特征流会丢信息（尤其主旋律），导致 Decoder 输出旋律线不完整；性能上限受前端节拍/提取模型限制
- Demucs 的作用是**节拍检测的辅助分离**（macOS 替代 Spleeter），不是"分离钢琴轨再转录"

**实测HOYO-MiX交响乐（136s管弦乐）：**

| 阶段 | 结果 | 详情 |
|:---:|:----:|------|
| Stage 1 Extract | ✅ 完成 | 输出 1152 个音符（8.4 note/s），比 AMT-APC 默认的 409 个多 2.8 倍，但仍极稀疏 |
| Stage 2 Structuralize | ❌ 崩溃 | Demucs 音源分离 ✅ 完成，但 madmom 节拍检测在交响乐上数组错误崩溃 |
| Stage 3 Decode | — 未跑到 | 缺少 beat framework，decode 无法启动 |

**问题和依赖：**
- madmom 兼容性差（需要 numpy<1.24 + setuptools 69.5.1 + 猴子补丁 np.float/np.int + collections.MutableSequence）
- madmom 节拍检测为流行音乐设计，对管弦乐复杂节奏无法处理
- GPU 驱动版本不匹配时只能 CPU 推理（缓慢）
- 依赖 demucs 做音源分离，增加部署复杂度

**结论：** 不选用。注意与官方评测的差异：官方主观评测（流行歌场景）Etude 优于现有模型，但我们实测弃用，原因是：
1. **依赖极重**：madmom 兼容性差（需 numpy<1.24 + setuptools 69.5.1 + 猴子补丁）、Spleeter/Demucs 源分离、三模型串联，打包体积不可接受
2. **交响乐在 beat 检测阶段就崩溃**（madmom 为流行音乐设计，对管弦乐复杂节奏无法处理）
3. **Decoder 丢主旋律**（论文自认 flatten 特征导致）——对工具类产品是负体验
4. 结构优势（beat 对齐）对"弹得出能听"这个核心需求边际贡献有限

### 6. Q&A (Query-and-reArrange)

| 维度 | 内容 |
|------|------|
| **论文** | arXiv 2306.01635, IJCAI 2023 |
| **定位** | **多轨 MIDI → 钢琴 MIDI 编排**，**不是音频→MIDI** |
| **参数** | 18.8M |
| **训练数据** | Slakh2100 + POP909（311,015 segments） |
| **状态** | 在服务器 3060 上训练过（50 epoch 约 4.6 天），可用 |
| **结论** | 用途不同——它解决的是"已有完整 MIDI 怎么简化成钢琴版"，不是"从音频生成 MIDI" |

---

## 三、选型决策树

```
输入：任意音频
├── 需要钢琴独奏 MIDI（钢琴改编版）
│   ├── AMT-APC ✅ 选用（最轻量，22MB ONNX，打包可达 100MB）
│   ├── PiCoGen ❌ 环境复杂，未验证
│   ├── Pop2Piano ❌ 质量比 AMT-APC 差
│   └── Etude ❌ 质量不如 AMT-APC
│
├── 需要多乐器 MIDI（完整转录）
│   └── MuScriptor（300M~1.3B，太大不适合打包）
│
└── 已有 MIDI 需要简化成钢琴版
    └── Q&A（Query-and-reArrange）
```

---

## 四、AMT-APC vs Etude 完整对比

> 两者都是"任意音频 → 钢琴翻奏 MIDI"（APCG 任务），但路线完全不同。
> **关键事实：Etude 的 Extract 阶段就是 AMT-APC 架构改造的**——Etude 不是另一个模型，而是"AMT-APC + 节拍框架 + 生成式解码器"。

| 维度 | **AMT-APC**（选用） | **Etude**（弃用） |
|:----|:----|:----|
| 本质 | 单模型端到端 | 三模型流水线 |
| 架构 | hFT-Transformer 微调（5.8M） | Extractor(AMT-APC改) + Beat-Transformer + Decoder(GPT-NeoX 25.5M) |
| 时间基准 | frame 级（无显式节拍对齐） | **beat 级**（节拍/小节/拍号显式对齐原曲） |
| 结构一致性 | 弱，节拍常对不齐原曲 | **强**（论文核心卖点） |
| 风格控制 | 24 维统计向量，level1/2/3 三档预设 | 3 个可细调属性（0~2），`--decode-only` 秒试风格 |
| 输出特点 | 直接出音符（piano roll） | 先出 dense 事件图，再"翻译"成规范编曲 |
| 部署成本 | **轻**（一个 ONNX 22MB，CPU 可跑，可打包） | **重**（三模型 176MB+ 依赖 madmom/Spleeter/Demucs，不可打包） |
| 官方评测 | Qmax 指标优于 Pop2Piano/PiCoGen2 | 主观听感优于 SOTA，接近人类编曲（流行歌场景） |
| 已知短板 | 改编自由度大、结构乱 | Decoder 丢主旋律（论文自认）；上限受前端限制；交响乐 beat 崩溃 |

**选型结论：** 对 2midi4lin 这种要打包成单 exe 的轻量工具，AMT-APC 是正确选择——轻、可 ONNX 内嵌、端到端。Etude 的 beat 结构优势对"弹得出能听"这个核心需求边际贡献有限，却带来三倍部署成本和一个丢旋律的解码器。改善流行歌听感的性价比路径是**调 AMT-APC 的 level 风格档**，而非换 Etude。

---

## 五、关键认知（防止后续丢失）

### 1. APC ≠ AMT
- **AMT（转录）**：检测"这段音频里有什么乐器在弹什么音符"
- **APC（钢琴改编）**：理解"这段音频怎么用钢琴弹出来"
- 两者高度相关（论文证明纯 AMT 模型不微调也能做 APC，F1=0.12）

### 2. 为什么交响乐不行
- APC 模型训练集只有钢琴+流行歌，没有管弦乐数据
- 交响乐 60+ 件乐器同时发声，频谱完全饱和
- 88 个钢琴键不可能还原整个管弦乐队的信息量（信息论上不可逆）
- **这不是 AMT-APC 的问题，是所有钢琴转录/改编模型的共同天花板**

**交响乐（HOYO-MiX 第八交响曲「千日同升」136s）五种处理方案实测对比：**

| 方法 | 音符 | note/s | 同时发声 | 状态 |
|:----|:---:|:------:|:--------:|:----:|
| AMT-APC 直接转录 | 409 | 3.0 | 最大 10 | ✅ 完成但极稀疏 |
| Demucs 分离→AMT-APC | 403 | 3.0 | 最大 8 | ✅ 分离无帮助 |
| Etude Stage1 (Extract) | 1152 | 8.4 | — | ⚠️ Stage2 beat 崩溃 |
| MuScriptor 钢琴轨 | 282 | 2.1 | 最大 7 | ✅ 但比 AMT-APC 还少 |
| MuScriptor 钢琴+吉他+弦乐 | 1261 | 9.5 | 最大 17 | ✅ 合轨可用，密度仍偏低 |

**结论：对于无钢琴声部的管弦乐，所有模型都无法产出有意义的钢琴独奏 MIDI。这不是模型选型问题，是 88 键钢琴的信息量上限决定的物理限制。

### 3. 为什么流行歌可以
- 流行歌虽然有多种乐器+人声，但**能量集中在主旋律频段**
- 模型可以提取主导音高，强行映射到钢琴音域
- 结果是"把流行歌当钢琴弹"——有 artifacts，但旋律线可辨认

### 4. 下载面板的定位
- 钢琴改编 MIDI 的最佳来源始终是**人工编写的改编 MIDI**
- 下载面板默认搜索 3 个快速源（BitMidi / FreeMIDI / MIDIsss），vgmusic / piano-midi.de 保留代码但移出默认（慢 + 大目录）
- 转录只适合钢琴独奏录音和流行歌曲（效果可接受）

---

## 六、服务器部署状态

| 项目 | 服务器路径 | 状态 |
|------|-----------|:----:|
| AMT-APC | `~/projects/amt-apc/` | 本地 ONNX 化完成，服务器代码保留 |
| PiCoGen | `~/projects/picogen_local/` | 代码在，未深入测试 |
| MuScriptor | `~/nas/muscriptor_medium/` | HuggingFace 权重（~1.14GB） |
| Q&A | `~/nas/qa_reference/` | 训练过，可用 |
| Etude | `~/projects/Etude/` | 代码在，测试后弃用 |
| 2midi4lin | `~/projects/2midi4lin/` | 项目主仓库 |
| 2midi4lin-training | `~/projects/2midi4lin-training/` | 训练代码（Q&A 训练） |

> 最后更新：2026-08-01