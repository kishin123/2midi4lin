-- 2midi4lin 分享集合页 — 建表 SQL
-- 在 PHPMyAdmin 或 MySQL 命令行执行

CREATE TABLE IF NOT EXISTS shares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_code VARCHAR(64) NOT NULL UNIQUE COMMENT '用户填的分享码（如 BV 号）',
    title VARCHAR(255) NOT NULL COMMENT '曲名',
    author VARCHAR(128) DEFAULT '' COMMENT '作者/编配者（选填）',
    source VARCHAR(64) DEFAULT '2midi4lin' COMMENT '来源标识',
    likes INT DEFAULT 0 COMMENT '点赞数',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code (share_code),
    INDEX idx_likes (likes DESC),
    INDEX idx_time (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
