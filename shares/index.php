<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>2midi4lin 作品分享</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       background: #1a1a2e; color: #eee; min-height: 100vh; }
header { background: #16213e; padding: 30px 20px; text-align: center; }
header h1 { font-size: 24px; margin-bottom: 6px; }
header p { color: #889; font-size: 14px; }
main { max-width: 800px; margin: 0 auto; padding: 20px; }
.search-box { margin-bottom: 20px; display: flex; gap: 8px; flex-wrap: wrap; }
.search-box input { flex: 1; min-width: 200px; padding: 10px 14px; border: 1px solid #334; border-radius: 6px;
                    background: #0d1b2e; color: #eee; font-size: 14px; }
.search-box input::placeholder { color: #556; }
.sort-tabs { display: flex; gap: 4px; }
.sort-btn { padding: 10px 16px; border: 1px solid #334; border-radius: 6px; background: #0d1b2e;
             color: #889; cursor: pointer; font-size: 13px; transition: all .2s; }
.sort-btn.active { border-color: var(--accent, #e94560); color: #fff; background: #2a1a2e; }
.sort-btn:hover { border-color: #667; }
.card { background: #16213e; border-radius: 10px; padding: 16px; margin-bottom: 10px;
        transition: background 0.2s; display: flex; gap: 12px; align-items: flex-start; }
.card:hover { background: #1a2744; }
.card .body { flex: 1; }
.card .code { color: #4FC3F7; font-size: 14px; margin-bottom: 4px; }
.card .title { font-size: 16px; font-weight: 600; }
.card .meta { color: #889; font-size: 13px; margin-top: 4px; }
.card .time { color: #556; font-size: 12px; margin-top: 2px; }
.like-btn { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px 12px;
            border: 1px solid #334; border-radius: 8px; background: transparent; color: #889;
            cursor: pointer; font-size: 12px; transition: all .2s; flex-shrink: 0; }
.like-btn:hover { border-color: #e94560; color: #e94560; }
.like-btn.liked { border-color: #e94560; color: #e94560; }
.like-btn .heart { font-size: 18px; }
.like-btn .count { font-size: 13px; font-weight: 600; }
.empty { text-align: center; color: #556; padding: 40px; font-size: 14px; }
.loading { text-align: center; color: #889; padding: 40px; }
.footer { text-align: center; color: #445; font-size: 12px; padding: 30px; }
a { color: #4FC3F7; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
</head>
<body>

<header>
  <h1>🎹 2midi4lin 作品分享</h1>
  <p>来自大家的钢琴 MIDI 作品</p>
</header>

<main>
  <div class="search-box">
    <input id="searchInput" type="text" placeholder="输入分享码搜索..." oninput="filterList()">
    <div class="sort-tabs">
      <button id="sortTime" class="sort-btn active" onclick="setSort('time')">🕐 最新</button>
      <button id="sortLikes" class="sort-btn" onclick="setSort('likes')">🔥 最热</button>
    </div>
  </div>
  <div id="list" class="loading">加载中...</div>
  <div class="footer">
    用 <a href="https://github.com/kishin123/2midi4lin" target="_blank">2midi4lin</a> 制作 · 分享你的作品
  </div>
</main>

<script>
const API_URL = 'api.php';
let currentSort = 'time';
let allItems = [];

async function loadShares() {
  try {
    const res = await fetch(API_URL + '?sort=' + currentSort);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    allItems = await res.json();
    renderList(allItems);
  } catch (e) {
    document.getElementById('list').innerHTML = '<div class="empty">加载失败，请稍后重试</div>';
  }
}

function renderList(items) {
  const container = document.getElementById('list');
  if (!items || items.length === 0) {
    container.innerHTML = '<div class="empty">还没有作品，快来分享第一个吧 🎵</div>';
    return;
  }
  container.innerHTML = items.map(item => {
    const code = escapeHtml(item.share_code);
    const title = escapeHtml(item.title);
    const author = item.author ? escapeHtml(item.author) : '';
    const likes = item.likes || 0;
    const time = item.created_at ? new Date(item.created_at + ' UTC').toLocaleString('zh-CN') : '';
    const authorHtml = author ? ` · ${author}` : '';
    return `<div class="card" data-code="${code}">
      <button class="like-btn" onclick="doLike('${code}', this)" title="点赞">
        <span class="heart">♥</span>
        <span class="count">${likes}</span>
      </button>
      <div class="body">
        <div class="code">${code}</div>
        <div class="title">${title}</div>
        <div class="meta">🎹 钢琴 MIDI${authorHtml}</div>
        <div class="time">${time}</div>
      </div>
    </div>`;
  }).join('');
}

function setSort(sort) {
  currentSort = sort;
  document.getElementById('sortTime').className = 'sort-btn' + (sort === 'time' ? ' active' : '');
  document.getElementById('sortLikes').className = 'sort-btn' + (sort === 'likes' ? ' active' : '');
  loadShares();
}

async function doLike(code, btn) {
  try {
    const res = await fetch(API_URL, {
      method: 'PUT',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({share_code: code}),
    });
    if (!res.ok) return;
    const data = await res.json();
    if (data.ok) {
      btn.querySelector('.count').textContent = data.likes;
      btn.classList.add('liked');
    }
  } catch (e) {}
}

function filterList() {
  const q = document.getElementById('searchInput').value.trim().toLowerCase();
  document.querySelectorAll('.card').forEach(card => {
    const code = card.dataset.code.toLowerCase();
    card.style.display = (!q || code.includes(q)) ? '' : 'none';
  });
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s;
  return div.innerHTML;
}

loadShares();
</script>
</body>
</html>
