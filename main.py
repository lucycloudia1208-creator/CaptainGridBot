"""
Captain Grid Bot - メインエントリーポイント
EdgeX Python SDK完全活用版
"""
import asyncio
from utils.config import get_config, is_testnet
from utils.logger import setup_logger
from core.grid_bot import CaptainGridBot

logger = setup_logger()

async def main():
    """メイン関数"""
    try:
        # 設定読み込み
        config = get_config()
        
        # テストネット警告
        if is_testnet(config["base_url"]):
            logger.info("⚠️ テストネットモードで起動")
        else:
            logger.warning("🔴 本番モードで起動！資金に注意してください")
        
        # ボット起動
        bot = CaptainGridBot(config)
        await bot.run()
        
    except ValueError as e:
        logger.error(f"❌ 設定エラー: {e}")
        logger.error("📋 .envファイルを確認してください")
    except Exception as e:
        logger.error(f"❌ 予期しないエラー: {e}")
        raise

if __name__ == "__main__":
    # 非同期メインループ実行
    asyncio.run(main())