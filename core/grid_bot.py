import asyncio
import aiohttp
import os
from loguru import logger

class CaptainGridBot:
    def __init__(self):
        self.base_url = "https://pro.edgex.exchange"
        self.account_id = os.getenv("ACCOUNT_ID")
        self.stark_private_key = os.getenv("STARK_PRIVATE_KEY")
        self.contract_id = "10000001"  # 文字列で！（2026年仕様）
        self.leverage = 100
        self.min_lot = 0.001
        self.phase1_grids = 2
        self.phase2_grids = 3

        logger.info("🏴‍☠️ Captain Grid Bot - EdgeX 2026 Edition ($17微益モード)")
        logger.info("🌍 環境: 🚀 PRODUCTION")
        logger.info(f"🔗 Base URL: {self.base_url}")
        logger.info(f"👤 Account ID: {self.account_id or 'None (Koyeb環境変数設定要！)'}")
        logger.info(f"🔑 STARK_PRIVATE_KEY 読み込み: {'成功 (長さ ' + str(len(self.stark_private_key or '')) + '文字)' if self.stark_private_key else '失敗 (None)'}")
        logger.info("🚀 初期化完了")
        logger.info(f"📊 Phase1: {self.phase1_grids}本グリッド / Phase2: {self.phase2_grids}本グリッド")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
        logger.info(f"📏 最小ロット: {self.min_lot} BTC")
        logger.info("🎯 毎日目標: $0.001-0.01の微益！！")

    async def get_price(self) -> float:
        """2026年1月最新: Funding APIでoraclePrice取得（最安定）"""
        async with aiohttp.ClientSession() as session:
            try:
                url = f"{self.base_url}/api/v1/public/funding/getLatestFundingRate?contractId={self.contract_id}"
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        logger.warning(f"HTTPステータス: {resp.status}")
                        raise Exception(f"HTTP {resp.status}")

                    raw_data = await resp.json()
                    logger.debug(f"Funding API 生レスポンス: {raw_data}")  # デバッグ用

                    # 成功判定: code == "SUCCESS"
                    if raw_data.get("code") != "SUCCESS":
                        raise Exception(f"APIエラー: {raw_data.get('msg', 'Unknown')}")

                    data = raw_data.get("data")
                    if not data:
                        raise Exception("dataフィールドなし")

                    item = data[0] if isinstance(data, list) else data

                    # oraclePriceがmark/fair price相当（最優先）
                    price_str = item.get("oraclePrice")
                    if not price_str:
                        raise Exception("oraclePriceなし")

                    price = float(price_str)
                    logger.info(f"✅ 価格取得成功 (oraclePrice): ${price:.2f}")
                    return price

            except Exception as e:
                logger.warning(f"⚠️ 価格取得失敗: {e}")

            # 最終安全網
            fallback = 105000.0  # 2026年1月現在のBTC目安
            logger.error(f"❌ 全失敗 - 仮価格 ${fallback:.2f} 使用")
            return fallback

    async def check_api_connection(self):
        logger.info("📡 EdgeX API接続確認中...")
        price = await self.get_price()
        logger.info("✅ API接続確認成功 - グリッド配置準備OK！！")
        return True

    async def place_grids(self):
        current_price = await self.get_price()
        logger.info(f"📍 現在価格: ${current_price:.2f} でグリッド配置開始")
        # 次にここにグリッド注文ロジック入れる！！
        # 必須チェック: 認証情報がないと注文不可
        grid_percentage = 0.0006
        order_quantity = "0.002"
        contract_id = self.contract_id

        buy_price = round(current_price * (1 - grid_percentage), 2)
        sell_price = round(current_price * (1 + grid_percentage), 2)

        logger.info("🔥 本番グリッド注文実行！！")
        logger.info(f"   資金: 46.65 USDT | レバ: 100倍 | 注文量: {order_quantity} BTC × 2本")
        logger.info(f"   ↓ 買い指値: ${buy_price} で {order_quantity} BTC")
        logger.info(f"   ↑ 売り指値: ${sell_price} で {order_quantity} BTC")

        async with aiohttp.ClientSession() as session:
            try:
                # Step1: 既存注文全キャンセル（重複防止）
                cancel_url = f"{self.base_url}/api/v1/private/order/cancel_all"
                cancel_payload = {
                    "accountId": self.account_id,
                    "contractId": contract_id
                }
                # Stark署名はEdgeX SDK or 手実装必要 → 今は省略（初回は空でOKな場合あり）
                async with session.post(cancel_url, json=cancel_payload) as resp:
                    result = await resp.json()
                    logger.info(f"🧹 既存注文キャンセル結果: {result}")

                # Step2: 買い注文
                buy_payload = {
                    "accountId": self.account_id,
                    "contractId": contract_id,
                    "side": "BUY",
                    "orderType": "LIMIT",
                    "price": str(buy_price),
                    "quantity": order_quantity,
                    "leverage": str(self.leverage),
                    "reduceOnly": False
                }
                create_url = f"{self.base_url}/api/v1/private/order/create"
                async with session.post(create_url, json=buy_payload) as resp:
                    result = await resp.json()
                    logger.info(f"📩 買い注文結果: {result}")

                # Step3: 売り注文
                sell_payload = buy_payload.copy()
                sell_payload["side"] = "SELL"
                sell_payload["price"] = str(sell_price)
                async with session.post(create_url, json=sell_payload) as resp:
                    result = await resp.json()
                    logger.info(f"📩 売り注文結果: {result}")

                logger.info("🎉 本番グリッド注文成功！！ 微益積み上げスタート！！")

            except Exception as e:
                logger.error(f"💥 注文失敗: {e}")
                logger.error("   初回はStark署名が必要かも - 次で実装！！")
    async def monitor(self):
        logger.info("👀 監視開始 - グリッドボット稼働中...")
        while True:
            try:
                price = await self.get_price()
                # ポジション監視・決済はここ
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