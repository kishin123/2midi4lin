<script setup lang="ts">
import { ref, reactive } from 'vue'

const tab = ref<'transcribe' | 'download'>('transcribe')

// ---- 全局拖拽拦截 ----
// PyWebView/浏览器默认会在拖文件时导航到文件路径，必须全局阻止
window.addEventListener('dragover', (e: any) => { e.preventDefault?.() })
window.addEventListener('drop', (e: any) => { e.preventDefault?.() })

// ---- 工具函数 ----
// 预览模式：浏览器里没有 pywebview 时用 mock 数据，方便 npm run dev 直接看 UI
const isMock = !(window as any).pywebview

function mockCall(method: string, _args: any[]): Promise<any> {
  const delay = (v: any) => new Promise(res => setTimeout(() => res(v), 600))
  switch (method) {
    case 'open_file_dialog': return delay('C:/Users/demo/Music/示例钢琴曲.mp3')
    case 'analyze_audio': return delay({ stars: 4, tips: '较适合，主旋律和和弦能清晰提取', detail: ['和声复杂'] })
    case 'transcribe': return delay('')
    case 'get_status': return delay({ status: 'done', progress: 100, result: 'C:/Users/demo/Music/2midi4lin/示例钢琴曲.mid', error: '', stage: '' })
    case 'video_to_midi': return delay('')
    case 'search_midi': return delay([
      { id: '1', title: '示例 MIDI 1 - 钢琴独奏', source: 'bitmidi', rating: 4 },
      { id: '2', title: '示例 MIDI 2 - 流行钢琴', source: 'freemidi', rating: 3 },
      { id: '3', title: '示例 MIDI 3 - 游戏原声', source: 'midisss', rating: 2 },
    ])
    case 'search_midi_start': return delay('started')
    case 'search_midi_poll': return delay({ new: [
      { id: '1', title: '示例 MIDI 1 - 钢琴独奏', source: 'bitmidi', rating: 4 },
      { id: '2', title: '示例 MIDI 2 - 流行钢琴', source: 'freemidi', rating: 3 },
    ], done: true })
    case 'download_midi': return delay('C:/Users/demo/Downloads/示例.mid')
    case 'download_musescore_url': return delay('C:/Users/demo/Downloads/示例_musescore.mid')
    case 'open_file': return delay(null)
    case 'open_browser': return delay(null)
    case 'get_save_dir': return delay({ dir: 'C:/Users/demo/Music/2midi4lin', custom: false, custom_dir: '', default_dir: 'C:/Users/demo/2midi4lin' })
    case 'choose_save_dir': return delay({ ok: true, msg: '已设置：C:/Users/demo/Music/我的作品' })
    case 'set_save_dir': return delay({ ok: true, msg: '已设置目录' })
    case 'reset_save_dir': return delay({ ok: true, msg: '已恢复默认' })
    case 'get_cookie_status': return delay({ configured: false, path: '', save_dir: 'C:/Users/demo/2midi4lin' })
    case 'choose_cookie_file': return delay({ ok: true, msg: '已启用 cookies：cookies.txt' })
    case 'clear_cookie': return delay({ ok: true, msg: '已清除 cookies' })
    default: return delay(null)
  }
}

function callApi(method: string, ...args: any[]): Promise<any> {
  const pw = (window as any).pywebview
  if (pw?.api?.[method]) return pw.api[method](...args)
  if (isMock) return mockCall(method, args)
  return Promise.reject(new Error('PyWebView API 不可用'))
}

// ======== 转录（原生 MIDI 输出） ========
const tr = reactive({
  filePath: '', fileName: '', style: 'level2', mode: 'apc',
  status: 'idle' as 'idle'|'running'|'done'|'error',
  progress: 0, resultPath: '', errorMsg: '',
  polling: false as any,
  analysis: null as any,
})
async function trSelectFile() {
  try {
    const r = await callApi('open_file_dialog', 'audio')
    if (r) {
      // 互斥：选文件时清空视频链接
      vtm.url = ''
      tr.filePath = r; tr.fileName = r.split(/[/\\]/).pop() || r
      analyzeAudio()
    }
  } catch { alert('PyWebView API 不可用') }
}
async function trStart() {
  // 有视频链接 → 走视频转 MIDI；否则转录本地文件
  if (vtm.url.trim()) { await vtmStart(); return }
  tr.status = 'running'; tr.progress = 0; tr.resultPath = ''; tr.errorMsg = ''
  try {
    await callApi('transcribe', tr.filePath, tr.style, tr.mode)
    tr.polling = setInterval(async () => {
      const s = await callApi('get_status')
      tr.progress = s.progress
      if (s.status === 'done') { tr.status = 'done'; tr.resultPath = s.result; saveLastResult(s.result); clearInterval(tr.polling); promptShare() }
      else if (s.status === 'error') { tr.status = 'error'; tr.errorMsg = s.error; clearInterval(tr.polling) }
    }, 500)
  } catch (e: any) { tr.status = 'error'; tr.errorMsg = String(e) }
}
function trReset() {
  Object.assign(tr, {filePath:'',fileName:'',status:'idle',progress:0,resultPath:'',errorMsg:'',analysis:null})
  clearInterval(tr.polling); tr.analysis=null
  Object.assign(vtm, {url:'',status:'idle',progress:0,resultPath:'',errorMsg:'',stage:''})
  clearInterval(vtm.polling)
}
function trOpenFolder() { if (tr.resultPath) callApi('open_file', tr.resultPath).catch(()=>{}) }

let _analyzeVer = 0
async function analyzeAudio() {
  const fp = tr.filePath
  if (!fp) return
  tr.analysis = null
  const ver = ++_analyzeVer
  try {
    const r = await callApi('analyze_audio', fp)
    if (ver === _analyzeVer) tr.analysis = r
  } catch { /* 静默忽略 */ }
}

function trHandleDrop(e: any) {
  e.preventDefault?.()
  const f = e.dataTransfer?.files?.[0]

  // 判断是否为绝对路径（盘符开头 或 UNC）
  const isAbs = (p: string) => /^[A-Za-z]:[\\/]/.test(p) || /^\\\\/.test(p) || p.startsWith('/')

  // 方式一：PyWebView 注入的完整路径（dom drop 监听器自动填充）
  if (f?.pywebviewFullPath && isAbs(f.pywebviewFullPath)) {
    vtm.url = ''
    tr.filePath = f.pywebviewFullPath
    tr.fileName = f.name
    analyzeAudio()
    return
  }

  // 方式二：等 Python on_drop 回调写入完整路径
  setTimeout(() => {
    callApi('get_dropped_file').then((path: string) => {
      if (path && isAbs(path)) {
        vtm.url = ''  // 互斥：拖入文件时清空视频链接
        tr.filePath = path
        analyzeAudio()
        tr.fileName = path.split(/[/\\]/).pop() || path
        return
      }
      // 方式三：JS File.path（仅当它是绝对路径，否则忽略避免错误路径）
      if (f?.path && isAbs(f.path)) {
        vtm.url = ''
        tr.filePath = f.path
        tr.fileName = f.name
        analyzeAudio()
        return
      }
      // 最后的降级：只有文件名（dev 浏览器预览场景），提示用户
      if (f?.name) {
        tr.filePath = f.name
        tr.fileName = f.name
        alert('预览模式无法获取完整路径，请使用「点击选择文件」')
      }
    }).catch(() => {
      if (f?.path && isAbs(f.path)) {
        tr.filePath = f.path
        tr.fileName = f.name
        analyzeAudio()
      }
    })
  }, 80)
}

// ======== 视频转 MIDI（整合到转录页） ========
const vtm = reactive({
  url: '', status: 'idle' as 'idle'|'running'|'done'|'error',
  progress: 0, resultPath: '', errorMsg: '', polling: false as any,
  stage: '',  // 下载中/转换中/转录中
})
async function vtmStart() {
  const u = vtm.url.trim()
  if (!u) return
  vtm.status = 'running'; vtm.progress = 0; vtm.resultPath = ''; vtm.errorMsg = ''; vtm.stage = '下载音频中...'
  try {
    await callApi('video_to_midi', u, tr.style, tr.mode)
    vtm.polling = setInterval(async () => {
      const s = await callApi('get_status')
      vtm.progress = s.progress
      if (s.stage) vtm.stage = s.stage
      if (s.status === 'done') { vtm.status = 'done'; vtm.resultPath = s.result; saveLastResult(s.result); clearInterval(vtm.polling); promptShare() }
      else if (s.status === 'error') { vtm.status = 'error'; vtm.errorMsg = s.error; clearInterval(vtm.polling) }
    }, 500)
  } catch (e: any) { vtm.status = 'error'; vtm.errorMsg = String(e) }
}
function vtmOpenFolder() { if (vtm.resultPath) callApi('open_file', vtm.resultPath).catch(()=>{}) }

// 完成时提示分享（延迟 1s，让用户先看到结果）
// 记录最后生成的成品（路径+文件名），不受重置影响：右上角分享自动带文件名、弹窗可打开文件夹
const lastResult = reactive({ path: '', name: '' })
function saveLastResult(path: string) {
  lastResult.path = path
  lastResult.name = path.split(/[/\\]/).pop()?.replace(/\.\w+$/, '') || ''
}
function promptShare() {
  setTimeout(() => openShareDialog(undefined, false), 1000)
}

// ======== 下载：搜索 MIDI + MuseScore 合成一个搜索栏 ========
const dl = reactive({
  query: '', results: [] as any[], loading: false, errorMsg: '', searched: false,
  downloadMsg: '', downloading: false, polling: false as any,
})
async function dlSmartSearch() {
  const q = dl.query.trim()
  if (!q) return
  clearInterval(dl.polling)
  dl.loading = true; dl.errorMsg = ''; dl.results = []; dl.searched = true; dl.downloadMsg = ''
  try {
    // URL 开头 → MuseScore 乐谱下载；否则 → 多源 MIDI 流式搜索
    if (/^https?:\/\//i.test(q)) {
      const r = await callApi('download_musescore_url', q)
      dl.downloadMsg = r
      dl.loading = false
    } else {
      await callApi('search_midi_start', q)
      // 流式轮询：哪个源先返回就先显示，全部完成再收尾
      dl.polling = setInterval(async () => {
        try {
          const r = await callApi('search_midi_poll')
          if (r.new && r.new.length) {
            const errs = r.new.filter((x: any) => x.error)
            if (errs.length && !dl.results.length) dl.errorMsg = errs[0].error
            dl.results.push(...r.new.filter((x: any) => !x.error))
            if (dl.results.length > 30) dl.results = dl.results.slice(0, 30)
          }
          if (r.done) { clearInterval(dl.polling); dl.loading = false }
        } catch { clearInterval(dl.polling); dl.loading = false }
      }, 400)
    }
  } catch (e: any) { dl.errorMsg = String(e); dl.loading = false }
}
async function dlDownload(item: any) {
  dl.downloading = true; dl.downloadMsg = ''
  try {
    const r = await callApi('download_midi', item, '')
    dl.downloadMsg = r
  } catch (e: any) { dl.downloadMsg = `失败: ${e}` }
  dl.downloading = false
}
function dlOpenFolder() {
  const path = dl.downloadMsg
  if (path && !path.startsWith('失败') && !path.startsWith('下载失败'))
    callApi('open_file', path).catch(()=>{})
}
function dlOpenBrowser(url: string) {
  callApi('open_browser', url).catch(()=>{})
}

// ======== 分享 ========
const showShare = ref(false)
const shareCode = ref('')
const shareTitle = ref('')
const shareTitleEditable = ref(true) // 手动点分享可编辑曲名；自动弹出只读
const shareMsg = ref('')
const shareOk = ref(false)

async function doShare() {
  shareMsg.value = ''
  shareOk.value = false
  const code = shareCode.value.trim()
  if (!code) { shareMsg.value = '请填写分享码'; return }
  // 只允许字母数字
  if (!/^[A-Za-z0-9]+$/.test(code)) { shareMsg.value = '分享码只能包含字母和数字'; return }
  if (!shareTitle.value.trim()) { shareMsg.value = '请填写曲名'; return }
  shareMsg.value = '分享中...'
  try {
    const r = await callApi('share_midi', code, shareTitle.value.trim(), '')
    if (r.error) shareMsg.value = '分享失败：' + r.error
    else { shareOk.value = true; shareMsg.value = '✅ 分享成功！' }
  } catch (e: any) {
    shareMsg.value = '分享失败：' + String(e)
  }
}
function openShareDialog(title?: string, editable = true) {
  const src: string = title || lastResult.name || tr.fileName || (vtm.resultPath ? vtm.resultPath.split(/[/\\]/).pop() as string : '')
  shareTitle.value = src.replace(/\.\w+$/, '')
  shareTitleEditable.value = editable
  shareCode.value = ''
  shareMsg.value = ''
  shareOk.value = false
  showShare.value = true
}
function openSharePage() {
  callApi('open_browser', 'https://2midi4lin.kesug.com/')
}
function openLastResultFolder() {
  if (lastResult.path) callApi('open_file', lastResult.path).catch(()=>{})
}
function openBili() {
  callApi('open_browser', 'https://space.bilibili.com/12077314')
}

// ======== 保存目录设置 ========
const saveDir = reactive({
  dir: '', custom: false, customDir: '', msg: '', loading: false,
})

async function loadSaveDir() {
  try {
    const r = await callApi('get_save_dir')
    saveDir.dir = r.dir; saveDir.custom = r.custom; saveDir.customDir = r.custom_dir
  } catch (e: any) { saveDir.msg = String(e) }
}

async function chooseSaveDir() {
  saveDir.loading = true; saveDir.msg = ''
  try {
    const r = await callApi('choose_save_dir')
    saveDir.msg = r.msg || ''
    if (r.ok) await loadSaveDir()
  } catch (e: any) { saveDir.msg = String(e) } finally { saveDir.loading = false }
}

async function resetSaveDir() {
  saveDir.loading = true; saveDir.msg = ''
  try {
    const r = await callApi('reset_save_dir')
    saveDir.msg = r.msg || ''
    if (r.ok) await loadSaveDir()
  } catch (e: any) { saveDir.msg = String(e) } finally { saveDir.loading = false }
}

loadSaveDir()

// ======== YouTube cookies 授权 ========
const cookie = reactive({
  configured: false, path: '', msg: '', loading: false,
})

async function loadCookie() {
  try {
    const r = await callApi('get_cookie_status')
    cookie.configured = r.configured; cookie.path = r.path
  } catch (e: any) { cookie.msg = String(e) }
}

async function chooseCookie() {
  cookie.loading = true; cookie.msg = ''
  try {
    const r = await callApi('choose_cookie_file')
    cookie.msg = r.msg || ''
    if (r.ok) await loadCookie()
  } catch (e: any) { cookie.msg = String(e) } finally { cookie.loading = false }
}

async function clearCookie() {
  cookie.loading = true; cookie.msg = ''
  try {
    const r = await callApi('clear_cookie')
    cookie.msg = r.msg || ''
    if (r.ok) await loadCookie()
  } catch (e: any) { cookie.msg = String(e) } finally { cookie.loading = false }
}

loadCookie()

// ======== 设置折叠 ========
const showSettings = ref(false)
</script>

<template>
  <div class="app" @dragover.prevent @drop.prevent>
    <header>
      <h1>🎹 2midi4lin</h1>
      <p class="subtitle">钢琴 MIDI 工具集</p>
      <button class="btn-share-header" @click="openShareDialog()" title="分享作品">📤</button>
    </header>

    <!-- 标签页 -->
    <nav class="tabs">
      <button :class="['tab', {active: tab==='transcribe'}]" @click="tab='transcribe'">🎵 转录</button>
      <button :class="['tab', {active: tab==='download'}]" @click="tab='download'">📥 下载</button>
    </nav>

    <!-- ========== 转录面板 ========== -->
    <div v-show="tab === 'transcribe'" class="panel">
      <!-- 本地音频文件 -->
      <section class="card">
        <div class="drop-zone" @click="trSelectFile" @dragover.prevent @drop.prevent="trHandleDrop">
          <div v-if="!tr.filePath" class="placeholder">
            <span class="icon">📂</span><span>点击选择音频文件</span>
            <span class="hint">WAV / MP3 / FLAC / OGG</span>
          </div>
          <div v-else class="file-info">
            <span class="icon">🎵</span><span class="name">{{ tr.fileName }}</span>
            <button class="btn-ghost" @click.stop="tr.filePath=''; tr.fileName=''; tr.analysis=null">✕</button>
          </div>
          <!-- 适配度检测 -->
          <div v-if="tr.analysis && tr.analysis.stars" class="analysis-badge">
            <span class="stars">{{ '⭐'.repeat(tr.analysis.stars) + '☆'.repeat(5-tr.analysis.stars) }}</span>
            <span class="a-tip">{{ tr.analysis.tips }}</span>
          </div>
        </div>
      </section>

      <!-- 视频链接转 MIDI -->
      <section class="card">
        <div class="search-row">
          <input v-model="vtm.url" class="search-input" placeholder="或粘贴钢琴演奏视频链接（B站/YouTube），直接转 MIDI"
                 @keyup.enter="trStart" @input="if (vtm.url.trim() && tr.filePath) { tr.filePath=''; tr.fileName=''; tr.analysis=null }" />
        </div>
        <p class="hint" style="margin-top:6px">粘贴视频链接后直接点下方「开始转录」即可（与本地文件二选一）</p>
        <section v-if="vtm.status==='running'" class="card progress-row" style="margin-top:8px;padding:8px 4px">
          <div class="bar"><div class="fill" :style="{width:vtm.progress+'%'}"></div></div>
          <span class="pct">{{ vtm.progress }}%</span>
        </section>
        <section v-if="vtm.status==='running'" class="card" style="margin-top:4px;padding:6px 4px">
          <p class="hint" style="text-align:center">⏳ {{ vtm.stage }}</p>
        </section>
        <section v-if="vtm.status==='done'" class="card result success" style="margin-top:8px;padding:8px 4px">
          <span>✅</span>
          <div class="ri">
            <p>MIDI 已生成</p>
            <p class="path">{{ vtm.resultPath }}</p>
          </div>
          <button class="btn-primary btn-s" @click="vtmOpenFolder">📂 打开文件夹</button>
        </section>
        <section v-if="vtm.status==='error'" class="card result error" style="margin-top:8px;padding:8px 4px">
          <span>❌</span><div class="ri"><p>{{ vtm.errorMsg }}</p></div>
        </section>
      </section>

      <!-- 转录模式 + 演奏风格 -->
      <section class="card">
        <label class="label">转录模式</label>
        <div class="style-group">
          <label :class="['style-opt', {active: tr.mode==='amt'}]">
            <input type="radio" value="amt" v-model="tr.mode" />
            <span>🎯 忠实转录</span>
          </label>
          <label :class="['style-opt', {active: tr.mode==='apc'}]">
            <input type="radio" value="apc" v-model="tr.mode" />
            <span>🎹 翻奏改编</span>
          </label>
        </div>
        <p class="hint" style="margin-top:6px">忠实转录=逐音还原（适合钢琴独奏/钢琴视频） · 翻奏改编=风格化重编（适合流行歌/混音）</p>
        <template v-if="tr.mode==='apc'">
          <label class="label" style="margin-top:10px">演奏风格</label>
          <div class="style-group">
            <label v-for="s in ['level1','level2','level3']" :key="s"
                   :class="['style-opt', {active: tr.style===s}]">
              <input type="radio" :value="s" v-model="tr.style" />
              <span>{{ {level1:'轻柔',level2:'标准',level3:'华丽'}[s] }}</span>
            </label>
          </div>
          <p class="hint" style="margin-top:6px">轻柔=抒情稀疏 · 标准=常规演奏 · 华丽=装饰多音符密</p>
        </template>
      </section>

      <!-- 开始按钮（文件或视频链接二选一） -->
      <section class="card action-row">
        <button class="btn-primary" :disabled="(!tr.filePath && !vtm.url.trim())||tr.status==='running'||vtm.status==='running'" @click="trStart">
          {{ vtm.status==='running' || (vtm.url.trim() && tr.status==='running') ? '处理中...' : (vtm.url.trim() ? '🎬 视频转MIDI' : '开始转录') }}
        </button>
        <button v-if="tr.status!=='idle'||vtm.status!=='idle'" class="btn-second" @click="trReset">重置</button>
      </section>
      <section v-if="tr.status==='running'" class="card progress-row">
        <div class="bar"><div class="fill" :style="{width:tr.progress+'%'}"></div></div>
        <span class="pct">{{ tr.progress }}%</span>
      </section>
      <section v-if="tr.status==='done'" class="card result success">
        <span>✅</span>
        <div class="ri"><p>转录完成</p><p class="path">{{ tr.resultPath }}</p></div>
        <div style="display:flex;gap:6px;margin-top:8px">
          <button class="btn-primary btn-s" @click="trOpenFolder">📂 打开文件夹</button>
          <button class="btn-second btn-s" @click="openShareDialog()">📤 分享</button>
        </div>
      </section>
      <section v-if="tr.status==='error'" class="card result error">
        <span>❌</span><div class="ri"><p>失败</p><p class="path">{{ tr.errorMsg }}</p></div>
      </section>
    </div>

    <!-- ========== 下载面板 ========== -->
    <div v-show="tab === 'download'" class="panel">
      <section class="card search-row">
        <input v-model="dl.query" class="search-input" placeholder="搜索 MIDI 歌名，或粘贴 MuseScore 乐谱链接"
               @keyup.enter="dlSmartSearch" />
        <button class="btn-primary btn-s" :disabled="dl.loading||!dl.query.trim()" @click="dlSmartSearch">
          {{ dl.loading ? '处理中...' : '搜索' }}
        </button>
      </section>
      <section v-if="dl.downloadMsg" class="card result success" style="margin-top:0">
        <span>✅</span>
        <div class="ri"><p class="path">{{ dl.downloadMsg }}</p></div>
        <button class="btn-primary btn-s" @click="dlOpenFolder">📂 打开文件夹</button>
      </section>
      <section v-if="dl.errorMsg" class="card result error">
        <span>❌</span><div class="ri"><p>{{ dl.errorMsg }}</p></div>
      </section>
      <section v-if="dl.loading" class="card">
        <p class="hint" style="text-align:center">🔍 正在处理，请稍候...</p>
      </section>
      <section v-if="dl.searched && !dl.loading && dl.results.length === 0 && !dl.errorMsg && !dl.downloadMsg" class="card">
        <p class="hint" style="text-align:center">😕 没有找到匹配的 MIDI</p>
        <p class="hint" style="text-align:center; font-size:12px; margin-top:4px">
          试试其他关键词？或在浏览器中手动浏览：
        </p>
        <div style="text-align:center; margin-top:8px; display:flex; gap:8px; flex-wrap:wrap; justify-content:center">
          <button class="btn-primary btn-s" @click="dlOpenBrowser('https://bitmidi.com')">🌐 BitMidi</button>
          <button class="btn-second btn-s" @click="dlOpenBrowser('https://www.midishow.com/search/result?q='+encodeURIComponent(dl.query))">🇨🇳 MidiShow</button>
          <button class="btn-second btn-s" @click="dlOpenBrowser('https://freemidi.org')">🌐 FreeMIDI</button>
          <button class="btn-second btn-s" @click="dlOpenBrowser('http://piano-midi.de')">🎹 Piano-Midi</button>
          <button class="btn-second btn-s" @click="dlOpenBrowser('https://www.vgmusic.com/music/other/miscellaneous/piano/')">🎮 VGMusic</button>
        </div>
      </section>
      <section v-if="dl.results.length" class="card result-list">
        <div v-for="(item, idx) in dl.results" :key="idx" class="result-item">
          <div class="ri">
            <p class="title"><span :class="'src-'+item.source">{{ item.source }}</span> {{ item.title }}</p>
            <p class="path" v-if="item.rating">评分: {{ item.rating }}</p>
          </div>
          <button class="btn-primary btn-xs" :disabled="dl.downloading" @click="dlDownload(item)">下载</button>
        </div>
        <div style="margin-top:10px; padding:8px; text-align:center; border-top:1px solid #223; font-size:12px; color:var(--muted)">
          没找到想要的？去 <a href="#" @click.prevent="dlOpenBrowser('https://www.midishow.com/search/result?q='+encodeURIComponent(dl.query))" style="color:#4FC3F7">MidiShow</a>
          <span style="margin:0 4px">·</span>
          <a href="#" @click.prevent="dlOpenBrowser('https://5nd.com/midi/')" style="color:#4FC3F7">5nd 音乐网</a>
          <span style="margin:0 4px">·</span>
          <a href="#" @click.prevent="dlOpenBrowser('https://www.midishow.com/search/result?q='+encodeURIComponent(dl.query))" style="color:#4FC3F7">更多中文 MIDI</a>
          手动浏览
        </div>
      </section>
    </div>

    <!-- 设置（折叠） -->
    <section class="card settings-card">
      <div class="settings-toggle" @click="showSettings = !showSettings">
        <span>⚙️ 设置</span>
        <span class="chevron" :class="{open: showSettings}">▾</span>
      </div>
      <div v-show="showSettings" class="settings-body">
        <div class="settings-group">
          <h4>📁 保存目录</h4>
          <p class="path" style="margin:4px 0 8px; word-break:break-all">
            当前：{{ saveDir.dir || '加载中...' }}
            <span v-if="saveDir.custom" style="color:#FFD54F">（自定义）</span>
            <span v-else style="color:var(--muted)">（默认）</span>
          </p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-primary btn-s" @click="chooseSaveDir" :disabled="saveDir.loading">📂 选择目录</button>
            <button class="btn-second btn-s" @click="resetSaveDir" :disabled="saveDir.loading">↩ 恢复默认</button>
          </div>
          <p v-if="saveDir.msg" class="path" style="margin-top:6px; color:#4FC3F7">{{ saveDir.msg }}</p>
          <p class="path" style="margin-top:6px; color:var(--muted)">转录/视频/下载的成品统一保存到该目录下，默认跟随 exe 所在位置</p>
        </div>
        <div class="settings-group">
          <h4>🎫 YouTube 授权</h4>
          <p class="path" style="margin:4px 0 8px">
            状态：
            <span v-if="cookie.configured" style="color:#81C784">✅ 已启用</span>
            <span v-else style="color:var(--muted)">未配置（下载 YouTube 可能触发反爬验证）</span>
          </p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn-primary btn-s" @click="chooseCookie" :disabled="cookie.loading">📄 导入 cookies 文件</button>
            <button v-if="cookie.configured" class="btn-second btn-s" @click="clearCookie" :disabled="cookie.loading">🗑 清除</button>
          </div>
          <p v-if="cookie.msg" class="path" style="margin-top:6px; color:#4FC3F7">{{ cookie.msg }}</p>
          <p class="path" style="margin-top:6px; color:var(--muted)">从浏览器导出 YouTube 的 cookies.txt（Chrome 装 Get cookies.txt LOCALLY 扩展），导入后下载 YouTube 不再触发验证</p>
        </div>
      </div>
    </section>

    <!-- 页脚：常驻入口 -->
    <footer class="footer">
      <span>🌐 作品集：</span>
      <a href="#" @click.prevent="openSharePage">2midi4lin.kesug.com</a>
      <span class="sep">·</span>
      <span>B站：</span>
      <a href="#" @click.prevent="openBili">真夏的硬币</a>
    </footer>
  </div>

  <!-- ========== 分享弹窗 ========== -->
  <div v-if="showShare" class="modal-overlay" @click.self="showShare=false">
    <div class="modal">
      <h3>📤 分享作品</h3>
      <p class="hint" style="margin-bottom:4px">分享码请从 <b style="color:var(--text)">林离</b> 软件中获取（播放页面显示的分享码）</p>
      <p class="hint" style="margin-bottom:12px">填入后作品会展示在集合页上</p>
      <input v-model="shareCode" class="search-input" placeholder="从林离获取分享码（如 L35X0G）" style="margin-bottom:8px">
      <button v-if="lastResult.path" class="btn-second" style="width:100%;margin-bottom:8px" @click="openLastResultFolder">📂 打开成品文件夹</button>
      <input v-if="shareTitleEditable" v-model="shareTitle" class="search-input" placeholder="填写曲名（默认取文件名）" style="margin-bottom:8px">
      <div v-else style="margin-bottom:8px; padding:10px 12px; background:#0d1b2e; border:1px solid #334; border-radius:6px; font-size:14px; color:var(--text)">
        {{ shareTitle || '（未选择文件）' }}
      </div>
      <div style="display:flex;gap:8px;margin-top:4px">
        <button class="btn-primary" style="flex:1" @click="doShare" :disabled="shareMsg==='分享中...'">
          {{ shareMsg === '分享中...' ? '提交中...' : '📤 提交分享' }}
        </button>
        <button class="btn-second" @click="showShare=false">取消</button>
      </div>
      <p v-if="shareMsg" class="hint" style="margin-top:8px;text-align:center">{{ shareMsg }}</p>
      <p v-if="shareOk" class="hint" style="margin-top:4px;text-align:center;font-size:12px">
        <a href="#" @click.prevent="openSharePage" style="color:#4FC3F7">👀 查看集合页</a>
      </p>
    </div>
  </div>
</template>

<style>
:root {
  --bg: #0f1220;
  --card: #1a2133;
  --card-border: #2a3450;
  --accent: #e94560;
  --accent2: #ff7b95;
  --gold: #e8b04b;
  --text: #eef1f8;
  --muted: #8b94ab;
  --radius: 14px;
  --shadow: 0 4px 20px rgba(0,0,0,.35);
  --glow: 0 0 0 1px rgba(233,69,96,.25), 0 4px 18px rgba(233,69,96,.15);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: radial-gradient(1100px 560px at 15% -10%, #232a4a 0%, var(--bg) 55%), var(--bg);
  color: var(--text);
  min-height: 100vh;
}
.app { max-width: 560px; margin: 0 auto; padding: 24px 14px 40px; display: flex; flex-direction: column; gap: 14px; }
header { text-align: center; padding: 18px 0 10px; position: relative; }
header h1 {
  font-size: 28px; letter-spacing: 1px;
  background: linear-gradient(120deg, #fff, var(--gold));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  filter: drop-shadow(0 2px 10px rgba(232,176,75,.22));
}
.subtitle { color: var(--muted); font-size: 13px; margin-top: 4px; }
.btn-share-header { position: absolute; right: 0; top: 16px; background: rgba(255,255,255,.04); border: 1px solid var(--card-border); border-radius: 10px; color: var(--muted); font-size: 18px; padding: 6px 10px; cursor: pointer; transition: all .2s; backdrop-filter: blur(4px); }
.btn-share-header:hover { border-color: var(--accent); color: var(--accent); box-shadow: var(--glow); }

/* 标签页 */
.tabs { display: flex; gap: 4px; background: rgba(255,255,255,.04); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 4px; }
.tab { flex: 1; padding: 11px; border: none; border-radius: 10px; background: transparent; color: var(--muted); font-size: 14px; font-weight: 600; cursor: pointer; transition: all .25s; letter-spacing: .5px; }
.tab.active { background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff; box-shadow: 0 4px 14px rgba(233,69,96,.35); }
.tab:not(.active):hover { background: rgba(255,255,255,.06); color: var(--text); }
.panel { display: flex; flex-direction: column; gap: 14px; }

.card {
  background: linear-gradient(180deg, rgba(255,255,255,.03), transparent 40%), var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 16px 18px;
  box-shadow: var(--shadow);
}
.card h4 { font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.label { font-size: 12px; color: var(--muted); margin-bottom: 8px; display: block; }

/* 文件区 */
.drop-zone { border: 2px dashed #3a4a6b; border-radius: 12px; padding: 28px 12px; text-align: center; cursor: pointer; transition: all .25s; background: rgba(255,255,255,.02); }
.drop-zone:hover { border-color: var(--gold); background: rgba(232,176,75,.05); }
.placeholder { display: flex; flex-direction: column; gap: 6px; align-items: center; }
.placeholder .icon { font-size: 34px; }
.hint { font-size: 12px; color: var(--muted); line-height: 1.6; }
.file-info { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255,255,255,.03); border: 1px solid var(--card-border); border-radius: 10px; }
.file-info .icon { font-size: 20px; }
.file-info .name { flex: 1; word-break: break-all; font-size: 14px; }
.btn-ghost { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 16px; padding: 4px; transition: color .2s; }
.btn-ghost:hover { color: var(--accent); }

/* 风格 */
.style-group { display: flex; gap: 8px; }
.style-opt { flex: 1; padding: 10px 8px; text-align: center; border-radius: 10px; border: 2px solid var(--card-border); cursor: pointer; font-size: 13px; font-weight: 600; transition: all .2s; background: rgba(255,255,255,.02); }
.style-opt input { display: none; }
.style-opt.active { border-color: var(--accent); background: linear-gradient(135deg, rgba(233,69,96,.18), rgba(233,69,96,.05)); color: #fff; box-shadow: var(--glow); }

/* 按钮 */
.action-row { display: flex; gap: 10px; }
.btn-primary { flex: 1; padding: 13px; border: none; border-radius: 10px; background: linear-gradient(135deg, var(--accent2), var(--accent)); color: #fff; font-size: 15px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 14px rgba(233,69,96,.3); transition: all .2s; letter-spacing: .5px; }
.btn-primary:disabled { opacity: .4; cursor: not-allowed; box-shadow: none; }
.btn-primary:not(:disabled):hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(233,69,96,.4); filter: brightness(1.06); }
.btn-primary:not(:disabled):active { transform: translateY(0); }
.btn-second { padding: 12px 16px; border: 1px solid var(--card-border); border-radius: 10px; background: rgba(255,255,255,.04); color: var(--text); cursor: pointer; font-size: 14px; transition: all .2s; }
.btn-second:hover { border-color: var(--accent); color: var(--accent); background: rgba(233,69,96,.06); }
.btn-s { padding: 8px 14px; font-size: 13px; flex: 0; }
.btn-xs { padding: 6px 12px; font-size: 12px; flex: 0; }

/* 进度 */
.progress-row { display: flex; align-items: center; gap: 10px; }
.bar { flex: 1; height: 8px; border-radius: 4px; background: #2a3450; overflow: hidden; }
.fill { height: 100%; background: linear-gradient(90deg, var(--accent), var(--gold)); border-radius: 4px; transition: width .3s; box-shadow: 0 0 8px rgba(233,69,96,.4); }
.pct { font-size: 13px; min-width: 38px; color: var(--muted); font-weight: 600; }

/* 结果 */
.result { display: flex; align-items: center; gap: 10px; }
.result .icon { font-size: 24px; }
.ri { flex: 1; }
.ri p:first-child { font-weight: 600; font-size: 14px; }
.path { font-size: 12px; color: var(--muted); word-break: break-all; margin-top: 2px; line-height: 1.5; }
.success { border-left: 4px solid #4caf50; background: rgba(76,175,80,.06); }
.error { border-left: 4px solid var(--accent); background: rgba(233,69,96,.06); }

/* 搜索 */
.search-row, .musescore-row { display: flex; gap: 8px; }
.musescore-row { border-top: 1px solid var(--card-border); padding-top: 12px; }
.search-input { flex: 1; background: #121827; border: 1px solid var(--card-border); border-radius: 10px; padding: 11px 14px; color: var(--text); font-size: 14px; transition: border-color .2s, box-shadow .2s; }
.search-input:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(233,69,96,.15); }
.search-input::placeholder { color: #5c6785; }

/* 结果列表 */
.result-list { max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.result-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #121827; border: 1px solid var(--card-border); border-radius: 10px; transition: all .2s; }
.result-item:hover { border-color: #3a4a6b; background: #161d30; }
.result-item .title { font-size: 13px; }
.src-bitmidi { color: #4CAF50; }
.src-freemidi { color: #42a5f5; }
.src-piano-midi { color: #ffa726; }
.src-vgmusic { color: #ba68c8; }
.src-midisss { color: #ef5350; }

/* 滚动条 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2a3450; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3a4a6b; }

/* 适配度检测 */
.analysis-badge { margin-top: 12px; padding: 10px 12px; background: linear-gradient(135deg, rgba(232,176,75,.08), rgba(232,176,75,.02)); border: 1px solid rgba(232,176,75,.3); border-radius: 10px; display: flex; flex-direction: column; gap: 3px; align-items: center; }
.stars { font-size: 18px; letter-spacing: 3px; }
.a-tip { font-size: 12px; color: var(--muted); }

/* 分享弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(5,8,16,.7); backdrop-filter: blur(6px); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: linear-gradient(180deg, #1e2740, #161d30); border: 1px solid var(--card-border); border-radius: 16px; padding: 24px; width: 90%; max-width: 400px; box-shadow: 0 20px 60px rgba(0,0,0,.5); animation: modalIn .2s ease; }
@keyframes modalIn { from { opacity: 0; transform: translateY(12px) scale(.97); } to { opacity: 1; transform: none; } }
.modal h3 { margin-bottom: 4px; }
.modal .search-input { width: 100%; background: #121827; border: 1px solid var(--card-border); border-radius: 10px; padding: 10px 12px; color: var(--text); font-size: 14px; }
.modal .search-input::placeholder { color: #5c6785; }

/* 页脚 */
.footer { text-align: center; padding: 14px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--card-border); margin-top: 18px; }
.footer a { color: #7cc7ff; text-decoration: none; transition: color .2s; }
.footer a:hover { color: #aadcff; text-decoration: underline; }
.footer .sep { margin: 0 6px; color: #3a4a6b; }

/* 设置折叠 */
.settings-card { padding: 0; overflow: hidden; }
.settings-toggle { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; cursor: pointer; font-size: 14px; font-weight: 600; user-select: none; transition: color .2s; }
.settings-toggle:hover { color: var(--gold); }
.chevron { transition: transform .25s; color: var(--muted); font-size: 12px; }
.chevron.open { transform: rotate(180deg); }
.settings-body { padding: 0 18px 16px; display: flex; flex-direction: column; gap: 14px; }
.settings-group { border-top: 1px solid var(--card-border); padding-top: 14px; }
.settings-group:first-child { border-top: none; padding-top: 0; }
.settings-group h4 { font-size: 13px; margin-bottom: 6px; }
</style>
