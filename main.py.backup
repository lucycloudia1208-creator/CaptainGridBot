"""
Captain Grid Bot - メインエントリーポイント
Private Keyのみ環境変数管理版（セキュア）
"""
import asyncio
import os
from utils.logger import setup_logger
from core.grid_bot import CaptainGridBot

logger = setup_logger()

async def main():
    """メイン関数"""
    try:
        # Private Keyだけ環境変数から取得（セキュリティ確保）
        private_key = os.getenv("EDGEX_STARK_PRIVATE_KEY")
        
        if not private_key:
            raise ValueError("❌ 環境変数 EDGEX_STARK_PRIVATE_KEY が設定されていません")
        
        # その他の設定は直接記述（環境変数トラブル回避）
        config = {
            # EdgeX API基本設定
            "base_url": "https://pro.edgex.exchange",
            "account_id": 678726936008066030,
            "stark_private_key": private_key,
            
            # 取引設定
            "symbol": "BTC-USDT",
            "grid_interval": 100.0,
            "grid_count": 4,
            "order_size_usdt": 10.0,
            
            # オプション設定
            "slack_webhook": None,
        }
        
        logger.info("🔥 セキュア設定版で起動")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {config['account_id']}")
        logger.info(f"🔑 Private Key: 環境変数から取得済み")
        
        # テストネット判定（念のため）
        if "testnet" in config["base_url"].lower():
            logger.info("⚠️ テストネットモードで起動")
        else:
            logger.warning("🔴 本番モードで起動！資金に注意してください")
        
        # ボット起動
        bot = CaptainGridBot(config)
        await bot.run()
        
    except ValueError as e:
        logger.error(f"❌ 設定エラー: {e}")
        logger.error("📋 Koyeb環境変数を確認してください")
    except Exception as e:
        logger.error(f"❌ 予期しないエラー: {e}")
        raise

if __name__ == "__main__":
    # 非同期メインループ実行
    asyncio.run(main())