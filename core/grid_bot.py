"""
Captain Grid Bot - $17微益モード版
半損許容・毎日稼ぐ・最小ロット強制配置
EdgeX SDK 0.3.0 2026年1月API仕様完全対応版
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from edgex_sdk import Client, OrderSide
from utils.logger import setup_logger, send_slack_notification

logger = setup_logger()

class CaptainGridBot:
    """$17微益モード版グリッドボット"""
    
    def __init__(self, config: Dict):
        """初期化"""
        self.config = config
        
        # Account ID整数化
        account_id = config["account_id"]
        if isinstance(account_id, str):
            account_id = int(account_id)
        self.account_id = account_id
        
        self.client = Client(
            base_url=config["base_url"],
            account_id=account_id,
            stark_private_key=config["stark_private_key"]
        )
        
        # BTC-USDT固定（string化 - 2026年API仕様）
        self.contract_id = "10000001"  # ← stringに変更
        self.symbol = config["symbol"]
        
        # 基本設定
        self.initial_balance = float(config.get("initial_balance", 43.0))
        self.order_size_usdt = float(config["order_size_usdt"])
        self.slack_webhook = config.get("slack_webhook")
        
        # EdgeX仕様
        self.min_size = 0.001
        self.leverage = 100
        
        # 微益モード設定
        self.grid_interval_percentage = float(config.get("grid_interval_percentage", 0.0006))
        self.force_min_order = bool(config.get("force_min_order", True))
        
        # 安全機能設定
        self.volatility_threshold = float(config.get("volatility_threshold", 0.03))
        self.volatility_check_interval = int(config.get("volatility_check_interval", 30))
        self.gradual_decline_threshold = float(config.get("gradual_decline_threshold", 0.01))
        self.gradual_decline_window = int(config.get("gradual_decline_window", 600))
        self.loss_limit = float(config.get("loss_limit", 0.50))
        self.max_net_position_btc = float(config.get("max_net_position_btc", 0.01))
        self.position_imbalance_limit = int(config.get("position_imbalance_limit", 3))
        
        # 自動復帰設定
        self.cooldown_period_minutes = int(config.get("cooldown_period_minutes", 45))
        self.max_cooldown_minutes = int(config.get("max_cooldown_minutes", 75))
        self.stability_check_period_minutes = int(config.get("stability_check_period_minutes", 60))
        self.stability_threshold = float(config.get("stability_threshold", 0.02))
        self.min_resume_balance = float(config.get("min_resume_balance", 8.5))
        self.max_consecutive_errors = int(config.get("max_consecutive_errors", 5))
        self.force_resume_after_max = bool(config.get("force_resume_after_max", True))
        
        # Phase設定
        self.grid_count_phase1 = int(config.get("grid_count_phase1", 2))
        self.grid_count_phase2 = int(config.get("grid_count_phase2", 3))
        self.phase2_threshold = float(config.get("phase2_threshold", 20.0))
        self.phase3_threshold = float(config.get("phase3_threshold", 30.0))
        
        # 状態管理
        self.trading_paused = False
        self.pause_start_time: Optional[datetime] = None
        self.pause_reason = ""
        self.consecutive_errors = 0
        self.last_valid_price: Optional[float] = None
        self.last_valid_balance: Optional[float] = None
        self.price_history: List[Tuple[datetime, float]] = []
        self.previous_price: Optional[float] = None
        self.current_phase = 1
        self.current_grid_count: Optional[int] = None
        self.current_grid_interval: Optional[float] = None
        
        logger.info(f"🚀 Captain Grid Bot - $17微益モード版 初期化完了")
        logger.info(f"📊 Phase1: {self.grid_count_phase1}本グリッド")
        logger.info(f"📊 Phase2: {self.grid_count_phase2}本グリッド")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
        logger.info(f"📏 最小ロット: {self.min_size} BTC")
        logger.info(f"🎯 毎日目標: $0.001-0.01の微益！！")

    async def get_balance(self) -> float:
        """残高取得（2026年API仕様完全対応）"""
        try:
            acc = await self.client.get_account_asset(account_id=self.account_id)
            
            if not isinstance(acc, dict) or acc.get("code") != "SUCCESS":
                logger.warning(f"⚠️ 残高取得失敗: {acc}")
                return self.last_valid_balance or 0.0
            
            collateral_list = acc.get("data", {}).get("collateralList", [])
            
            for item in collateral_list:
                if str(item.get("coinId")) == "USDT":
                    balance = float(item.get("amount", "0"))
                    if balance >= 0:
                        self.last_valid_balance = balance
                        logger.debug(f"💰 USDT残高: ${balance:.4f}")
                        return balance
            
            logger.warning("⚠️ USDT残高が見つかりません")
            return self.last_valid_balance or 0.0
            
        except Exception as e:
            logger.error(f"❌ 残高取得エラー: {e}")
            return self.last_valid_balance or 0.0

    async def check_position_imbalance(self) -> Tuple[bool, int]:
        """アクティブ注文から偏りチェック"""
        try:
            orders_resp = await self.client.get_active_orders(
                account_id=self.account_id,
                filter_contract_id_list=[int(self.contract_id)],  # intに変換して渡す
                size=50
            )
            
            if not isinstance(orders_resp, dict) or orders_resp.get("code") != "SUCCESS":
                logger.warning(f"⚠️ 注文取得失敗: {orders_resp}")
                return False, 0
            
            orders = orders_resp.get("data", [])
            # contract_idは文字列で比較
            filtered_orders = [o for o in orders if str(o.get("contractId")) == self.contract_id]
            
            buy_count = sum(1 for o in filtered_orders if o.get("side") in ["BUY", 1])
            sell_count = sum(1 for o in filtered_orders if o.get("side") in ["SELL", 2])
            
            imbalance = buy_count - sell_count
            
            if abs(imbalance) >= self.position_imbalance_limit:
                logger.warning(f"⚠️ ポジション偏り: 買い{buy_count} vs 売り{sell_count} (差={imbalance})")
                return True, imbalance
            
            return False, imbalance
            
        except Exception as e:
            logger.error(f"❌ 偏りチェックエラー: {e}")
            return False, 0

    async def cancel_all(self):
        """全注文キャンセル（2026年API仕様対応）"""
        try:
            logger.info("🗑️ 全注文キャンセル開始...")
            
            # アクティブ注文取得
            orders_resp = await self.client.get_active_orders(
                account_id=self.account_id,
                filter_contract_id_list=[int(self.contract_id)],
                size=50
            )
            
            if not isinstance(orders_resp, dict) or orders_resp.get("code") != "SUCCESS":
                logger.warning(f"⚠️ 注文取得失敗: {orders_resp}")
                return
            
            orders = orders_resp.get("data", [])
            filtered_orders = [o for o in orders if str(o.get("contractId")) == self.contract_id]
            
            if not filtered_orders:
                logger.info("📝 キャンセル対象の注文なし")
                return
            
            logger.info(f"🗑️ {len(filtered_orders)}件の注文をキャンセル中...")
            
            for order in filtered_orders:
                try:
                    order_id = str(order.get("orderId"))
                    await self.client.cancel_order(
                        contract_id=self.contract_id,
                        order_id=order_id
                    )
                    logger.debug(f"✅ キャンセル完了: {order_id}")
                    await asyncio.sleep(0.2)  # Rate limit対策
                except Exception as e:
                    logger.error(f"❌ 注文キャンセル失敗 ({order_id}): {e}")
            
            logger.info("✅ 全注文キャンセル完了")
            
        except Exception as e:
            logger.error(f"❌ 全注文キャンセルエラー: {e}")

    def update_phase(self, balance: float):
        """Phase自動更新"""
        old_phase = self.current_phase
        if balance >= self.phase3_threshold:
            self.current_phase = 3
        elif balance >= self.phase2_threshold:
            self.current_phase = 2
        else:
            self.current_phase = 1
        
        if old_phase != self.current_phase:
            logger.info(f"🎯 Phase {old_phase} → Phase {self.current_phase} 切り替え！")

    def calculate_grid_settings(self, balance: float, btc_price: float) -> Tuple[int, float]:
        """Phase対応のグリッド設定計算"""
        self.update_phase(balance)
        
        if self.current_phase == 1:
            grid_count = self.grid_count_phase1
            interval_pct = self.grid_interval_percentage
        elif self.current_phase == 2:
            grid_count = self.grid_count_phase2
            interval_pct = 0.0005
        else:
            grid_count = 4
            interval_pct = 0.0004
        
        grid_interval = btc_price * interval_pct
        
        logger.info(f"🎯 Phase {self.current_phase}: {grid_count}本 × ${grid_interval:.1f}間隔")
        return grid_count, grid_interval

    async def get_price(self) -> Optional[float]:
        """現在価格取得（aiohttp直叩き）"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.config['base_url']}/api/v1/public/ticker?contractId={self.contract_id}"
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("code") == "SUCCESS":
                            price_data = data.get("data", {})
                            price = price_data.get("markPrice") or price_data.get("lastPrice")
                            if price:
                                price_float = float(price)
                                self.last_valid_price = price_float
                                return price_float
            
            logger.warning(f"⚠️ 価格取得失敗")
            return self.last_valid_price
            
        except Exception as e:
            logger.error(f"❌ 価格取得エラー: {e}")
            return self.last_valid_price

    async def place_grid(self, center_price: float):
        """グリッド配置（微益モード）"""
        if not self.current_grid_count or not self.current_grid_interval:
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(balance, center_price)
        
        has_imbalance, imbalance = await self.check_position_imbalance()
        
        center_price = float(center_price)
        grid_interval = float(self.current_grid_interval)
        base_size = self.order_size_usdt / center_price
        
        placed = 0
        forced = 0
        
        for i in range(1, self.current_grid_count + 1):
            buy_price = round(center_price - i * grid_interval, 1)
            sell_price = round(center_price + i * grid_interval, 1)
            
            size = max(base_size, self.min_size) if (self.force_min_order and placed == 0) else base_size
            if size < self.min_size:
                if self.force_min_order and placed == 0:
                    size = self.min_size
                    forced += 1
                else:
                    continue
            
            size_str = f"{size:.8f}".rstrip('0').rstrip('.')
            
            # 買い注文
            if not (has_imbalance and imbalance >= self.position_imbalance_limit):
                try:
                    await self.client.create_limit_order(
                        contract_id=self.contract_id,
                        size=size_str,
                        price=f"{buy_price:.1f}",
                        side=OrderSide.BUY
                    )
                    placed += 1
                    logger.info(f"✅ 買い注文: {size_str} BTC @ ${buy_price:.1f}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ 買い注文失敗: {e}")
            
            # 売り注文
            if not (has_imbalance and imbalance <= -self.position_imbalance_limit):
                try:
                    await self.client.create_limit_order(
                        contract_id=self.contract_id,
                        size=size_str,
                        price=f"{sell_price:.1f}",
                        side=OrderSide.SELL
                    )
                    placed += 1
                    logger.info(f"✅ 売り注文: {size_str} BTC @ ${sell_price:.1f}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ 売り注文失敗: {e}")
            
            if forced > 0:
                break
        
        logger.info(f"🎯 グリッド配置完了: {placed}件（強制配置: {forced}件）")

    async def run(self):
        """メインループ（main.pyから呼び出し）"""
        # main.pyでループ管理するため、ここは空のまま
        pass