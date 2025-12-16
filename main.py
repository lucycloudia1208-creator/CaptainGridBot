"""
Captain Grid Bot - $17最終資金・不死身版
追加入金なし・超安全待機モード
"""
import asyncio
import os
from utils.logger import setup_logger
from core.grid_bot import CaptainGridBot

# ローカルテスト用: .envファイルから環境変数を読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = setup_logger()

async def main():
    """メイン関数"""
    try:
        private_key = os.getenv("EDGEX_STARK_PRIVATE_KEY")
        
        if not private_key:
            raise ValueError("❌ 環境変数 EDGEX_STARK_PRIVATE_KEY が設定されていません")
        
        config = {
            # EdgeX API基本設定
            "base_url": "https://pro.edgex.exchange",
            "account_id": 678726936008066030,
            "stark_private_key": private_key,
            
            # 取引設定
            "symbol": "BTC-USDT",
            "initial_balance": 17.18,  # $17最終資金
            
            # 超安全版設定
            "order_size_usdt": 2.0,  # $2固定（超保守的）
            "grid_count_phase1": 2,  # Phase1: 2本固定
            "grid_count_phase2": 3,  # Phase2: 3本（$20超え）
            
            # 安全機能設定
            "volatility_threshold": 0.03,  # 急落: 60秒3%
            "volatility_check_interval": 30,  # 30秒ごとチェック
            "gradual_decline_threshold": 0.01,  # ジワ下落: 10分1%
            "gradual_decline_window": 600,  # 10分（秒）
            "loss_limit": 0.30,  # 損失上限: -30%
            "max_net_position_btc": 0.01,  # ネットポジション上限
            "position_imbalance_limit": 3,  # 注文偏り上限
            
            # 自動復帰設定
            "cooldown_period_minutes": 45,
            "max_cooldown_minutes": 75,
            "stability_check_period_minutes": 60,
            "stability_threshold": 0.02,
            "min_resume_balance": 12.0,  # $12以上で再開可能（-30%対応）
            "max_consecutive_errors": 5,
            "force_resume_after_max": True,
            
            # Phase切り替え
            "phase2_threshold": 20.0,  # $20でPhase2へ
            "phase3_threshold": 30.0,  # $30でPhase3へ（将来用）
            
            # オプション
            "slack_webhook": None,
        }
        
        logger.info("🔥🔥🔥 Captain Grid Bot - $17不死身版 🔥🔥🔥")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {config['account_id']}")
        logger.info(f"💰 最終資金: ${config['initial_balance']}（追加入金なし）")
        logger.info(f"💵 注文サイズ: ${config['order_size_usdt']}固定")
        logger.info(f"🛡️ 急落検知: {config['volatility_threshold']*100}%/{config['volatility_check_interval']}秒")
        logger.info(f"🛡️ ジワ下落検知: {config['gradual_decline_threshold']*100}%/{config['gradual_decline_window']//60}分")
        logger.info(f"🛡️ 損失上限: -{config['loss_limit']*100}%")
        logger.info(f"🛡️ ネットポジション上限: {config['max_net_position_btc']} BTC")
        logger.info(f"🎯 Phase1目標: ${config['phase2_threshold']}到達")
        logger.info(f"🎄 クリスマス期間: 手動監視を推奨します")
        logger.info(f"🛡️ $17最終資金モード: 追加入金なしで不死身運用開始！！")
        logger.info(f"⚠️ 現在の高値圏では注文スキップ多発 → 超安全待機モード")
        logger.warning("🔴 本番モードで起動！")
        
        bot = CaptainGridBot(config)
        await bot.run()
        
    except ValueError as e:
        logger.error(f"❌ 設定エラー: {e}")
    except Exception as e:
        logger.error(f"❌ 予期しないエラー: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())