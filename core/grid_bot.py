import asyncio
import aiohttp
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class CaptainGridBot:
    def __init__(self):
        self.base_url = "https://pro.edgex.exchange"
        self.account_id = os.getenv("ACCOUNT_ID")
        self.stark_private_key = os.getenv("STARK_PRIVATE_KEY")
        self.contract_id = 10000001  # BTC-USD Perpetual
        self.leverage = 100
        self.min_lot = 0.001
        self.phase1_grids = 2
        self.phase2_grids = 3
        self.daily_target = (0.001, 0.01)  # $0.001-0.01 微益モード

        logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition ($17微益モード)")
        logger.info("🌍 環境: 🚀 PRODUCTION")
        logger.info(f"🔗 Base URL: {self.base_url}")
        logger.info(f"👤 Account ID: {self.account_id}")
        logger.info("🚀 初期化完了")
        logger.info(f"📊 Phase1: {self.phase1_grids}本グリッド / Phase2: {self.phase2_grids}本グリッド")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
        logger.info(f"📏 最小ロット: {self.min_lot} BTC")
        logger.info("🎯 毎日目標: $0.001-0.01の微益！！")

    async def get_price(self) -> float:
        """
        頑健版価格取得:
        Funding API → Orderbook mid-price → 仮価格フォールバック
        """
        async with aiohttp.ClientSession() as session:
            # 1) Primary: Funding API (markPrice / indexPrice)
            try:
                url = (
                    f"{self.base_url}/api/v1/public/funding/getLatestFundingRate"
                    f"?contractId={self.contract_id}"
                )
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        raise ValueError(f"HTTP {resp.status}")
                    data = await resp.json()

                if data.get("code") != 0:
                    raise ValueError(f"API error: {data.get('msg', 'Unknown')}")

                raw = data.get("data")
                # list でも dict でも両対応（重要！）
                items = raw if isinstance(raw, list) else [raw] if raw else []

                for item in items:
                    if not item:
                        continue
                    for key in ("markPrice", "indexPrice"):  # markPrice優先
                        val = item.get(key)
                        if val is not None:
                            price = float(val)
                            logger.info(f"✅ 価格取得成功 (Funding {key}): ${price}")
                            return price
                raise ValueError("価格フィールドなし")

            except Exception as e:
                logger.warning(f"⚠️ Funding API 失敗: {e}")

            # 2) Fallback: Orderbook mid-price
            try:
                url = (
                    f"{self.base_url}/api/v1/public/orderbook"
                    f"?contractId={self.contract_id}&depth=1"
                )
                async with session.get(url, timeout=10) as resp:
                    if resp.status != 200:
                        raise ValueError(f"HTTP {resp.status}")
                    data = await resp.json()

                if data.get("code") != 0:
                    raise ValueError(f"API error: {data.get('msg', 'Unknown')}")

                book = data.get("data", {})
                bids = book.get("bids", [])
                asks = book.get("asks", [])

                if bids and asks:
                    best_bid = float(bids[0].get("price", 0))
                    best_ask = float(asks[0].get("price", 0))
                    if best_bid > 0 and best_ask > 0:
                        price = (best_bid + best_ask) / 2
                        logger.info(f"✅ 価格取得成功 (Orderbook mid): ${price:.2f}")
                        return price
                raise ValueError("板データ不足")

            except Exception as e:
                logger.warning(f"⚠️ Orderbook fallback 失敗: {e}")

            # 3) 最終フォールバック: 仮価格
            fallback_price = 65000.0
            logger.error(f"❌ 全API失敗 - 仮価格 ${fallback_price} 使用")
            return fallback_price

    async def check_api_connection(self):
        logger.info("📡 EdgeX API接続確認中...")
        price = await self.get_price()
        if price:
            logger.info("✅ API接続確認成功 - グリッド配置準備OK！！")
            return True
        else:
            logger.warning("⚠️ API接続確認エラー: 価格データ取得失敗")
            return False

    async def place_grids(self):
        current_price = await self.get_price()
        logger.info(f"📍 現在価格: ${current_price} でグリッド配置開始")
        # TODO: グリッド幅計算・注文価格生成・Private APIで注文送信
        pass

    async def monitor(self):
        logger.info("👀 監視開始 - グリッドボット稼働中...")
        while True:
            try:
                price = await self.get_price()
                # TODO: ポジション監視・決済ロジック
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"💥 監視ループエラー: {e}")
                await asyncio.sleep(30)

    async def run(self):
        if not await self.check_api_connection():
            logger.error("🚫 API接続失敗 - 30秒後に再試行")
            await asyncio.sleep(30)
            return await self.run()

        await self.place_grids()
        await self.monitor()


async def main():
    bot = CaptainGridBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())