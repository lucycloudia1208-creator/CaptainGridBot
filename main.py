import asyncio
import os
from loguru import logger
from dotenv import load_dotenv

# .env読み込み（Koyebでも動くように）
load_dotenv()

# ここで新しいCaptainGridBotをインポート！！（パスは君の構成に合わせて）
from core.grid_bot import CaptainGridBot
# もしcoreフォルダがない場合は from grid_bot import CaptainGridBot

async def main():
    logger.info("=" * 70)
    logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition ($17微益モード)")
    logger.info("=" * 70)
    logger.info("🌍 環境: 🚀 PRODUCTION")
    
    # 引数なしで起動！！ これ大事！！
    bot = CaptainGridBot()
    
    # run()の中でcheck_api_connectionと監視ループ全部やってくれる
    await bot.run()

if __name__ == "__main__":
    # Koyeb/Heroku系はこれで永遠に動く
    asyncio.run(main())