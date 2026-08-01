<?php
/**
 * 2midi4lin 分享 API
 * 
 * POST /api.php  — 提交分享（违禁词自动和谐为 ***）
 * PUT  /api.php  — 点赞
 * GET  /api.php  — 获取作品列表（JSON）
 * GET  /api.php?code=xxx — 查询单个分享
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PUT, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ---- 数据库配置（密码从环境变量注入，禁止硬编码） ----
// 部署时设置环境变量 SHARE_DB_PASS；Host/Name/User 为默认值可覆盖
$DB_HOST = getenv('SHARE_DB_HOST') ?: 'sql113.infinityfree.com';
$DB_NAME = getenv('SHARE_DB_NAME') ?: 'if0_42504152_share4lin';
$DB_USER = getenv('SHARE_DB_USER') ?: 'if0_42504152';
$DB_PASS = getenv('SHARE_DB_PASS') ?: '';

// ---- 违禁词列表（命中后自动替换为 ***） ----
$FORBIDDEN_WORDS = [
    '加微信', '微信号', '微信：', 'VX', 'vx',
    'QQ群', 'q群', '加QQ', 'qq号',
    '电报', 'Telegram', 't.me', 'tg群',
    'discord.gg', 'discord邀请',
    '私信我', '私聊我', '加我好友',
    'http://', 'https://', 'www.',
    '草泥马', '法克', '傻逼', '煞笔', '你妈逼',
    'fuck', 'shit', 'bitch', 'asshole',
    'cnm', 'nmsl', 'sb', 'tmd',
    '色情', '裸聊', '约炮', '一夜情',
    '赌博', '赌场', '博彩',
    '毒品', '吸毒', '冰毒',
];

try {
    $pdo = new PDO(
        "mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4",
        $DB_USER, $DB_PASS,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
    );
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['error' => '数据库连接失败']);
    exit;
}

// ---- 路由 ----
$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'POST') {
    handlePost($pdo);
} elseif ($method === 'PUT') {
    handleLike($pdo);
} else {
    handleGet($pdo);
}

// ============================================================
//  工具函数
// ============================================================

function getClientIP() {
    if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $ip = explode(',', $_SERVER['HTTP_X_FORWARDED_FOR'])[0];
    } elseif (!empty($_SERVER['HTTP_X_REAL_IP'])) {
        $ip = $_SERVER['HTTP_X_REAL_IP'];
    } else {
        $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    }
    return trim($ip);
}

/** 和谐字符串中的违禁词 */
function censorText($text) {
    global $FORBIDDEN_WORDS;
    foreach ($FORBIDDEN_WORDS as $word) {
        $text = preg_replace('/' . preg_quote($word, '/') . '/ui', '***', $text);
    }
    return $text;
}

// ============================================================
//  接口处理
// ============================================================

function handlePost($pdo) {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) {
        http_response_code(400);
        echo json_encode(['error' => '请求数据格式错误']);
        exit;
    }

    $share_code = trim($input['share_code'] ?? '');
    $title      = trim($input['title'] ?? '');
    $author     = trim($input['author'] ?? '');
    $source     = trim($input['source'] ?? '2midi4lin');

    // 校验
    if ($share_code === '') {
        http_response_code(400);
        echo json_encode(['error' => '分享码不能为空']);
        exit;
    }
    if (mb_strlen($share_code) > 64) {
        http_response_code(400);
        echo json_encode(['error' => '分享码过长']);
        exit;
    }
    if ($title === '') {
        http_response_code(400);
        echo json_encode(['error' => '曲名不能为空']);
        exit;
    }

    // 自动和谐违禁词
    $share_code = censorText($share_code);
    $title      = censorText($title);
    $author     = censorText($author);

    // 检查重复
    $stmt = $pdo->prepare('SELECT id FROM shares WHERE share_code = ?');
    $stmt->execute([$share_code]);
    if ($stmt->fetch()) {
        http_response_code(409);
        echo json_encode(['error' => '该分享码已被使用']);
        exit;
    }

    // 写入
    $stmt = $pdo->prepare(
        'INSERT INTO shares (share_code, title, author, source) VALUES (?, ?, ?, ?)'
    );
    $stmt->execute([$share_code, $title, $author, $source]);

    echo json_encode([
        'ok' => true,
        'share_code' => $share_code,
        'message' => '分享成功',
    ]);
}

// ---- PUT：点赞 ----
function handleLike($pdo) {
    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input) {
        http_response_code(400);
        echo json_encode(['error' => '请求数据格式错误']);
        exit;
    }
    $share_code = trim($input['share_code'] ?? '');
    if ($share_code === '') {
        http_response_code(400);
        echo json_encode(['error' => '分享码不能为空']);
        exit;
    }

    $stmt = $pdo->prepare('UPDATE shares SET likes = likes + 1 WHERE share_code = ?');
    $stmt->execute([$share_code]);
    if ($stmt->rowCount() === 0) {
        http_response_code(404);
        echo json_encode(['error' => '未找到该分享码']);
        exit;
    }

    $stmt = $pdo->prepare('SELECT likes FROM shares WHERE share_code = ?');
    $stmt->execute([$share_code]);
    echo json_encode(['ok' => true, 'likes' => (int)$stmt->fetchColumn()]);
}

// ---- GET：读取作品 ----
function handleGet($pdo) {
    $code = trim($_GET['code'] ?? '');
    $sort = trim($_GET['sort'] ?? '');

    if ($code !== '') {
        $stmt = $pdo->prepare('SELECT * FROM shares WHERE share_code = ?');
        $stmt->execute([$code]);
        $row = $stmt->fetch(PDO::FETCH_ASSOC);
        if ($row) {
            echo json_encode($row);
        } else {
            http_response_code(404);
            echo json_encode(['error' => '未找到该分享码']);
        }
    } else {
        if ($sort === 'likes') {
            $stmt = $pdo->query('SELECT * FROM shares ORDER BY likes DESC, created_at DESC LIMIT 200');
        } else {
            $stmt = $pdo->query('SELECT * FROM shares ORDER BY created_at DESC LIMIT 200');
        }
        echo json_encode($stmt->fetchAll(PDO::FETCH_ASSOC));
    }
}
