"""
Captain Grid Bot - $17微益モード版
半損許容・毎日稼ぐ・最小ロット強制配置
EdgeX SDK 0.1.0対応 - 2026年1月API仕様完全対応版
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
        
        self.account_id = account_id  # インスタンス変数として保存
        
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
        """残高取得（2026年1月API仕様対応・異常値ハンドリング付き）"""
        try:
            # 最新API仕様: account_idを明示的に渡す
            acc = await self.client.get_account_asset(account_id=self.account_id)
            
            if isinstance(acc, dict):
                # data.collateralList から取得
                collateral_list = acc.get("data", {}).get("collateralList", [])
            else:
                collateral_list = []
            
            # coinId == "USDT" でフィルタ（2026年1月仕様）
            for item in collateral_list:
                coin_id = str(item.get("coinId", ""))
                if coin_id == "USDT":
                    # amount は文字列で返ってくるため float() で変換
                    balance = float(item.get("amount", "0"))
                    
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
            
            # USDT が見つからない場合
            logger.warning(f"⚠️ USDT残高が見つかりません。collateralList: {collateral_list}")
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ 残高取得エラー: {e}")
            return self.last_valid_balance if self.last_valid_balance else 0.0
    
    async def check_position_imbalance(self) -> tuple:
        """ネットポジション偏りチェック（2026年1月API仕様対応・注文本数ベース）"""
        try:
            # 最新API仕様: account_id と filter_contract_id_list を必須で渡す
            orders_resp = await self.client.get_active_orders(
                account_id=self.account_id,
                filter_contract_id_list=[int(self.contract_id)],  # BTC-USDT: 10000001
                size=50  # 最大50件取得
            )
            
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("data", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp
            else:
                orders = []
            
            # contract_idでフィルタ（念のため再確認）
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
            grid_interval = btc_price * 0.0004   # 0.04%
        
        logger.info(f"🎯 Phase {self.current_phase}: {grid_count}本 × ${grid_interval:.1f}幅")
        logger.info(f"💰 残高: ${balance:.2f} USDT")
        
        return grid_count, grid_interval
    
    async def get_price(self) -> Optional[float]:
        """現在価格取得"""
        try:
            ticker = await self.client.get_ticker(contract_id=str(self.contract_id))
            
            if isinstance(ticker, dict):
                data = ticker.get("data", {})
            else:
                data = ticker if hasattr(ticker, "get") else {}
            
            # markPrice または lastPrice
            price = data.get("markPrice") or data.get("lastPrice")
            
            if price:
                price_float = float(price)
                self.last_valid_price = price_float
                return price_float
            
            return self.last_valid_price
            
        except Exception as e:
            logger.error(f"❌ 価格取得エラー: {e}")
            return self.last_valid_price
    
    def record_price(self, price: float):
        """価格履歴記録"""
        now = datetime.now()
        self.price_history.append((now, price))
        
        # 古い履歴削除（10分以上前）
        cutoff = now - timedelta(minutes=10)
        self.price_history = [
            (t, p) for t, p in self.price_history if t > cutoff
        ]
    
    async def check_volatility(self, current_price: float) -> bool:
        """急落検知（3%以上）"""
        if self.previous_price is None:
            return False
        
        change_rate = (current_price - self.previous_price) / self.previous_price
        
        if change_rate < -self.volatility_threshold:
            logger.warning(f"🚨 急落検知: {change_rate*100:.2f}%")
            await self.emergency_stop("急落検知")
            return True
        
        self.previous_price = current_price
        return False
    
    async def check_gradual_decline(self) -> bool:
        """ジワ下落検知（10分で1%以上）"""
        if len(self.price_history) < 2:
            return False
        
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.gradual_decline_window)
        
        old_prices = [p for t, p in self.price_history if t < cutoff]
        if not old_prices:
            return False
        
        oldest_price = old_prices[0]
        current_price = self.price_history[-1][1]
        
        decline_rate = (current_price - oldest_price) / oldest_price
        
        if decline_rate < -self.gradual_decline_threshold:
            logger.warning(f"🚨 ジワ下落検知: {decline_rate*100:.2f}%（{self.gradual_decline_window}秒間）")
            await self.emergency_stop("ジワ下落検知")
            return True
        
        return False
    
    async def check_loss_limit(self, balance: float) -> bool:
        """損失上限チェック（50%）"""
        loss_rate = (self.initial_balance - balance) / self.initial_balance
        
        if loss_rate >= self.loss_limit:
            logger.warning(f"🚨 損失上限到達: {loss_rate*100:.1f}%")
            await self.emergency_stop("損失上限到達")
            return True
        
        return False
    
    async def emergency_stop(self, reason: str):
        """緊急停止"""
        if self.trading_paused:
            return
        
        logger.warning(f"⛔ 緊急停止: {reason}")
        
        self.trading_paused = True
        self.pause_start_time = datetime.now()
        self.pause_reason = reason
        
        try:
            await self.cancel_all()
            logger.info("✅ 全注文キャンセル完了")
        except Exception as e:
            logger.error(f"❌ 注文キャンセル失敗: {e}")
        
        if self.slack_webhook:
            await send_slack_notification(
                self.slack_webhook,
                f"⛔ Captain Bot緊急停止: {reason}"
            )
    
    async def auto_resume_check(self):
        """自動復帰チェック"""
        if not self.trading_paused or not self.pause_start_time:
            return
        
        elapsed = datetime.now() - self.pause_start_time
        elapsed_minutes = elapsed.total_seconds() / 60
        
        # 最大待機時間超過
        if elapsed_minutes > self.max_cooldown_minutes:
            if self.force_resume_after_max:
                logger.info(f"🔄 最大待機時間超過（{elapsed_minutes:.1f}分）→ 強制復帰")
                await self.resume_trading()
            else:
                logger.warning(f"⛔ 最大待機時間超過（{elapsed_minutes:.1f}分）→ 手動復帰待ち")
            return
        
        # クールダウン期間中
        if elapsed_minutes < self.cooldown_period_minutes:
            logger.info(f"⏳ クールダウン中: {elapsed_minutes:.1f}/{self.cooldown_period_minutes}分")
            return
        
        # 安定性チェック
        cutoff = datetime.now() - timedelta(minutes=self.stability_check_period_minutes)
        recent_prices = [p for t, p in self.price_history if t > cutoff]
        
        if len(recent_prices) < 2:
            logger.info("⏳ 安定性チェック: データ不足")
            return
        
        max_price = max(recent_prices)
        min_price = min(recent_prices)
        volatility = (max_price - min_price) / min_price
        
        if volatility > self.stability_threshold:
            logger.info(f"⏳ 安定性チェック: ボラティリティ高い ({volatility*100:.2f}%)")
            return
        
        # 残高チェック
        balance = await self.get_balance()
        if balance < self.min_resume_balance:
            logger.warning(f"⛔ 残高不足で復帰不可: ${balance:.2f} < ${self.min_resume_balance}")
            return
        
        logger.info(f"✅ 安定性確認 → 自動復帰")
        await self.resume_trading()
    
    async def resume_trading(self):
        """取引再開"""
        logger.info("🔄 取引再開")
        
        self.trading_paused = False
        self.pause_start_time = None
        self.pause_reason = ""
        self.consecutive_errors = 0
        
        price = await self.get_price()
        if price:
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, price
            )
            await self.place_grid(price)
        
        if self.slack_webhook:
            await send_slack_notification(
                self.slack_webhook,
                "🔄 Captain Bot取引再開"
            )
    
    async def cancel_all(self):
        """全注文キャンセル（2026年1月API仕様対応）"""
        try:
            # 最新API仕様: account_id と filter_contract_id_list を必須で渡す
            orders_resp = await self.client.get_active_orders(
                account_id=self.account_id,
                filter_contract_id_list=[int(self.contract_id)],  # BTC-USDT: 10000001
                size=50  # 最大50件取得
            )
            
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("data", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp
            else:
                orders = []
            
            # contract_idでフィルタ（念のため再確認）
            filtered_orders = [o for o in orders if str(o.get("contractId")) == self.contract_id]
            
            if not filtered_orders:
                logger.info("📝 キャンセル対象なし")
                return
            
            logger.info(f"🗑️ {len(filtered_orders)}件キャンセル中...")
            
            for order in filtered_orders:
                try:
                    order_id = str(order.get("orderId"))
                    await self.client.cancel_order(
                        contract_id=str(self.contract_id),
                        order_id=order_id
                    )
                    logger.debug(f"✅ キャンセル: {order_id}")
                    await asyncio.sleep(0.2)  # Rate limit対策
                except Exception as e:
                    logger.error(f"❌ キャンセル失敗: {e}")
            
            logger.info("✅ 全キャンセル完了")
            
        except Exception as e:
            logger.error(f"❌ 全キャンセルエラー: {e}")
    
    async def initialize(self):
        """初期化処理"""
        logger.info("🔄 初期化中...")
        
        # 既存注文クリア
        await self.cancel_all()
        await asyncio.sleep(1)
        
        logger.info("✅ 初期化完了")
    
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
                    await asyncio.sleep(0.3)  # Rate limit対策
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
                    await asyncio.sleep(0.3)  # Rate limit対策
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
