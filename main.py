"""
Captain Grid Bot エントリーポイント
EdgeX 2026年1月版 - レバレッジ同期対応
"""
import asyncio
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from core.grid_bot import CaptainGridBot
from utils.config import get_config
from utils.logger import setup_logger

logger = setup_logger()

async def sync_leverage(bot: CaptainGridBot):
    """EdgeX APIからレバレッジ設定を取得・同期"""
    try:
        logger.info("🔧 レバレッジ設定を確認中...")
        
        # アカウント情報取得
        account_info = await bot.client.get_account_info(account_id=bot.account_id)
        
        if isinstance(account_info, dict):
            data = account_info.get("data", {})
            # EdgeXのレバレッジは契約ごとに設定される可能性
            # 通常は100倍固定だが、APIから取得して確認
            api_leverage = data.get("leverage", 100)
            
            if api_leverage != bot.leverage:
                logger.warning(f"⚠️ レバレッジ不一致: Bot={bot.leverage}倍 vs API={api_leverage}倍")
                logger.info(f"🔧 APIの設定に同期: {api_leverage}倍")
                bot.leverage = api_leverage
            else:
                logger.info(f"✅ レバレッジ確認: {bot.leverage}倍（一致）")
        else:
            logger.warning("⚠️ アカウント情報取得失敗 → デフォルト100倍を使用")
            
    except Exception as e:
        logger.warning(f"⚠️ レバレッジ同期エラー: {e}")
        logger.info(f"→ デフォルト{bot.leverage}倍を使用")

async def check_api_version(bot: CaptainGridBot):
    """EdgeX APIバージョンチェック（V2移行監視）"""
    try:
        # ヘルスチェックまたはシステム情報でバージョン確認
        # 現在はV1固定、V2が来たら警告
        logger.info("📡 EdgeX API接続確認中...")
        
        # 価格取得でAPI接続テスト
        ticker = await bot.client.get_ticker(contract_id=bot.contract_id)
        
        if ticker and isinstance(ticker, dict) and ticker.get("code") == "SUCCESS":
            logger.info("✅ EdgeX API V1接続成功")
            
            # V2チェック（将来用）
            api_version = ticker.get("version", "V1")
            if api_version != "V1":
                logger.warning(f"⚠️ 新バージョン検知: {api_version}")
                logger.warning("⚠️ ボットの互換性を確認してください！")
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
        
        # 設定読み込み
        logger.info("📋 設定読み込み中...")
        config = get_config()
    
        # 環境情報表示
        env_type = "🧪 TESTNET" if config["is_testnet"] else "🚀 PRODUCTION"
        logger.info(f"🌍 環境: {env_type}")
        logger.info(f"🔗 Base URL: {config['base_url']}")
        logger.info(f"👤 Account ID: {config['account_id']}")
        logger.info(f"💱 Symbol: {config['symbol']} (Contract: {config['contract_id']})")
        logger.info(f"📊 グリッド: {config['grid_count']}本 × ${config['grid_interval']:.1f}幅")
        logger.info(f"💰 初期残高: ${config['initial_balance']:.2f}")
        logger.info(f"💵 注文サイズ: ${config['order_size_usdt']:.2f}/注文")
        
        if config["is_testnet"]:
            logger.warning("⚠️ テストネットモードで稼働中")
            logger.warning("⚠️ 本番デプロイ時は EDGEX_BASE_URL を変更してください")
        
        # Botインスタンス作成
        logger.info("🤖 Bot初期化中...")
        bot = CaptainGridBot(config)
        
        # API接続確認
        await check_api_version(bot)
        
        # レバレッジ同期
        await sync_leverage(bot)
        
        # Rate Limit警告
        logger.info("=" * 70)
        logger.info("⚠️ EdgeX Rate Limit: 2 operations/2 seconds")
        logger.info("⚠️ ボットは自動的に待機時間を挿入します")
        logger.info("=" * 70)
        
        # V2移行予定の通知
        logger.info("=" * 70)
        logger.info("📢 EdgeX V2 API: 2026 Q1予定")
        logger.info("📢 V1は継続稼働中、移行時は設定確認推奨")
        logger.info("=" * 70)
        
        # Bot実行
        logger.info("🚀 Captain Grid Bot 起動！")
        logger.info("=" * 70)
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("=" * 70)
        logger.info("⛔ ユーザーによる停止")
        logger.info("=" * 70)
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
