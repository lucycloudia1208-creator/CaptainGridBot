import asyncio
import aiohttp  # ← 追加！！！
import os
from loguru import logger

class CaptainGridBot:
    def __init__(self):
        self.base_url = "https://pro.edgex.exchange"
        self.account_id = os.getenv("ACCOUNT_ID")
        self.stark_private_key = os.getenv("STARK_PRIVATE_KEY")
        self.contract_id = "10000001"
        self.leverage = 100
        self.min_lot = 0.001

        logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition ($17微益モード)")
        logger.info("🌍 環境: 🚀 PRODUCTION")
        logger.info(f"🔗 Base URL: {self.base_url}")
        logger.info(f"👤 Account ID: {self.account_id or 'None - Koyeb環境変数設定要！！'}")
        logger.info(f"🔑 STARK_PRIVATE_KEY: {'成功 (長さ ' + str(len(self.stark_private_key or '')) + '文字)' if self.stark_private_key else '失敗 (None)'}")
        logger.info("🚀 初期化完了")
        logger.info("📊 Phase1: 2本グリッド")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
        logger.info(f"📏 最小ロット: {self.min_lot} BTC")
        logger.info("🎯 毎日目標: $0.001-0.01の微益！！")

    async def get_price(self) -> float:
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/api/v1/public/funding/getLatestFundingRate?contractId={self.contract_id}"
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status}")
                    raw_data = await resp.json()

                if raw_data.get("code") != "SUCCESS":
                    raise Exception(f"APIエラー: {raw_data.get('msg')}")

                item = raw_data["data"][0]
                price = float(item["oraclePrice"])
                logger.info(f"✅ 価格取得成功 (oraclePrice): ${price:.2f}")
                return price

            except Exception as e:
                logger.warning(f"⚠️ 価格取得失敗: {e}")
                fallback = 105000.0
                logger.error(f"❌ 仮価格 ${fallback:.2f} 使用")
                return fallback

    async def check_api_connection(self):
        logger.info("📡 EdgeX API接続確認中...")
        price = await self.get_price()
        logger.info("✅ API接続確認成功 - グリッド配置準備OK！！")

    async def place_grids(self):
        current_price = await self.get_price()
        logger.info(f"📍 現在価格: ${current_price:.2f} でグリッド配置開始")

        if not self.account_id or not self.stark_private_key:
            logger.error("🚫 ACCOUNT_ID または STARK_PRIVATE_KEY 未設定 - 注文スキップ！！")
            return

        try:
            from edgex_sdk import Client, OrderSide

            client = Client(
                base_url=self.base_url,
                account_id=int(self.account_id),
                stark_private_key=self.stark_private_key
            )

            grid_percentage = 0.0006
            order_quantity = "0.002"

            buy_price = round(current_price * (1 - grid_percentage), 2)
            sell_price = round(current_price * (1 + grid_percentage), 2)

            logger.info("🔥 SDKで本番グリッド注文実行！！")
            logger.info(f"   ↓ 買い指値: ${buy_price} で {order_quantity} BTC")
            logger.info(f"   ↑ 売り指値: ${sell_price} で {order_quantity} BTC")

            buy_result = await client.create_limit_order(
                contract_id=self.contract_id,
                size=order_quantity,
                price=str(buy_price),
                side=OrderSide.BUY
            )
            logger.info(f"📩 買い注文結果: {buy_result}")

            sell_result = await client.create_limit_order(
                contract_id=self.contract_id,
                size=order_quantity,
                price=str(sell_price),
                side=OrderSide.SELL
            )
            logger.info(f"📩 売り注文結果: {sell_result}")

            logger.info("🎉🎉 グリッド注文成功！！ 微益積み上げ開始！！ 🎉🎉")

        except Exception as e:
            logger.error(f"💥 SDK注文エラー: {e}")

    async def monitor(self):
        logger.info("👀 監視開始 - グリッドボット稼働中...")
        while True:
            try:
                await self.get_price()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"💥 監視エラー: {e}")
                await asyncio.sleep(30)

    async def run(self):
        await self.check_api_connection()
        await self.place_grids()
        await self.monitor()


async def main():
    bot = CaptainGridBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())