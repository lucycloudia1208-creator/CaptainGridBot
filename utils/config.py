"""
設定管理モジュール - EdgeX SDK用の環境変数を読み込み
"""
import os
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

def get_config():
    """
    環境変数から設定を辞書形式で取得
    
    Returns:
        dict: EdgeX SDK用の設定情報
    """
    # Account IDを取得して整数化
    account_id_str = os.getenv("EDGEX_ACCOUNT_ID")
    
    # Account IDを整数に変換（EdgeX SDKの内部計算で必要）
    try:
        account_id = int(account_id_str)
    except (ValueError, TypeError):
        raise ValueError(f"❌ EDGEX_ACCOUNT_IDが数値ではありません: {account_id_str}")
    
    config = {
        # EdgeX API基本設定
        "base_url": os.getenv("EDGEX_BASE_URL", "https://testnet.edgex.exchange"),
        "account_id": account_id,  # 整数型で渡す
        "stark_private_key": str(os.getenv("EDGEX_STARK_PRIVATE_KEY")),
        
        # 取引設定
        "symbol": os.getenv("SYMBOL", "BTC-USDT"),
        "grid_interval": float(os.getenv("GRID_INTERVAL", "100")),
        "grid_count": int(os.getenv("GRID_COUNT", "10")),
        "order_size_usdt": float(os.getenv("ORDER_SIZE_USDT", "10")),
        
        # オプション設定
        "slack_webhook": os.getenv("EDGEX_SLACK_WEBHOOK"),
    }
    
    # 必須項目チェック
    if not config["account_id"]:
        raise ValueError("❌ EDGEX_ACCOUNT_IDが設定されていません！.envを確認してください")
    if not config["stark_private_key"] or config["stark_private_key"] == "None":
        raise ValueError("❌ EDGEX_STARK_PRIVATE_KEYが設定されていません！.envを確認してください")
    
    return config

def is_testnet(base_url: str) -> bool:
    """
    テストネットかどうか判定
    
    Args:
        base_url: EdgeXのベースURL
        
    Returns:
        bool: テストネットならTrue
    """
    return "testnet" in base_url.lower()