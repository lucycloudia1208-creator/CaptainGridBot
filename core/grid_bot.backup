"""
価格追従型グリッドボット - Account ID整数化対応版
EdgeX SDK 0.3.0完全対応・2025年12月最新版
"""
import asyncio
import aiohttp
from typing import Dict
from edgex_sdk import Client, OrderSide
from utils.logger import setup_logger, send_slack_notification

logger = setup_logger()

class CaptainGridBot:
    """船長の価格追従型グリッドボット（低資金対応）"""
    
    def __init__(self, config: Dict):
        """初期化"""
        self.config = config
        
        # Account IDを整数型に強制変換（EdgeX SDK要件）
        account_id = config["account_id"]
        if isinstance(account_id, str):
            account_id = int(account_id)
        
        self.client = Client(
            base_url=config["base_url"],
            account_id=account_id,  # 整数型で渡す
            stark_private_key=config["stark_private_key"]
        )
        
        # BTC-USDTは常に固定
        self.contract_id = "10000001"
        self.symbol = config["symbol"]
        
        # 型を完全に保証
        self.grid_interval = float(config["grid_interval"])
        self.grid_count = int(config["grid_count"])
        self.order_size_usdt = float(config["order_size_usdt"])
        self.slack_webhook = config.get("slack_webhook")
        
        # EdgeX仕様
        self.min_size = 0.001  # 最小ロット
        self.leverage = 100    # レバレッジ
        
        logger.info(f"🚀 Captain Grid Bot 初期化完了")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {account_id} (型: {type(account_id).__name__})")
        logger.info(f"📊 シンボル: {self.symbol}")
        logger.info(f"⚙️ グリッド設定: 間隔${self.grid_interval} × {self.grid_count}本（片側）")
        logger.info(f"💵 1注文サイズ: ${self.order_size_usdt}")
        logger.info(f"📏 最小ロット: {self.min_size} BTC")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
    
    async def get_price(self) -> float:
        """現在価格を取得（Binance）"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data["price"])
                        logger.info(f"💹 価格取得成功（Binance）: ${price:.2f}")
                        return price
        except Exception as e:
            logger.error(f"❌ 価格取得エラー: {e}")
        
        raise ValueError("価格データが取得できませんでした")
    
    async def initialize(self):
        """初期化チェック"""
        try:
            acc = await self.client.get_account_asset()
            
            if isinstance(acc, dict):
                collateral_list = acc.get("data", {}).get("collateralList", [])
            else:
                collateral_list = []
            
            usdt_balance = 0.0
            for item in collateral_list:
                if str(item.get("coinId")) == "1000":
                    usdt_balance = float(item.get("amount", 0))
                    break
            
            logger.info(f"💰 USDT残高: {usdt_balance:.4f} USDT")
            logger.info(f"📋 契約ID: {self.contract_id} (BTC-USDT固定)")
            logger.info(f"⚡ レバレッジ: {self.leverage}倍（EdgeXダッシュボードで事前設定推奨）")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 初期化エラー: {e}")
            if self.slack_webhook:
                send_slack_notification(self.slack_webhook, f"❌ 初期化エラー: {e}")
            raise
    
    async def cancel_all(self):
        """全注文キャンセル"""
        try:
            orders_resp = await self.client.get_active_orders(contract_id=self.contract_id)
            
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("data", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp
            else:
                orders = []
            
            if not orders or len(orders) == 0:
                logger.info("📭 キャンセル対象の注文なし")
                return
            
            logger.info(f"🗑️ {len(orders)}件の注文をキャンセル中...")
            
            for order in orders:
                try:
                    order_id = order.get("orderId") or order.get("id")
                    if order_id:
                        await self.client.cancel_order(order_id=str(order_id))
                        await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"⚠️ 注文キャンセル失敗（継続）: {e}")
            
            logger.info("✅ 全注文キャンセル完了")
            
        except Exception as e:
            logger.error(f"❌ キャンセルエラー: {e}")
    
    async def place_grid(self, center_price: float):
        """グリッド注文配置（最小ロット0.001対応）"""
        center_price = float(center_price)
        grid_interval = float(self.grid_interval)
        order_size_usdt = float(self.order_size_usdt)
        
        logger.info(f"📝 グリッド配置開始（中心価格: ${center_price:.1f}）")
        
        placed_count = 0
        
        for i in range(1, int(self.grid_count) + 1):
            buy_price = float(center_price) - (float(i) * grid_interval)
            sell_price = float(center_price) + (float(i) * grid_interval)
            
            buy_price = round(buy_price, 1)
            sell_price = round(sell_price, 1)
            
            # サイズ計算（レバレッジ考慮）
            size_btc = (order_size_usdt * self.leverage) / center_price
            
            # 最小ロット0.001以上に調整
            if size_btc < self.min_size:
                size_btc = self.min_size
            
            size_btc = round(size_btc, 3)
            
            logger.info(f"🔍 注文準備: 買い${buy_price:.1f} / 売り${sell_price:.1f} / サイズ{size_btc} BTC")
            
            # 買い注文
            try:
                await self.client.create_limit_order(
                    contract_id=str(self.contract_id),
                    size=str(size_btc),
                    price=str(int(buy_price)),
                    side=OrderSide.BUY
                )
                placed_count += 1
                logger.info(f"✅ 買い注文成功: {size_btc} BTC @ ${buy_price:.1f}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ 買い注文失敗: {e}")
            
            # 売り注文
            try:
                await self.client.create_limit_order(
                    contract_id=str(self.contract_id),
                    size=str(size_btc),
                    price=str(int(sell_price)),
                    side=OrderSide.SELL
                )
                placed_count += 1
                logger.info(f"✅ 売り注文成功: {size_btc} BTC @ ${sell_price:.1f}")
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error(f"❌ 売り注文失敗: {e}")
        
        logger.info(f"🎯 グリッド配置完了: {placed_count}件")
        if self.slack_webhook:
            send_slack_notification(
                self.slack_webhook,
                f"✅ グリッド配置完了\n中心価格: ${center_price}\n注文数: {placed_count}件"
            )
    
    async def run(self):
        """ボットメインループ"""
        try:
            logger.info("=" * 50)
            logger.info("🏴‍☠️ Captain Grid Bot 起動！")
            logger.info("=" * 50)
            
            await self.initialize()
            
            price = await self.get_price()
            logger.info(f"💹 現在価格: ${price:.1f}")
            
            await self.place_grid(price)
            
            logger.info("👀 価格監視開始（60秒ごと）...")
            
            while True:
                await asyncio.sleep(60)
                
                try:
                    new_price = await self.get_price()
                    
                    price_diff = abs(float(new_price) - float(price))
                    threshold = float(self.grid_interval) * 2.0
                    
                    if price_diff >= threshold:
                        logger.info(f"🔄 価格変動検知: ${price:.1f} → ${new_price:.1f}")
                        
                        await self.cancel_all()
                        await asyncio.sleep(1)
                        
                        await self.place_grid(new_price)
                        price = new_price
                    else:
                        logger.info(f"📊 現在価格: ${new_price:.1f} (中心: ${price:.1f})")
                
                except Exception as e:
                    logger.error(f"❌ 監視ループエラー: {e}")
                    if self.slack_webhook:
                        send_slack_notification(self.slack_webhook, f"❌ エラー: {e}")
                    await asyncio.sleep(30)
        
        except KeyboardInterrupt:
            logger.info("⛔ ユーザーによる停止")
            if self.slack_webhook:
                send_slack_notification(self.slack_webhook, "⛔ Bot停止（手動）")
        except Exception as e:
            logger.error(f"❌ 致命的エラー: {e}")
            if self.slack_webhook:
                send_slack_notification(self.slack_webhook, f"❌ Bot停止: {e}")
            raise