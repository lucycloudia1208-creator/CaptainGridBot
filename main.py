"""
Captain Grid Bot - $17微益モード版
半損許容・毎日稼ぐ・勝ち体験重視
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
            
            # 微益モード設定
            "order_size_usdt": 5.0,  # $5（攻めと守りのバランス）
            "grid_count_phase1": 2,  # Phase1: 2本
            "grid_count_phase2": 3,  # Phase2: 3本（$20超え）
            "grid_interval_percentage": 0.0006,  # 0.06%幅（約$52）
            "force_min_order": True,  # 最小ロット強制配置
            
            # 安全機能設定（緩和版）
            "volatility_threshold": 0.03,  # 急落: 60秒3%
            "volatility_check_interval": 30,  # 30秒ごとチェック
            "gradual_decline_threshold": 0.01,  # ジワ下落: 10分1%
            "gradual_decline_window": 600,  # 10分（秒）
            "loss_limit": 0.50,  # 損失上限: -50%（半損許容）
            "max_net_position_btc": 0.01,  # ネットポジション上限
            "position_imbalance_limit": 3,  # 注文偏り上限
            
            # 自動復帰設定
            "cooldown_period_minutes": 45,
            "max_cooldown_minutes": 75,
            "stability_check_period_minutes": 60,
            "stability_threshold": 0.02,
            "min_resume_balance": 8.5,  # -50%対応
            "max_consecutive_errors": 5,
            "force_resume_after_max": True,
            
            # Phase切り替え
            "phase2_threshold": 20.0,  # $20でPhase2へ
            "phase3_threshold": 30.0,  # $30でPhase3へ（将来用）
            
            # オプション
            "slack_webhook": None,
        }
        
        logger.info("🔥🔥🔥 Captain Grid Bot - $17微益モード版 🔥🔥🔥")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {config['account_id']}")
        logger.info(f"💰 最終資金: ${config['initial_balance']}（追加入金なし）")
        logger.info(f"💵 注文サイズ: ${config['order_size_usdt']}固定")
        logger.info(f"🎯 毎日目標: $0.001-0.01の微益！勝ち体験重視！")
        logger.info(f"🛡️ 急落検知: {config['volatility_threshold']*100}%/{config['volatility_check_interval']}秒")
        logger.info(f"🛡️ ジワ下落検知: {config['gradual_decline_threshold']*100}%/{config['gradual_decline_window']//60}分")
        logger.info(f"🛡️ 損失上限: -{config['loss_limit']*100}%（半損許容）")
        logger.info(f"📐 グリッド幅: {config['grid_interval_percentage']*100}%（狭め＝注文入りやすい）")
        logger.info(f"🎄 クリスマス期間: 手動監視を推奨します")
        logger.info(f"⚠️ 重要指標日: 相談してから稼働！")
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