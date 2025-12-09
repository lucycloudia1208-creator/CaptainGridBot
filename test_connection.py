"""
EdgeX SDK接続テスト
サーバー時刻と残高を取得して接続確認
"""
import asyncio
from utils.config import get_config
from utils.logger import setup_logger
from edgex_sdk import Client

logger = setup_logger()

async def test_connection():
    """接続テスト"""
    try:
        config = get_config()
        logger.info("🔌 EdgeX接続テスト開始...")
        
        # クライアント初期化
        client = Client(
            base_url=config["base_url"],
            account_id=config["account_id"],
            stark_private_key=config["stark_private_key"]
        )
        
        # サーバー時刻取得
        server_time = await client.get_server_time()
        logger.info(f"✅ サーバー時刻取得成功: {server_time}")
        
        # 残高取得
        account = await client.get_account_asset()
        logger.info(f"✅ アカウント情報取得成功")
        
        # USDT残高表示
        for asset in account.get("balances", []):
            if asset.get("asset") == "USDT":
                logger.info(f"💰 USDT残高: {asset.get('available')} (利用可能)")
                break
        
        logger.info("🎉 接続テスト成功！")
        return True
        
    except Exception as e:
        logger.error(f"❌ 接続テスト失敗: {e}")
        logger.error("📋 .envの設定を確認してください")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())