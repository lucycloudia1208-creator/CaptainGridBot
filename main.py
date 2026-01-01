"""
Captain Grid Bot エントリーポイント
EdgeX 2026年1月版 - レバレッジ同期対応 + 完全互換修正
"""
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from core.grid_bot import CaptainGridBot
from utils.config import get_config, is_testnet  # ← is_testnet追加！！
from utils.logger import setup_logger

logger = setup_logger()

async def sync_leverage(bot: CaptainGridBot):
    """EdgeX APIからレバレッジ設定を取得・同期"""
    try:
        logger.info("🔧 レバレッジ設定を確認中...")
        
        account_info = await bot.client.get_account_info(account_id=bot.account_id)
        
        if isinstance(account_info, dict) and account_info.get("code") == "SUCCESS":
            data = account_info.get("data", {})
            api_leverage = data.get("leverage", 100)  # EdgeXは契約ごとorアカウント全体
            
            if api_leverage != bot.leverage:
                logger.warning(f"⚠️ レバレッジ不一致: Bot={bot.leverage}倍 → API={api_leverage}倍に同期")
                bot.leverage = api_leverage
            else:
                logger.info(f"✅ レバレッジ確認: {bot.leverage}倍（一致）")
        else:
            logger.warning("⚠️ アカウント情報取得失敗 → デフォルト100倍を使用")
            
    except Exception as e:
        logger.warning(f"⚠️ レバレッジ同期エラー: {e} → デフォルト{bot.leverage}倍を使用")

async def check_api_version(bot: CaptainGridBot):
    """EdgeX API接続確認（V2移行監視）"""
    try:
        logger.info("📡 EdgeX API接続確認中...")
        
        ticker = await bot.client.get_ticker(contract_id=bot.contract_id)
        
        if ticker and ticker.get("code") == "SUCCESS":
            logger.info("✅ EdgeX API接続成功（V1稼働中）")
        else:
            logger.warning("⚠️ API接続テスト: レスポンス異常")
            
    except Exception as e:
        logger.error(f"❌ API接続確認エラー: {e}")
        raise

async def main():
    """メイン処理"""
    try:
        logger.info("=" * 70)
        logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition")
        logger.info("=" * 70)
        
        logger.info("📋 設定読み込み中...")
        raw_config = get_config()  # utils.configから取得
        
        # 環境判定（本番/テストネット）
        is_test = is_testnet(raw_config["base_url"])
        env_type = "🧪 TESTNET" if is_test else "🚀 PRODUCTION"
        logger.info(f"🌍 環境: {env_type}")
        
        # CaptainGridBotが期待するキー形式に完全変換
        config = {
            "base_url": raw_config["base_url"],
            "account_id": raw_config["account_id"],
            "stark_private_key": raw_config["stark_private_key"],
            "symbol": raw_config.get("symbol", "BTC-USDT"),
            
            # グリッド設定（最新ボットが期待するキー）
            "grid_interval": raw_config.get("grid_interval", raw_config.get("GRID_INTERVAL_PERCENTAG", 100.0)),  # 互換性
            "grid_count": raw_config.get("grid_count", raw_config.get("GRID_COUNT_PHASE1", 4) + raw_config.get("GRID_COUNT_PHASE2", 0)),
            "order_size_usdt": raw_config.get("order_size_usdt", raw_config.get("ORDER_SIZE_USDT", 10.0)),
            
            # 初期値（ダッシュボード同期用）
            "initial_balance": float(raw_config.get("initial_balance", raw_config.get("INITIAL_BALANCE", 43.0))),
            
            # レバレッジ（初期値、後で同期）
            "leverage": 100,  # デフォルト100倍
            
            "slack_webhook": raw_config.get("slack_webhook"),
        }
        
        logger.info(f"🔗 Base URL: {config['base_url']}")
        logger.info(f"👤 Account ID: {config['account_id']}")
        logger.info(f"💱 Symbol: {config['symbol']}")
        logger.info(f"💰 初期資金: ${config['initial_balance']:.2f}")
        logger.info(f"💵 注文サイズ: ${config['order_size_usdt']:.2f}")
        logger.info(f"📐 グリッド間隔: {config['grid_interval']}")
        logger.info(f"🎯 グリッド本数: {config['grid_count']}本（片側基準）")
        
        logger.info("🤖 Bot初期化中...")
        bot = CaptainGridBot(config)
        
        # API接続確認
        await check_api_version(bot)
        
        # レバレッジ同期
        await sync_leverage(bot)
        
        # Rate Limit & V2通知
        logger.info("=" * 70)
        logger.warning("⚠️ EdgeX Rate Limit: 2 operations/2 seconds（自動待機対応）")
        logger.info("📢 EdgeX V2 API: 2026 Q1予定（V1は継続稼働中）")
        logger.info("=" * 70)
        
        logger.info("🚀 Captain Grid Bot 正式起動！！")
        logger.info("=" * 70)
        
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("⛔ ユーザーによる手動停止")
    except Exception as e:
        logger.error("=" * 70)
        logger.error(f"❌ 致命的エラー: {e}")
        logger.error("=" * 70)
        raise
    finally:
        logger.info("=" * 70)
        logger.info("👋 Captain Grid Bot 終了")
        logger.info("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())