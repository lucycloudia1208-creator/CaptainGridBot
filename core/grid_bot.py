"""
Captain Grid Bot - $17微益モード版
半損許容・毎日稼ぐ・最小ロット強制配置
EdgeX SDK 0.1.0対応
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
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
        
        self.client = Client(
            base_url=config["base_url"],
            account_id=account_id,
            stark_private_key=config["stark_private_key"]
        )
        
        # BTC-USDT固定
        self.contract_id = "10000001"
        self.symbol = config["symbol"]
        
        # 基本設定
        self.initial_balance = float(config.get("initial_balance", 17.18))
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
        self.price_history: List[tuple] = []
        self.previous_price: Optional[float] = None
        self.current_phase = 1
        
        # 動的設定
        self.current_grid_interval: Optional[float] = None
        self.current_grid_count: Optional[int] = None
        
        logger.info(f"🚀 Captain Grid Bot - $17微益モード版 初期化完了")
        logger.info(f"📊 Phase1: 2本グリッド（$17-20）")
        logger.info(f"📊 Phase2: 3本グリッド（$20-30）")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍（EdgeX設定）")
        logger.info(f"📏 最小ロット: {self.min_size} BTC")
        logger.info(f"🎯 微益モード稼働中: 毎日$0.001-0.01目標！！")
        logger.info(f"🎄 クリスマス期間: 手動監視を推奨します")
        logger.info(f"⚠️ 重要指標日: 必ず相談してから稼働！")
    
    async def get_balance(self) -> float:
        """残高取得（異常値ハンドリング付き）"""
        try:
            acc = await self.client.get_account_asset()
            
            if isinstance(acc, dict):
                collateral_list = acc.get("data", {}).get("collateralList", [])
            else:
                collateral_list = []
            
            for item in collateral_list:
                if str(item.get("coinId")) == "1000":
                    balance = float(item.get("amount", 0))
                    
                    # 異常値チェック
                    if balance < 0:
                        logger.warning(f"⚠️ 残高異常値（マイナス）: ${balance:.2f} → 前回値使用")
                        return self.last_valid_balance if self.last_valid_balance else 0.0
                    
                    if balance > self.initial_balance * 10:
                        logger.warning(f"⚠️ 残高異常値（過大）: ${balance:.2f} → 前回値使用")
                        return self.last_valid_balance if self.last_valid_balance else 0.0
                    
                    # 正常値を保存
                    self.last_valid_balance = balance
                    logger.debug(f"💰 残高確認: ${balance:.2f} USDT")
                    return balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ 残高取得エラー: {e}")
            return self.last_valid_balance if self.last_valid_balance else 0.0
    
    async def check_position_imbalance(self) -> tuple:
        """ネットポジション偏りチェック（注文本数ベース）"""
        try:
            orders_resp = await self.client.get_active_orders()
            
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("data", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp
            else:
                orders = []
            
            # contract_idでフィルタ
            filtered_orders = [o for o in orders if str(o.get("contractId")) == self.contract_id]
            
            buy_count = 0
            sell_count = 0
            
            for order in filtered_orders:
                side = order.get("side")
                if side == "BUY" or side == 1:
                    buy_count += 1
                elif side == "SELL" or side == 2:
                    sell_count += 1
            
            imbalance = buy_count - sell_count
            
            if abs(imbalance) >= self.position_imbalance_limit:
                logger.warning(f"⚠️ ポジション偏り検知: 買い{buy_count}本 vs 売り{sell_count}本")
                return True, imbalance
            
            return False, imbalance
            
        except Exception as e:
            logger.error(f"❌ 偏りチェックエラー: {e}")
            return False, 0
    
    def update_phase(self, balance: float):
        """Phaseの自動更新"""
        old_phase = self.current_phase
        
        if balance >= self.phase3_threshold:
            self.current_phase = 3
        elif balance >= self.phase2_threshold:
            self.current_phase = 2
        else:
            self.current_phase = 1
        
        if old_phase != self.current_phase:
            logger.info(f"🎯 Phase {old_phase} → Phase {self.current_phase} へ自動切り替え！")
            logger.info(f"💰 現在残高: ${balance:.2f}")
    
    def calculate_grid_settings(self, balance: float, btc_price: float) -> tuple:
        """Phase対応の動的グリッド計算"""
        
        # Phase更新
        self.update_phase(balance)
        
        # Phase別グリッド数
        if self.current_phase == 1:
            grid_count = self.grid_count_phase1  # 2本
            grid_interval = btc_price * self.grid_interval_percentage  # 0.06%
        elif self.current_phase == 2:
            grid_count = self.grid_count_phase2  # 3本
            grid_interval = btc_price * 0.0005   # 0.05%
        else:  # Phase3（将来用）
            grid_count = 4
            grid_interval = btc_price * 0.0004
        
        grid_interval = round(grid_interval, 1)  # 小数点1桁に丸め
        
        logger.info(f"📐 Phase{self.current_phase} グリッド: {grid_count}本 × ${grid_interval:.1f}幅")
        
        return grid_count, grid_interval
    
    async def get_price(self) -> Optional[float]:
        """価格取得（Binance）"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data["price"])
                        self.last_valid_price = price
                        logger.info(f"💹 価格: ${price:.2f}")
                        return price
        except Exception as e:
            logger.error(f"❌ 価格取得エラー: {e}")
        
        if self.last_valid_price:
            logger.warning(f"⚠️ 最後の有効価格使用: ${self.last_valid_price:.2f}")
            return self.last_valid_price
        
        return None
    
    def record_price(self, price: float):
        """価格履歴記録"""
        now = datetime.now()
        self.price_history.append((now, price))
        
        # 古いデータ削除（1時間以上前）
        cutoff = now - timedelta(hours=1)
        self.price_history = [(t, p) for t, p in self.price_history if t > cutoff]
    
    async def check_volatility(self, current_price: float) -> bool:
        """急落検知（30秒3%）"""
        if self.previous_price is None:
            self.previous_price = current_price
            return False
        
        price_change_rate = abs(current_price - self.previous_price) / self.previous_price
        
        if price_change_rate >= self.volatility_threshold:
            logger.critical(f"🚨 急落検知！")
            logger.critical(f"📊 前回チェックから{price_change_rate*100:.2f}%変動")
            logger.critical(f"💹 ${self.previous_price:.2f} → ${current_price:.2f}")
            await self.emergency_stop("急落検知")
            return True
        
        self.previous_price = current_price
        return False
    
    async def check_gradual_decline(self) -> bool:
        """ジワ下落検知（10分1%）"""
        if len(self.price_history) < 2:
            return False
        
        # 10分前のデータ取得
        cutoff = datetime.now() - timedelta(seconds=self.gradual_decline_window)
        old_data = [(t, p) for t, p in self.price_history if t <= cutoff]
        
        if not old_data:
            return False
        
        # 10分前の価格
        old_price = old_data[-1][1]
        current_price = self.price_history[-1][1]
        
        # 下落率計算
        decline_rate = (old_price - current_price) / old_price
        
        if decline_rate >= self.gradual_decline_threshold:
            logger.critical(f"🚨 ジワ下落検知！")
            logger.critical(f"📊 {self.gradual_decline_window//60}分で{decline_rate*100:.2f}%下落")
            logger.critical(f"💹 ${old_price:.2f} → ${current_price:.2f}")
            await self.emergency_stop("ジワ下落検知")
            return True
        
        return False
    
    async def check_loss_limit(self, balance: float) -> bool:
        """損失上限チェック（-50%）"""
        if balance < self.initial_balance * (1 - self.loss_limit):
            loss_rate = (self.initial_balance - balance) / self.initial_balance
            logger.critical(f"🚨 損失上限到達！")
            logger.critical(f"📊 損失率: {loss_rate*100:.1f}%")
            logger.critical(f"💰 ${self.initial_balance:.2f} → ${balance:.2f}")
            await self.emergency_stop(f"損失上限（-{self.loss_limit*100}%）")
            return True
        
        return False
    
    async def check_market_stability(self) -> bool:
        """市場安定性判定"""
        if len(self.price_history) < 2:
            return False
        
        cutoff = datetime.now() - timedelta(minutes=self.stability_check_period_minutes)
        recent_data = [(t, p) for t, p in self.price_history if t >= cutoff]
        
        if len(recent_data) < 2:
            return False
        
        prices = [p for _, p in recent_data]
        max_price = max(prices)
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        
        volatility = (max_price - min_price) / avg_price
        is_stable = volatility <= self.stability_threshold
        
        if is_stable:
            logger.info(f"✅ 市場安定: {self.stability_check_period_minutes}分で{volatility*100:.2f}%変動")
        else:
            logger.warning(f"⚠️ 市場不安定: {self.stability_check_period_minutes}分で{volatility*100:.2f}%変動")
        
        return is_stable
    
    async def emergency_stop(self, reason: str):
        """緊急停止"""
        logger.critical(f"🚨🚨🚨 緊急停止: {reason} 🚨🚨🚨")
        
        try:
            await self.cancel_all()
            await asyncio.sleep(1)
            
            self.trading_paused = True
            self.pause_start_time = datetime.now()
            self.pause_reason = reason
            
            logger.critical(f"⛔ 取引停止完了")
            logger.critical(f"❄️ 冷却: {self.cooldown_period_minutes}分")
            
            if self.slack_webhook:
                send_slack_notification(self.slack_webhook, f"🚨 緊急停止: {reason}")
            
        except Exception as e:
            logger.error(f"❌ 緊急停止エラー: {e}")
    
    async def auto_resume_check(self):
        """自動再開チェック"""
        if not self.trading_paused or not self.pause_start_time:
            return
        
        elapsed = (datetime.now() - self.pause_start_time).total_seconds() / 60
        
        if elapsed < self.cooldown_period_minutes:
            remaining = self.cooldown_period_minutes - elapsed
            logger.info(f"❄️ 冷却中... あと{remaining:.1f}分")
            return
        
        # 強制再開
        if elapsed >= self.max_cooldown_minutes:
            if self.force_resume_after_max:
                logger.warning(f"⚠️ 最大冷却期間到達")
                logger.info(f"🔥 強制再開")
                
                balance = await self.get_balance()
                if balance < self.min_resume_balance:
                    logger.error(f"❌ 残高不足: ${balance:.2f} < ${self.min_resume_balance}")
                    return
                
                await self.resume_trading()
                return
        
        # 通常再開
        balance = await self.get_balance()
        if balance < self.min_resume_balance:
            logger.warning(f"⚠️ 残高不足: ${balance:.2f}")
            return
        
        if await self.check_market_stability():
            logger.info(f"✅ 市場安定 → 再開！")
            await self.resume_trading()
        else:
            remaining = self.max_cooldown_minutes - elapsed
            logger.info(f"⚠️ 不安定 → 待機（あと{remaining:.1f}分で強制）")
    
    async def resume_trading(self):
        """取引再開"""
        try:
            balance = await self.get_balance()
            
            if balance < self.min_resume_balance:
                logger.error(f"❌ 残高不足: ${balance:.2f}")
                return
            
            current_price = await self.get_price()
            if not current_price:
                logger.error("❌ 価格取得失敗")
                return
            
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, current_price
            )
            
            self.trading_paused = False
            self.pause_start_time = None
            self.consecutive_errors = 0
            
            logger.info(f"✅ 取引再開！")
            logger.info(f"💰 残高: ${balance:.2f}")
            
            await self.place_grid(current_price)
            
            if self.slack_webhook:
                send_slack_notification(self.slack_webhook, f"✅ 再開: ${balance:.2f}")
            
        except Exception as e:
            logger.error(f"❌ 再開エラー: {e}")
    
    async def initialize(self):
        """初期化"""
        try:
            balance = await self.get_balance()
            
            logger.info(f"💰 USDT残高: ${balance:.2f}")
            logger.info(f"📋 契約ID: {self.contract_id}")
            
            if balance < self.min_resume_balance:
                logger.warning(f"⚠️ 残高: ${balance:.2f} < ${self.initial_balance}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 初期化エラー: {e}")
            raise
    
    async def cancel_all(self):
        """全注文キャンセル"""
        try:
            orders_resp = await self.client.get_active_orders()
            
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("data", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp
            else:
                orders = []
            
            # contract_idでフィルタ
            filtered_orders = [o for o in orders if str(o.get("contractId")) == self.contract_id]
            
            if not filtered_orders:
                logger.info("📭 キャンセル対象なし")
                return
            
            logger.info(f"🗑️ {len(filtered_orders)}件キャンセル中...")
            
            for order in filtered_orders:
                try:
                    order_id = order.get("orderId") or order.get("id")
                    if order_id:
                        await self.client.cancel_order(order_id=str(order_id))
                        await asyncio.sleep(0.2)
                except Exception as e:
                    logger.warning(f"⚠️ キャンセル失敗: {e}")
            
            logger.info("✅ キャンセル完了")
            
        except Exception as e:
            logger.error(f"❌ キャンセルエラー: {e}")
    
    async def place_grid(self, center_price: float):
        """グリッド配置（微益モード・最小ロット強制配置）"""
        if not self.current_grid_count or not self.current_grid_interval:
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, center_price
            )
        
        # ネットポジション偏りチェック
        has_imbalance, imbalance = await self.check_position_imbalance()
        
        center_price = float(center_price)
        grid_interval = float(self.current_grid_interval)
        order_size_usdt = float(self.order_size_usdt)
        
        logger.info(f"📝 グリッド配置開始")
        logger.info(f"💹 中心価格: ${center_price:.1f}")
        logger.info(f"📐 {self.current_grid_count}本 × ${grid_interval:.1f}幅")
        
        if has_imbalance:
            logger.warning(f"⚠️ ポジション偏り考慮: 差={imbalance}本")
        
        placed_count = 0
        forced_count = 0
        skipped_count = 0
        
        for i in range(1, int(self.current_grid_count) + 1):
            buy_price = round(center_price - (i * grid_interval), 1)
            sell_price = round(center_price + (i * grid_interval), 1)
            
            # 注文サイズ計算（証拠金ベース）
            size_btc = order_size_usdt / center_price
            
            # 最小ロットチェック
            if size_btc < self.min_size:
                if self.force_min_order and placed_count == 0:
                    # 1本だけ強制配置
                    logger.warning(f"⚠️ 注文サイズ不足 ({size_btc:.6f} < {self.min_size})")
                    logger.info(f"💪 微益モード: 最小ロット0.001で強制配置（1本のみ）")
                    size_btc = self.min_size
                    forced_count += 1
                else:
                    logger.warning(f"⚠️ 注文サイズ不足 ({size_btc:.6f} < {self.min_size}) → スキップ")
                    skipped_count += 1
                    continue
            
            size_btc = round(size_btc, 3)
            
            # 買い注文（偏り考慮）
            skip_buy = has_imbalance and imbalance >= self.position_imbalance_limit
            if not skip_buy:
                try:
                    await self.client.create_limit_order(
                        contract_id=str(self.contract_id),
                        size=str(size_btc),
                        price=str(round(buy_price, 1)),
                        side=OrderSide.BUY
                    )
                    placed_count += 1
                    logger.info(f"✅ 買い: {size_btc} BTC @ ${buy_price:.1f}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ 買い失敗: {e}")
            else:
                logger.warning(f"⚠️ 買い注文スキップ（ロング偏重防止）")
            
            # 売り注文（偏り考慮）
            skip_sell = has_imbalance and imbalance <= -self.position_imbalance_limit
            if not skip_sell:
                try:
                    await self.client.create_limit_order(
                        contract_id=str(self.contract_id),
                        size=str(size_btc),
                        price=str(round(sell_price, 1)),
                        side=OrderSide.SELL
                    )
                    placed_count += 1
                    logger.info(f"✅ 売り: {size_btc} BTC @ ${sell_price:.1f}")
                    await asyncio.sleep(0.3)
                except Exception as e:
                    logger.error(f"❌ 売り失敗: {e}")
            else:
                logger.warning(f"⚠️ 売り注文スキップ（ショート偏重防止）")
            
            # 強制配置は1本のみ
            if forced_count > 0:
                break
        
        if forced_count > 0:
            logger.info(f"💪 微益モード: {forced_count}本を最小ロットで強制配置！")
            logger.info(f"🎯 小幅往復で$0.001-0.01稼ぐ！")
        
        if skipped_count > 0:
            logger.info(f"📊 注文サイズ不足でスキップ: {skipped_count}件")
        
        logger.info(f"🎯 配置完了: {placed_count}件")
    
    async def run(self):
        """メインループ"""
        try:
            logger.info("=" * 60)
            logger.info("🏴‍☠️ Captain Grid Bot - $17微益伝説スタート！")
            logger.info("=" * 60)
            
            await self.initialize()
            
            price = await self.get_price()
            if not price:
                raise ValueError("初期価格取得失敗")
            
            logger.info(f"💹 現在価格: ${price:.1f}")
            
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, price
            )
            
            await self.place_grid(price)
            
            self.previous_price = price
            self.record_price(price)
            
            logger.info(f"👀 監視開始（{self.volatility_check_interval}秒ごと）...")
            
            while True:
                await asyncio.sleep(self.volatility_check_interval)
                
                try:
                    new_price = await self.get_price()
                    
                    if new_price is None:
                        self.consecutive_errors += 1
                        logger.warning(f"⚠️ 価格取得失敗（{self.consecutive_errors}/{self.max_consecutive_errors}）")
                        
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            await self.emergency_stop("連続エラー")
                        continue
                    
                    self.consecutive_errors = 0
                    self.record_price(new_price)
                    
                    # 停止中
                    if self.trading_paused:
                        logger.info(f"⛔ 停止中（{self.pause_reason}）")
                        await self.auto_resume_check()
                        continue
                    
                    # 残高チェック
                    balance = await self.get_balance()
                    
                    # === 多層防御 ===
                    
                    # 1. 急落検知
                    if await self.check_volatility(new_price):
                        continue
                    
                    # 2. ジワ下落検知
                    if await self.check_gradual_decline():
                        continue
                    
                    # 3. 損失上限
                    if await self.check_loss_limit(balance):
                        continue
                    
                    # === グリッド再配置 ===
                    
                    price_diff = abs(new_price - price)
                    threshold = self.current_grid_interval * 2.0
                    
                    if price_diff >= threshold:
                        logger.info(f"🔄 価格変動: ${price:.1f} → ${new_price:.1f}")
                        
                        await self.cancel_all()
                        await asyncio.sleep(1)
                        
                        self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                            balance, new_price
                        )
                        
                        await self.place_grid(new_price)
                        price = new_price
                    else:
                        logger.info(f"📊 ${new_price:.1f} (中心: ${price:.1f})")
                
                except Exception as e:
                    logger.error(f"❌ ループエラー: {e}")
                    self.consecutive_errors += 1
                    
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        await self.emergency_stop("連続エラー")
                    
                    await asyncio.sleep(30)
        
        except KeyboardInterrupt:
            logger.info("⛔ 手動停止")
        except Exception as e:
            logger.error(f"❌ 致命的エラー: {e}")
            raise
