<script setup lang="ts">
import { ref, reactive, computed } from 'vue'

const tab = ref<'transcribe' | 'download'>('transcribe')

// ---- 全局拖拽拦截 ----
// PyWebView/浏览器默认会在拖文件时导航到文件路径，必须全局阻止
window.addEventListener('dragover', (e: any) => { e.preventDefault?.() })
window.addEventListener('drop', (e: any) => { e.preventDefault?.() })

// ---- 工具函数 ----
// 预览模式：浏览器里没有 pywebview 时用 mock 数据，方便 npm run dev 直接看 UI
const isMock = !(window as any).pywebview
let mockCookieOn = false // mock 状态：cookies 是否已导入

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
    case 'get_cookie_status': return delay({ configured: mockCookieOn, path: mockCookieOn ? 'C:/Users/demo/.2midi4lin/cookies.txt' : '', save_dir: 'C:/Users/demo/2midi4lin' })
    case 'choose_cookie_file': { mockCookieOn = true; return delay({ ok: true, msg: '已导入 cookies.txt' }) }
    case 'clear_cookie': { mockCookieOn = false; return delay({ ok: true, msg: '已清除 cookies' }) }
    case 'get_device_status': return delay({ provider: 'CPUExecutionProvider', gpu: false, label: 'CPU' })
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

// 视频链接平台提示：常驻显示 YouTube 反爬提醒，粘贴链接后按平台细化
const vtmUrlHint = computed(() => {
  const u = vtm.url.trim().toLowerCase()
  if (u.includes('bilibili.com') || u.includes('b23.tv')) {
    return '✅ B站链接，可直接转录；若提示需登录，请换公开视频或登录后重试'
  }
  if (u.includes('youtube.com') || u.includes('youtu.be')) {
    return '⚠️ YouTube 若遇反爬验证，请在 ⚙️设置 → 🎫 YouTube 授权 导入 cookies.txt 后重试，或换用 B站链接'
  }
  return '💡 B站链接可直接转录；YouTube 若遇反爬验证，请在 ⚙️设置 → 🎫 YouTube 授权 导入 cookies.txt'
})

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

// ======== 使用说明 ========
const showHelp = ref(false)
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

// ======== GPU 加速状态（开始转录前探测） ========
const device = ref({ provider: '', gpu: false, label: '', loaded: false })

async function loadDevice() {
  try {
    const r = await callApi('get_device_status')
    device.value = { provider: r.provider, gpu: !!r.gpu, label: r.label, loaded: true }
  } catch (e: any) { device.value.loaded = false }
}

// PyWebView 注入与 api 填充是异步的：window.pywebview 先注入（api 为空），
// pywebviewready 事件后才填充方法。Vue module script 异步执行可能早于注入，
// 因此分层等待：无 pw 时短轮询等注入；有 pw 但 api 空时等 pywebviewready + 轮询。
// 超过 2 秒仍未注入视为浏览器预览（走 mock）。
let bootTries = 0
function bootInit() {
  const pw = (window as any).pywebview
  if (pw?.api?.get_device_status) {
    loadCookie()
    loadDevice()
  } else if (pw) {
    // pywebview 已注入但 api 未填充：等 pywebviewready + 轮询兜底
    window.addEventListener('pywebviewready', bootInit, { once: true })
    setTimeout(bootInit, 400)
  } else if (bootTries++ < 10) {
    // pywebview 尚未注入（module script 早于注入执行）：短轮询等待
    setTimeout(bootInit, 200)
  } else {
    // 真·浏览器预览（无 pywebview）：走 mock
    loadCookie()
    loadDevice()
  }
}
bootInit()

// ======== 设置折叠 ========
const showSettings = ref(false)
</script>

<template>
  <div class="app" @dragover.prevent @drop.prevent>
    <header>
      <h1>🎹 2midi4lin</h1>
      <p class="subtitle">钢琴 MIDI 工具集</p>
      <div class="header-actions">
        <button class="btn-icon" @click="showHelp = true" title="使用说明">?</button>
        <button class="btn-icon" @click="showSettings = !showSettings" :title="showSettings ? '收起设置' : '设置'" :class="{active: showSettings}">⚙️</button>
        <button class="btn-icon" @click="openShareDialog()" title="分享作品">📤</button>
      </div>
    </header>

    <!-- 标签页 -->
    <nav class="tabs">
      <button :class="['tab', {active: tab==='transcribe'}]" @click="tab='transcribe'">🎵 转录</button>
      <button :class="['tab', {active: tab==='download'}]" @click="tab='download'">📥 下载</button>
    </nav>

    <!-- ========== 转录面板 ========== -->
    <div v-show="tab === 'transcribe'" class="panel">
      <!-- 输入源：本地文件 或 视频链接（二选一，左右两栏） -->
      <section class="card input-card">
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
        <div class="input-video">
          <div class="input-divider-v"><span>或粘贴视频链接</span></div>
          <input v-model="vtm.url" class="search-input" placeholder="B站 / YouTube 视频链接"
                 @keyup.enter="trStart" @input="if (vtm.url.trim() && tr.filePath) { tr.filePath=''; tr.fileName=''; tr.analysis=null }" />
          <p class="hint" style="margin-top:6px">{{ vtmUrlHint }}</p>
        </div>        <section v-if="vtm.status==='running'" class="card progress-row" style="margin-top:8px;padding:8px 4px">
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

      <!-- 转录模式 + 演奏风格 + 开始（合并一张卡） -->
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
        <p class="hint" style="margin-top:6px">忠实=逐音还原（适合钢琴独奏） · 翻奏=风格化重编（适合流行歌）</p>
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
        <div class="device-bar" v-if="device.loaded">
          <span v-if="device.gpu" class="dev-gpu">⚡ GPU 加速已启用（{{ device.label }}），转录更快</span>
          <span v-else class="dev-cpu">💻 使用 CPU 计算（转录较慢，可安装显卡驱动开启加速）</span>
        </div>
        <div class="action-row" style="margin-top:12px">
          <button class="btn-primary" :disabled="(!tr.filePath && !vtm.url.trim())||tr.status==='running'||vtm.status==='running'" @click="trStart">
            {{ vtm.status==='running' || (vtm.url.trim() && tr.status==='running') ? '处理中...' : (vtm.url.trim() ? '🎬 视频转MIDI' : '开始转录') }}
          </button>
          <button v-if="tr.status!=='idle'||vtm.status!=='idle'" class="btn-second" @click="trReset">重置</button>
        </div>
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

    <!-- 页脚：作品集 + B站 文字入口 -->
    <footer class="footer">
      <span>🌐 作品集：</span>
      <a href="#" @click.prevent="openSharePage">2midi4lin.kesug.com</a>
      <span class="sep">·</span>
      <span>B站：</span>
      <a href="#" @click.prevent="openBili">真夏的硬币</a>
    </footer>
    <section v-show="showSettings" class="card settings-card">
      <div class="settings-body">
        <div class="settings-item">
          <div class="si-head">
            <h4>📁 保存目录</h4>
            <span class="si-badge" :class="saveDir.custom ? 'badge-custom' : 'badge-default'">{{ saveDir.custom ? '自定义' : '默认' }}</span>
          </div>
          <div class="si-path" :title="saveDir.dir">{{ saveDir.dir || '加载中...' }}</div>
          <div class="si-actions">
            <button class="btn-second btn-s" @click="chooseSaveDir" :disabled="saveDir.loading">📂 选择目录</button>
            <button class="btn-second btn-s" @click="resetSaveDir" :disabled="saveDir.loading">↩ 恢复默认</button>
          </div>
          <p v-if="saveDir.msg" class="hint" style="color:#4FC3F7">{{ saveDir.msg }}</p>
          <p class="hint">默认目录为程序所在位置，不可写时自动回退到「我的文档」</p>
        </div>
        <div class="settings-item">
          <div class="si-head">
            <h4>🎫 YouTube 授权</h4>
            <span class="si-badge" :class="cookie.configured ? 'badge-ok' : 'badge-warn'">{{ cookie.configured ? '已启用' : '未配置' }}</span>
          </div>
          <div v-if="cookie.configured" class="si-path" :title="cookie.path">{{ cookie.path }}</div>
          <div class="si-actions">
            <button class="btn-second btn-s" @click="chooseCookie" :disabled="cookie.loading">📄 导入 cookies</button>
            <button v-if="cookie.configured" class="btn-second btn-s" @click="clearCookie" :disabled="cookie.loading">🗑 清除</button>
          </div>
          <p v-if="cookie.msg" class="hint" style="color:#4FC3F7">{{ cookie.msg }}</p>
          <p class="hint">从浏览器导出 YouTube cookies.txt（Chrome 装 Get cookies.txt LOCALLY 扩展）后导入，下载 YouTube 不再触发反爬验证</p>
        </div>
      </div>
    </section>
  </div>

  <!-- ========== 分享弹窗 ========== -->
  <div v-if="showHelp" class="modal-overlay" @click.self="showHelp=false">
    <div class="modal" style="max-width:440px; max-height:72vh; overflow-y:auto">
      <h3>💡 使用说明</h3>
      <p class="hint" style="margin-bottom:10px">2midi4lin 将音频 / 视频一键转为钢琴 MIDI 谱</p>
      <div class="help-sec">
        <h4>快速上手</h4>
        <ol class="help-ol">
          <li>拖入音频文件（wav / mp3 / flac / ogg），或粘贴 B 站 / YouTube 视频链接</li>
          <li>选择演奏风格（轻柔 / 标准 / 华丽）</li>
          <li>点击「开始转录」，等待处理完成</li>
          <li>完成后可打开成品文件夹、分享到集合页</li>
        </ol>
      </div>
      <div class="help-sec">
        <h4>常见说明</h4>
        <ul class="help-ul">
          <li><b>GPU 加速</b>：优先调用显卡（DirectML / CUDA），未检测到则使用 CPU</li>
          <li><b>保存目录</b>：默认程序所在位置，可在设置中修改</li>
          <li><b>YouTube 视频</b>：受限视频需在设置中导入 cookies</li>
          <li><b>作品分享</b>：分享码从「林离」软件获取，填入后作品展示在集合页</li>
        </ul>
      </div>
      <div style="display:flex;gap:8px;margin-top:14px">
        <button class="btn-primary" style="flex:1" @click="showHelp=false">知道了</button>
      </div>
    </div>
  </div>
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
  --bg: #1e1e2e;
  --card: #262637;
  --card-border: #3a3a4a;
  --accent: #e34f4f;
  --accent-hover: #f05a5a;
  --text: #e8e8f0;
  --muted: #9a9ab0;
  --radius: 12px;
  --shadow: 0 4px 12px rgba(0,0,0,.2);
  --glow: 0 0 0 1px rgba(227,79,79,.25), 0 4px 14px rgba(227,79,79,.12);
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
}
.app { max-width: 780px; margin: 0 auto; padding: 16px 20px 24px; display: flex; flex-direction: column; gap: 14px; }
header { text-align: center; padding: 8px 0 4px; position: relative; }
header h1 {
  font-size: 24px; letter-spacing: .5px; font-weight: 700;
  color: #f0f0f0;
}
.subtitle { color: var(--muted); font-size: 12px; margin-top: 2px; letter-spacing: 1.5px; }
.header-actions { position: absolute; right: 0; top: 6px; display: flex; gap: 6px; }
.btn-icon { width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; background: var(--card); border: 1px solid var(--card-border); border-radius: 8px; color: var(--muted); font-size: 14px; cursor: pointer; transition: all .2s; }
.btn-icon:hover { border-color: var(--accent); color: var(--text); }
.btn-icon.active { color: var(--accent); border-color: var(--accent); background: rgba(227,79,79,.08); }

/* 标签页 */
.tabs { display: flex; gap: 2px; background: var(--card); border-radius: var(--radius); padding: 3px; }
.tab { flex: 1; padding: 9px; border: none; border-radius: 9px; background: transparent; color: var(--muted); font-size: 14px; font-weight: 500; cursor: pointer; transition: all .2s; }
.tab.active { background: var(--accent); color: #fff; }
.tab:not(.active):hover { color: var(--text); background: rgba(255,255,255,.04); }
.panel { display: flex; flex-direction: column; gap: 14px; }

.card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  padding: 16px 18px;
  box-shadow: var(--shadow);
  transition: border-color .2s;
}
.card:hover { border-color: #4a4a5a; }
.card h4 { font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.label { font-size: 12px; color: var(--muted); margin-bottom: 8px; display: block; letter-spacing: .3px; }

/* 文件区 */
.drop-zone { border: 2px dashed #4a4a5a; border-radius: 10px; padding: 18px 12px; text-align: center; cursor: pointer; transition: all .2s; background: rgba(255,255,255,.01); }
.drop-zone:hover, .drop-zone.dragover { border-color: var(--accent); background: rgba(227,79,79,.04); }
.input-card { display: flex; gap: 0; align-items: stretch; }
.input-card .drop-zone { flex: 1; border-radius: 8px; }
.input-video { flex: 1; display: flex; flex-direction: column; justify-content: center; padding-left: 16px; border-left: 1px solid var(--card-border); }
.input-divider-v { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; color: var(--muted); font-size: 12px; }
.input-divider-v::before, .input-divider-v::after { content: ''; flex: 1; height: 1px; background: var(--card-border); }
.placeholder { display: flex; flex-direction: column; gap: 4px; align-items: center; position: relative; }
.placeholder .icon { font-size: 28px; position: relative; }
.hint { font-size: 12px; color: var(--muted); line-height: 1.5; }
.file-info { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: rgba(255,255,255,.03); border: 1px solid var(--card-border); border-radius: 8px; }
.file-info .icon { font-size: 20px; }
.file-info .name { flex: 1; word-break: break-all; font-size: 14px; }
.btn-ghost { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 16px; padding: 4px; transition: color .2s; }
.btn-ghost:hover { color: var(--accent); }

/* 风格 */
.style-group { display: flex; gap: 8px; }
.style-opt { flex: 1; padding: 8px; text-align: center; border-radius: 8px; border: 1px solid var(--card-border); cursor: pointer; font-size: 13px; font-weight: 500; transition: all .2s; background: rgba(255,255,255,.01); }
.style-opt input { display: none; }
.style-opt.active { border-color: var(--accent); background: rgba(227,79,79,.1); color: #fff; }

/* 按钮 */
.action-row { display: flex; gap: 10px; }
.btn-primary { flex: 1; height: 40px; border: none; border-radius: 8px; background: var(--accent); color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; transition: all .2s; }
.btn-primary:disabled { opacity: .4; cursor: not-allowed; }
.btn-primary:not(:disabled):hover { background: var(--accent-hover); }
.btn-primary:not(:disabled):active { transform: translateY(1px); }
.btn-second { height: 36px; padding: 0 16px; border: 1px solid var(--card-border); border-radius: 8px; background: var(--card); color: var(--text); cursor: pointer; font-size: 13px; transition: all .2s; white-space: nowrap; }
.btn-second:hover { border-color: var(--accent); color: var(--accent); }
.btn-s { padding: 0 14px; font-size: 12px; height: 32px; flex: 0 0 auto; white-space: nowrap; }
.btn-xs { padding: 0 12px; font-size: 12px; height: 28px; flex: 0 0 auto; white-space: nowrap; }

/* 进度 */
.device-bar { text-align: center; margin-bottom: 2px; }
.dev-gpu { font-size: 12px; color: #81C784; background: rgba(129,199,132,.08); border: 1px solid rgba(129,199,132,.25); border-radius: 6px; padding: 4px 10px; display: inline-block; }
.dev-cpu { font-size: 12px; color: #9a9ab0; background: rgba(154,154,176,.08); border: 1px solid rgba(154,154,176,.2); border-radius: 6px; padding: 4px 10px; display: inline-block; }
.progress-row { display: flex; align-items: center; gap: 10px; }
.bar { flex: 1; height: 6px; border-radius: 3px; background: #3a3a4a; overflow: hidden; }
.fill { height: 100%; background: var(--accent); border-radius: 3px; transition: width .3s; }
.pct { font-size: 13px; min-width: 38px; color: var(--muted); font-weight: 500; }

/* 结果 */
.result { display: flex; align-items: center; gap: 10px; }
.result .icon { font-size: 24px; }
.ri { flex: 1; }
.ri p:first-child { font-weight: 600; font-size: 14px; }
.path { font-size: 12px; color: var(--muted); word-break: break-all; margin-top: 2px; line-height: 1.5; }
.success { border-left: 3px solid #4caf50; background: rgba(76,175,80,.05); }
.error { border-left: 3px solid var(--accent); background: rgba(227,79,79,.05); }

/* 搜索 */
.search-row, .musescore-row { display: flex; gap: 8px; }
.musescore-row { border-top: 1px solid var(--card-border); padding-top: 12px; }
.search-input { flex: 1; background: #20202e; border: 1px solid var(--card-border); border-radius: 8px; padding: 10px 12px; color: var(--text); font-size: 13px; transition: border-color .2s, box-shadow .2s; }
.search-input:focus { outline: none; border-color: #5f95d7; box-shadow: 0 0 0 2px rgba(95,149,215,.15); }
.search-input::placeholder { color: #6a6a80; }

/* 结果列表 */
.result-list { max-height: 380px; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; }
.result-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #20202e; border: 1px solid var(--card-border); border-radius: 8px; transition: all .2s; }
.result-item:hover { border-color: #4a4a5a; background: #262637; }
.result-item .title { font-size: 13px; }
.src-bitmidi { color: #4CAF50; }
.src-freemidi { color: #5f95d7; }
.src-piano-midi { color: #ffa726; }
.src-vgmusic { color: #ba68c8; }
.src-midisss { color: #ef5350; }

/* 滚动条 */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #3a3a4a; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4a4a5a; }

/* 适配度检测 */
.analysis-badge { margin-top: 12px; padding: 10px 12px; background: rgba(255,167,38,.05); border: 1px solid rgba(255,167,38,.25); border-radius: 8px; display: flex; flex-direction: column; gap: 3px; align-items: center; }
.stars { font-size: 16px; letter-spacing: 3px; }

/* 分享弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(10,10,18,.65); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #262637; border: 1px solid var(--card-border); border-radius: 14px; padding: 22px; width: 90%; max-width: 400px; box-shadow: 0 20px 50px rgba(0,0,0,.4); animation: modalIn .2s ease; }
@keyframes modalIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
.modal h3 { margin-bottom: 4px; font-size: 16px; }
.modal .search-input { width: 100%; background: #20202e; border: 1px solid var(--card-border); border-radius: 8px; padding: 10px 12px; color: var(--text); font-size: 13px; }
.modal .search-input::placeholder { color: #6a6a80; }
.help-sec { margin-bottom: 10px; }
.help-sec h4 { font-size: 13px; color: var(--text); margin: 0 0 6px; padding-bottom: 4px; border-bottom: 1px solid var(--card-border); }
.help-ol, .help-ul { margin: 0; padding-left: 18px; font-size: 12.5px; color: var(--muted); line-height: 1.9; }
.help-ol li, .help-ul li { margin-bottom: 2px; }
.help-ul b { color: var(--text); font-weight: 600; }

/* 页脚（常驻入口 + 设置开关） */
.footer { text-align: center; padding: 10px; font-size: 12px; color: var(--muted); border-top: 1px solid var(--card-border); margin-top: 10px; }
.footer a { color: #7cc7ff; text-decoration: none; transition: color .2s; }
.footer a:hover { color: #aadcff; text-decoration: underline; }
.footer .sep { margin: 0 6px; color: #4a4a5a; }
.settings-card { padding: 16px 18px; animation: slideDown .25s ease; }
.settings-body { display: flex; flex-direction: column; gap: 16px; }
@keyframes slideDown { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: none; } }
.settings-item { border-top: 1px solid var(--card-border); padding-top: 14px; }
.settings-item:first-child { border-top: none; padding-top: 0; }
.si-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.si-head h4 { font-size: 13px; color: var(--text); margin: 0; }
.si-badge { font-size: 11px; padding: 2px 8px; border-radius: 20px; font-weight: 500; }
.badge-default { background: rgba(154,154,176,.12); color: var(--muted); }
.badge-custom { background: rgba(255,213,79,.12); color: #FFD54F; }
.badge-ok { background: rgba(129,199,132,.12); color: #81C784; }
.badge-warn { background: rgba(255,167,38,.12); color: #ffa726; }
.si-path { font-size: 12px; color: var(--muted); background: #20202e; border: 1px solid var(--card-border); border-radius: 8px; padding: 8px 10px; word-break: break-all; margin-bottom: 8px; }
.si-actions { display: flex; gap: 8px; }
.settings-item .hint { margin-top: 6px; }
</style>
