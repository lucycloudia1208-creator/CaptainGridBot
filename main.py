"""
Captain Grid Bot - メインエントリーポイント
全損リスク限りなく0の超安全版
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
            "initial_balance": 20.0,  # 推奨初期残高 $20
            
            # 動的グリッド設定（残高に応じて自動調整）
            "grid_interval": None,  # 自動計算
            "grid_count": None,     # 自動計算
            "order_size_usdt": 10.0,
            
            # 安全機能設定
            "volatility_threshold": 0.03,  # 3%変動で緊急停止
            "volatility_check_interval": 60,  # 60秒間隔でチェック
            "liquidation_buffer": 0.80,  # -80%損失で強制決済
            "cooldown_period_minutes": 60,  # 基本冷却期間1時間
            "max_cooldown_minutes": 180,  # 最大冷却期間3時間
            "stability_check_period_minutes": 120,  # 過去2時間の安定性確認
            "stability_threshold": 0.01,  # 1%以下で安定と判断
            "min_resume_balance": 10.0,  # 再開最低残高 $10
            "max_consecutive_errors": 5,  # 連続エラー上限
            
            # オプション設定
            "slack_webhook": None,
        }
        
        logger.info("🔥🔥🔥 Captain Grid Bot - 超安全版 起動 🔥🔥🔥")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {config['account_id']}")
        logger.info(f"🔑 Private Key: 環境変数から取得済み")
        logger.info(f"💰 推奨初期残高: ${config['initial_balance']}")
        logger.info(f"🛡️ ボラ緊急停止: {config['volatility_threshold']*100}%/{config['volatility_check_interval']}秒")
        logger.info(f"🛡️ 強制清算回避: -{config['liquidation_buffer']*100}%損失")
        logger.info(f"❄️ 冷却期間: {config['cooldown_period_minutes']}分（最大{config['max_cooldown_minutes']}分）")
        logger.info(f"✅ 再開条件: ${config['min_resume_balance']}以上 + {config['stability_check_period_minutes']}分間安定")
        
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