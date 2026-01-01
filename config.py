"""
EdgeX Grid Bot 設定ファイル（2026年1月版 - 本番環境デフォルト）
"""
import os
from typing import Dict

def get_config() -> Dict:
    """環境変数から設定を取得"""
    
    config = {
        # EdgeX API設定（本番デフォルト）
        "base_url": os.getenv("EDGEX_BASE_URL", "https://pro.edgex.exchange"),  # 本番デフォルト
        "account_id": os.getenv("EDGEX_ACCOUNT_ID"),  # 必須
        "stark_private_key": os.getenv("EDGEX_STARK_PRIVATE_KEY"),  # 必須
        
        # 取引ペア
        "symbol": os.getenv("SYMBOL", "BTC-USDT"),
        "contract_id": "10000001",  # BTC-USDT固定
        
        # グリッド設定
        "grid_interval": float(os.getenv("GRID_INTERVAL", "100.0")),  # 本番: $100幅
        "grid_count": int(os.getenv("GRID_COUNT", "4")),  # 本番: 4本グリッド
        "order_size_usdt": float(os.getenv("ORDER_SIZE_USDT", "10.0")),  # 1注文あたり$10
        
        # 資金管理
        "initial_balance": float(os.getenv("INITIAL_BALANCE", "195.0")),  # 本番: $195スタート
        "invest_usdt": float(os.getenv("INVEST_USDT", "195.0")),
        
        # 微益モード設定（Phase1用）
        "grid_interval_percentage": float(os.getenv("GRID_INTERVAL_PERCENTAGE", "0.0006")),  # 0.06%
        "force_min_order": os.getenv("FORCE_MIN_ORDER", "true").lower() == "true",
        
        # 安全機能
        "volatility_threshold": float(os.getenv("VOLATILITY_THRESHOLD", "0.03")),  # 3%急落
        "volatility_check_interval": int(os.getenv("VOLATILITY_CHECK_INTERVAL", "30")),  # 30秒
        "gradual_decline_threshold": float(os.getenv("GRADUAL_DECLINE_THRESHOLD", "0.01")),  # 1%ジワ下落
        "gradual_decline_window": int(os.getenv("GRADUAL_DECLINE_WINDOW", "600")),  # 10分
        "loss_limit": float(os.getenv("LOSS_LIMIT", "0.50")),  # 50%損失で停止
        "max_net_position_btc": float(os.getenv("MAX_NET_POSITION_BTC", "0.01")),  # 0.01 BTC
        "position_imbalance_limit": int(os.getenv("POSITION_IMBALANCE_LIMIT", "3")),  # 3本差
        
        # 自動復帰設定
        "cooldown_period_minutes": int(os.getenv("COOLDOWN_PERIOD_MINUTES", "45")),  # 45分
        "max_cooldown_minutes": int(os.getenv("MAX_COOLDOWN_MINUTES", "75")),  # 75分
        "stability_check_period_minutes": int(os.getenv("STABILITY_CHECK_PERIOD_MINUTES", "60")),  # 60分
        "stability_threshold": float(os.getenv("STABILITY_THRESHOLD", "0.02")),  # 2%
        "min_resume_balance": float(os.getenv("MIN_RESUME_BALANCE", "8.5")),  # $8.5
        "max_consecutive_errors": int(os.getenv("MAX_CONSECUTIVE_ERRORS", "5")),
        "force_resume_after_max": os.getenv("FORCE_RESUME_AFTER_MAX", "true").lower() == "true",
        
        # Phase設定
        "grid_count_phase1": int(os.getenv("GRID_COUNT_PHASE1", "2")),  # $17-20: 2本
        "grid_count_phase2": int(os.getenv("GRID_COUNT_PHASE2", "3")),  # $20-30: 3本
        "phase2_threshold": float(os.getenv("PHASE2_THRESHOLD", "20.0")),
        "phase3_threshold": float(os.getenv("PHASE3_THRESHOLD", "30.0")),
        
        # Slack通知
        "slack_webhook": os.getenv("SLACK_WEBHOOK_URL"),  # オプション
        
        # テストモード判定
        "is_testnet": "testnet" in os.getenv("EDGEX_BASE_URL", "").lower()
    }
    
    # 必須項目チェック
    if not config["account_id"]:
        raise ValueError("❌ EDGEX_ACCOUNT_ID is required")
    if not config["stark_private_key"]:
        raise ValueError("❌ EDGEX_STARK_PRIVATE_KEY is required")
    
    return config

def validate_config(config: Dict) -> bool:
    """設定の妥当性チェック"""
    
    # Account ID検証
    try:
        account_id = int(config["account_id"])
        if account_id <= 0:
            raise ValueError("Account ID must be positive")
    except (ValueError, TypeError):
        raise ValueError(f"❌ Invalid account_id: {config['account_id']}")
    
    # Stark Private Key検証
    stark_key = config["stark_private_key"]
    if not stark_key.startswith("0x") or len(stark_key) < 10:
        raise ValueError(f"❌ Invalid stark_private_key format")
    
    # グリッド設定検証
    if config["grid_count"] < 1 or config["grid_count"] > 20:
        raise ValueError(f"❌ grid_count must be 1-20, got {config['grid_count']}")
    
    if config["grid_interval"] <= 0:
        raise ValueError(f"❌ grid_interval must be positive, got {config['grid_interval']}")
    
    # 資金管理検証
    if config["order_size_usdt"] <= 0:
        raise ValueError(f"❌ order_size_usdt must be positive")
    
    if config["initial_balance"] <= 0:
        raise ValueError(f"❌ initial_balance must be positive")
    
    # 安全機能検証
    if not 0 < config["loss_limit"] <= 1.0:
        raise ValueError(f"❌ loss_limit must be 0-1.0, got {config['loss_limit']}")
    
    return True
