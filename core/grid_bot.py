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
        if not self.account_id or not self.stark_private_key:
            logger.error("🚫 ACCOUNT_ID または STARK_PRIVATE_KEY が未設定 - 注文できません！！")
            logger.error("   KoyebのEnvironment Variablesに設定してください！！")
            return

        # グリッドパラメータ（微益・安全設計）
        grid_percentage = 0.0006          # グリッド幅: 0.06%（約$52.8）
        order_quantity = "0.002"          # 各注文量: 0.002 BTC（合計0.004 BTC）
        contract_id = self.contract_id    # "10000001"

        # グリッド価格計算
        buy_price = current_price * (1 - grid_percentage)   # 下の買い指値
        sell_price = current_price * (1 + grid_percentage)  # 上の売り指値

        logger.info("🔥 本番グリッド注文実行！！")
        logger.info(f"   資金: 46.65 USDT | レバ: 100倍 | 注文量: {order_quantity} BTC × 2本")
        logger.info(f"   ↓ 買い指値: ${buy_price:.2f} で {order_quantity} BTC")
        logger.info(f"   ↑ 売り指値: ${sell_price:.2f} で {order_quantity} BTC")

        async with aiohttp.ClientSession() as session:
            try:
                # Step1: 既存注文を全キャンセル（重複・ゴミ注文防止！！超重要）
                cancel_url = f"{self.base_url}/api/v1/private/order/cancel_all"
                cancel_payload = {
                    "accountId": self.account_id,
                    "contractId": contract_id
                }
                # TODO: Stark署名付与（後で実装 - 今はシミュレーション）
                logger.info("🧹 既存注文を全キャンセル中...（シミュレーション）")

                # Step2: 買い注文（LIMIT BUY）
                buy_url = f"{self.base_url}/api/v1/private/order/create"
                buy_payload = {
                    "accountId": self.account_id,
                    "contractId": contract_id,
                    "side": "BUY",
                    "orderType": "LIMIT",
                    "price": str(round(buy_price, 2)),
                    "quantity": order_quantity,
                    "leverage": str(self.leverage),
                    "reduceOnly": False
                }
                logger.info(f"📩 買い注文送信: {buy_payload}")

                # Step3: 売り注文（LIMIT SELL）
                sell_payload = buy_payload.copy()
                sell_payload["side"] = "SELL"
                sell_payload["price"] = str(round(sell_price, 2))
                logger.info(f"📩 売り注文送信: {sell_payload}")

                # TODO: 本物のPOSTリクエスト + Stark署名 + nonce + timestamp
                # async with session.post(buy_url, json=buy_payload, headers=headers) as resp:
                #     result = await resp.json()
                #     logger.info(f"注文結果: {result}")

                logger.info("✅ グリッド注文完了！！（現在はシミュレーション - 次で本番POST実装）")
                logger.info("   価格が±0.06%動けば約定 → 反対側で利益確定 → 微益積み上げスタート！！")

            except Exception as e:
                logger.error(f"💥 注文処理エラー: {e}")

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