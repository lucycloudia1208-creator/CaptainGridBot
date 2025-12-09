"""
ログ管理モジュール - Koyeb対応のシンプルログ
"""
import logging
import sys
from datetime import datetime

def setup_logger(name: str = "CaptainGridBot") -> logging.Logger:
    """
    ロガーをセットアップ（日本語対応、タイムスタンプ付き）
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: 設定済みロガー
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # すでにハンドラーが設定されていたら追加しない
    if logger.handlers:
        return logger
    
    # コンソール出力ハンドラー
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # 日本語対応フォーマット（タイムスタンプ付き）
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

def send_slack_notification(webhook_url: str, message: str):
    """
    Slackに通知を送信（オプション機能）
    
    Args:
        webhook_url: Slack Webhook URL
        message: 送信メッセージ
    """
    if not webhook_url:
        return
    
    try:
        import requests
        payload = {"text": f"🤖 Captain Grid Bot\n{message}"}
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        # Slack通知失敗してもボット停止しない
        print(f"⚠️ Slack通知エラー（無視して継続）: {e}")