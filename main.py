"""
Captain Grid Bot エントリーポイント
EdgeX 2026年1月版 - レバレッジ同期対応 + 完全互換修正 + SDK廃止対策
"""
import asyncio
import sys
import aiohttp
from pathlib import Path
from datetime import datetime

# プロジェクトルート追加
sys.path.insert(0, str(Path(__file__).parent))

# インポート
from core.grid_bot import CaptainGridBot
from utils.config import get_config, is_testnet
from utils.logger import setup_logger

logger = setup_logger()

async def check_api_connection(bot: CaptainGridBot):
    """
    EdgeX API接続確認（2026年仕様 - get_ticker廃止対策）
    """
    try:
        logger.info("📡 EdgeX API接続確認中...")
        
        # BTC-USDT契約ID固定
        bot.contract_id = 10000001
        
        # public tickerで現在価格取得（認証不要・最安定）
        async with aiohttp.ClientSession() as session:
            url = f"{bot.config['base_url']}/api/v1/public/ticker?contractId=10000001"
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    price_data = data.get("data", {})
                    price = price_data.get("markPrice") or price_data.get("lastPrice")
                    if price:
                        price = float(price)
                        bot.last_valid_price = price
                        logger.info(f"✅ EdgeX API接続成功 - 現在価格: ${price:.2f}")
                        logger.info("✅ 契約ID: 10000001 (BTC-USDT)")
                        return
        raise Exception("価格データ取得失敗")
        
    except Exception as e:
        logger.warning(f"⚠️ API接続確認エラー: {e}")
        logger.warning("⚠️ 続行します（初回価格はget_priceで取得）")
        bot.contract_id = 10000001

async def main():
    logger.info("=" * 70)
    logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition ($17微益モード)")
    logger.info("=" * 70)
    
    try:
        config = get_config()
        
        # 環境情報ログ
        logger.info(f"🌍 環境: {'🧪 TESTNET' if is_testnet(config['base_url']) else '🚀 PRODUCTION'}")
        logger.info(f"🔗 Base URL: {config['base_url']}")
        logger.info(f"👤 Account ID: {config['account_id']}")
        logger.info(f"💱 Symbol: {config['symbol']}")
        
        # Bot初期化
        bot = CaptainGridBot(config)
        
        # API接続確認（失敗しても続行）
        await check_api_connection(bot)
        
        # メインループ開始
        logger.info("👀 監視開始 - グリッドボット稼働中...")
        
        while True:
            try:
                current_price = await bot.get_price()
                if not current_price:
                    logger.error("❌ 現在価格取得失敗 - 30秒後に再試行")
                    await asyncio.sleep(30)
                    continue
                
                balance = await bot.get_balance()
                logger.info(f"💰 現在残高: ${balance:.4f} | 価格: ${current_price:.2f}")
                
                # Phase更新 & グリッド設定計算
                bot.update_phase(balance)
                grid_count, grid_interval = bot.calculate_grid_settings(balance, current_price)
                bot.current_grid_count = grid_count
                bot.current_grid_interval = grid_interval
                
                # グリッド配置
                await bot.place_grid(current_price)
                
                # 連続エラーリセット
                bot.consecutive_errors = 0
                
                # 次のチェックまで待機（10秒ごとに監視）
                await asyncio.sleep(10)
                
            except Exception as e:
                bot.consecutive_errors += 1
                logger.error(f"❌ メインループエラー ({bot.consecutive_errors}/{bot.max_consecutive_errors}): {e}")
                
                if bot.consecutive_errors >= bot.max_consecutive_errors:
                    logger.error("❌ 連続エラー上限 - 一時停止")
                    await asyncio.sleep(60)
                    bot.consecutive_errors = 0
                
                await asyncio.sleep(10)
                
    except KeyboardInterrupt:
        logger.info("⛔ 手動停止されました")
    except Exception as e:
        logger.error(f"❌ 致命的エラー: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())