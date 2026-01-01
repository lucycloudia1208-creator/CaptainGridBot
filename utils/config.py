"""
設定管理モジュール - EdgeX SDK用の環境変数を読み込み
2026年1月版 - 本番優先 + 微益モード完全対応
"""
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む（ローカルテスト用）
load_dotenv()

def get_config():
    """
    環境変数から設定を辞書形式で取得（Koyeb + ローカル両対応）
    
    Returns:
        dict: EdgeX SDK + CaptainGridBot用の設定情報
    """
    # Account IDを取得して整数化
    account_id_str = os.getenv("EDGEX_ACCOUNT_ID")
    try:
        account_id = int(account_id_str) if account_id_str else None
    except (ValueError, TypeError):
        raise ValueError(f"❌ EDGEX_ACCOUNT_IDが数値ではありません: {account_id_str}")
    
    # Stark Private Key
    stark_private_key = os.getenv("EDGEX_STARK_PRIVATE_KEY")
    if not stark_private_key or stark_private_key.strip() in ["", "None", "null"]:
        raise ValueError("❌ EDGEX_STARK_PRIVATE_KEYが設定されていません！Koyeb Secretまたは.envを確認してください")
    
    config = {
        # EdgeX API基本設定（本番優先）
        "base_url": os.getenv("EDGEX_BASE_URL", "https://pro.edgex.exchange"),  # ← 本番デフォルト！！
        "account_id": account_id,
        "stark_private_key": stark_private_key.strip(),
        
        # 取引設定（ボット固有）
        "symbol": os.getenv("SYMBOL", "BTC-USDT"),
        
        # 微益モード設定（新方式：パーセント間隔）
        "grid_interval_percentage": float(os.getenv("GRID_INTERVAL_PERCENTAG", "0.0006")),  # デフォルト0.06%
        "order_size_usdt": float(os.getenv("ORDER_SIZE_USDT", "3.0")),  # 安全第一で$3スタート推奨
        
        # Phase設定
        "grid_count_phase1": int(os.getenv("GRID_COUNT_PHASE1", "2")),
        "grid_count_phase2": int(os.getenv("GRID_COUNT_PHASE2", "2")),  # 合計4本に抑え
        
        # その他ボット設定（main.pyで使う）
        "initial_balance": float(os.getenv("INITIAL_BALANCE", "43.0")),
        "force_min_order": os.getenv("FORCE_MIN_ORDER", "true").lower() == "true",
        "volatility_threshold": float(os.getenv("VOLATILITY_THRESHOLD", "0.03")),
        "volatility_check_interval": int(os.getenv("VOLATILITY_CHECK_INTERVAL", "30")),
        "loss_limit": float(os.getenv("LOSS_LIMIT", "0.50")),
        "position_imbalance_limit": int(os.getenv("POSITION_IMBALANCE_LIMIT", "3")),
        
        # オプション
        "slack_webhook": os.getenv("EDGEX_SLACK_WEBHOOK") or None,
    }
    
    # 必須項目最終チェック
    if not config["account_id"]:
        raise ValueError("❌ EDGEX_ACCOUNT_IDが設定されていません！")
    
    return config

def is_testnet(base_url: str) -> bool:
    """
    テストネットかどうか判定
    
    Args:
        base_url: EdgeXのベースURL
        
    Returns:
        bool: テストネットならTrue、本番ならFalse
    """
    return "testnet" in str(base_url).lower()