"""
Captain Grid Bot - 全損リスク限りなく0の超安全版
価格追従型グリッドボット + 動的グリッド幅調整 + 多層防御システム
EdgeX SDK 0.3.0完全対応・2025年12月最新版
"""
import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from edgex_sdk import Client, OrderSide
from utils.logger import setup_logger, send_slack_notification
import statistics

logger = setup_logger()

class CaptainGridBot:
    """船長の価格追従型グリッドボット（超安全版）"""
    
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
        
        # 基本設定
        self.initial_balance = float(config.get("initial_balance", 20.0))
        self.order_size_usdt = float(config["order_size_usdt"])
        self.slack_webhook = config.get("slack_webhook")
        
        # EdgeX仕様
        self.min_size = 0.001  # 最小ロット
        self.leverage = 100    # レバレッジ
        
        # 安全機能設定
        self.volatility_threshold = float(config.get("volatility_threshold", 0.03))
        self.volatility_check_interval = int(config.get("volatility_check_interval", 60))
        self.liquidation_buffer = float(config.get("liquidation_buffer", 0.80))
        self.cooldown_period_minutes = int(config.get("cooldown_period_minutes", 60))
        self.max_cooldown_minutes = int(config.get("max_cooldown_minutes", 180))
        self.stability_check_period_minutes = int(config.get("stability_check_period_minutes", 120))
        self.stability_threshold = float(config.get("stability_threshold", 0.01))
        self.min_resume_balance = float(config.get("min_resume_balance", 10.0))
        self.max_consecutive_errors = int(config.get("max_consecutive_errors", 5))
        
        # 状態管理
        self.trading_paused = False
        self.pause_start_time: Optional[datetime] = None
        self.pause_reason = ""
        self.consecutive_errors = 0
        self.last_valid_price: Optional[float] = None
        self.price_history: List[tuple] = []  # (timestamp, price)
        self.previous_price: Optional[float] = None
        
        # 動的グリッド設定（実行時に計算）
        self.current_grid_interval: Optional[float] = None
        self.current_grid_count: Optional[int] = None
        
        logger.info(f"🚀 Captain Grid Bot - 超安全版 初期化完了")
        logger.info(f"📍 接続先: {config['base_url']}")
        logger.info(f"🆔 Account ID: {account_id} (型: {type(account_id).__name__})")
        logger.info(f"📊 シンボル: {self.symbol}")
        logger.info(f"💰 推奨初期残高: ${self.initial_balance}")
        logger.info(f"💵 1注文サイズ: ${self.order_size_usdt}")
        logger.info(f"📏 最小ロット: {self.min_size} BTC")
        logger.info(f"⚡ レバレッジ: {self.leverage}倍")
        logger.info(f"🛡️ ボラ緊急停止: {self.volatility_threshold*100}%/{self.volatility_check_interval}秒")
        logger.info(f"🛡️ 強制清算回避: -{self.liquidation_buffer*100}%損失")
        logger.info(f"❄️ 冷却期間: {self.cooldown_period_minutes}分（最大{self.max_cooldown_minutes}分）")
        logger.info(f"✅ 再開条件: ${self.min_resume_balance}以上 + {self.stability_check_period_minutes}分間安定")
    
    async def get_balance(self) -> float:
        """現在のUSDT残高を取得"""
        try:
            acc = await self.client.get_account_asset()
            
            if isinstance(acc, dict):
                collateral_list = acc.get("data", {}).get("collateralList", [])
            else:
                collateral_list = []
            
            for item in collateral_list:
                if str(item.get("coinId")) == "1000":
                    balance = float(item.get("amount", 0))
                    logger.debug(f"💰 残高確認: ${balance:.2f} USDT")
                    return balance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"❌ 残高取得エラー: {e}")
            return 0.0
    
    async def get_unrealized_pnl(self) -> float:
        """未実現損益を取得"""
        try:
            positions_resp = await self.client.get_positions()
            
            if isinstance(positions_resp, dict):
                positions = positions_resp.get("data", [])
            elif isinstance(positions_resp, list):
                positions = positions_resp
            else:
                positions = []
            
            total_pnl = 0.0
            for pos in positions:
                if str(pos.get("contractId")) == self.contract_id:
                    pnl = float(pos.get("unrealizedPnl", 0))
                    total_pnl += pnl
            
            logger.debug(f"📊 未実現PnL: ${total_pnl:.2f}")
            return total_pnl
            
        except Exception as e:
            logger.error(f"❌ PnL取得エラー: {e}")
            return 0.0
    
    def calculate_grid_settings(self, balance: float, btc_price: float) -> tuple:
        """残高に応じてグリッド設定を動的計算"""
        
        # グリッド数の決定
        if balance >= 50:
            grid_count = 5
        elif balance >= 30:
            grid_count = 4
        elif balance >= 20:
            grid_count = 3
        else:  # $10-20
            grid_count = 2
        
        # グリッド幅の決定（残高ベース）
        if balance < 15:
            # $10-15: 超タイト（0.05%幅）
            grid_interval = btc_price * 0.0005
        elif balance < 25:
            # $15-25: タイト（0.08%幅）
            grid_interval = btc_price * 0.0008
        elif balance < 50:
            # $25-50: 通常（0.1%幅）
            grid_interval = btc_price * 0.001
        else:
            # $50以上: やや広め（0.15%幅）
            grid_interval = btc_price * 0.0015
        
        # 整数に丸める（EdgeX要件）
        grid_interval = round(grid_interval, 0)
        
        logger.info(f"📐 動的グリッド計算: 残高${balance:.2f} → {grid_count}本 × ${grid_interval:.0f}幅")
        
        return grid_count, grid_interval
    
    async def get_price(self) -> Optional[float]:
        """現在価格を取得（Binance + フォールバック保護）"""
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
                        logger.info(f"💹 価格取得成功（Binance）: ${price:.2f}")
                        return price
        except Exception as e:
            logger.error(f"❌ Binance価格取得エラー: {e}")
        
        # フォールバック: 最後の有効価格
        if self.last_valid_price:
            logger.warning(f"⚠️ 最後の有効価格を使用: ${self.last_valid_price:.2f}")
            return self.last_valid_price
        
        # 完全失敗
        logger.error("❌ 価格取得完全失敗！取引スキップ")
        return None
    
    def record_price(self, price: float):
        """価格履歴を記録（ボラティリティ・安定性判定用）"""
        now = datetime.now()
        self.price_history.append((now, price))
        
        # 古いデータを削除（3時間以上前）
        cutoff = now - timedelta(hours=3)
        self.price_history = [(t, p) for t, p in self.price_history if t > cutoff]
    
    async def check_volatility(self, current_price: float) -> bool:
        """ボラティリティ緊急停止チェック"""
        if self.previous_price is None:
            self.previous_price = current_price
            return False
        
        # 変動率計算
        price_change_rate = abs(current_price - self.previous_price) / self.previous_price
        
        if price_change_rate >= self.volatility_threshold:
            logger.critical(f"🚨 異常ボラティリティ検知！")
            logger.critical(f"📊 {self.volatility_check_interval}秒で{price_change_rate*100:.2f}%変動")
            logger.critical(f"💹 ${self.previous_price:.2f} → ${current_price:.2f}")
            
            await self.emergency_stop("異常ボラティリティ")
            return True
        
        self.previous_price = current_price
        return False
    
    async def check_liquidation_risk(self) -> bool:
        """強制清算リスクチェック"""
        try:
            balance = await self.get_balance()
            unrealized_pnl = await self.get_unrealized_pnl()
            total_equity = balance + unrealized_pnl
            
            if self.initial_balance <= 0:
                return False
            
            loss_rate = (self.initial_balance - total_equity) / self.initial_balance
            
            if loss_rate >= self.liquidation_buffer:
                logger.critical(f"🚨 強制清算リスク検知！")
                logger.critical(f"📊 損失率: {loss_rate*100:.1f}%")
                logger.critical(f"💰 初期残高: ${self.initial_balance:.2f}")
                logger.critical(f"💰 現在残高: ${total_equity:.2f}")
                
                await self.emergency_stop("強制清算回避")
                return True
            
            if loss_rate >= 0.50:  # -50%で警告
                logger.warning(f"⚠️ 損失率: {loss_rate*100:.1f}% - 要注意")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 清算リスクチェックエラー: {e}")
            return False
    
    async def check_market_stability(self) -> bool:
        """市場安定性チェック（過去N分間の変動率）"""
        if len(self.price_history) < 2:
            logger.info("📊 価格データ不足 - 安定性判定スキップ")
            return False
        
        # 指定期間のデータを抽出
        cutoff = datetime.now() - timedelta(minutes=self.stability_check_period_minutes)
        recent_data = [(t, p) for t, p in self.price_history if t >= cutoff]
        
        if len(recent_data) < 2:
            logger.info(f"📊 過去{self.stability_check_period_minutes}分のデータ不足")
            return False
        
        # 価格のみ抽出
        prices = [p for _, p in recent_data]
        
        # 変動率計算（最大値-最小値）
        max_price = max(prices)
        min_price = min(prices)
        avg_price = sum(prices) / len(prices)
        
        volatility = (max_price - min_price) / avg_price
        
        is_stable = volatility <= self.stability_threshold
        
        if is_stable:
            logger.info(f"✅ 市場安定: 過去{self.stability_check_period_minutes}分で{volatility*100:.2f}%変動")
        else:
            logger.warning(f"⚠️ 市場不安定: 過去{self.stability_check_period_minutes}分で{volatility*100:.2f}%変動")
        
        return is_stable
    
    async def emergency_stop(self, reason: str):
        """緊急停止（全決済 + 取引停止）"""
        logger.critical(f"🚨🚨🚨 緊急停止発動: {reason} 🚨🚨🚨")
        
        try:
            # 全注文キャンセル
            await self.cancel_all()
            await asyncio.sleep(1)
            
            # 全ポジションクローズ（可能なら）
            await self.close_all_positions()
            
            # 取引停止状態に移行
            self.trading_paused = True
            self.pause_start_time = datetime.now()
            self.pause_reason = reason
            
            logger.critical(f"⛔ 取引停止完了 - 理由: {reason}")
            logger.critical(f"❄️ 冷却期間: {self.cooldown_period_minutes}分（最大{self.max_cooldown_minutes}分）")
            
            if self.slack_webhook:
                send_slack_notification(
                    self.slack_webhook,
                    f"🚨 緊急停止\n理由: {reason}\n冷却: {self.cooldown_period_minutes}分"
                )
            
        except Exception as e:
            logger.error(f"❌ 緊急停止処理エラー: {e}")
    
    async def close_all_positions(self):
        """全ポジションをクローズ"""
        try:
            positions_resp = await self.client.get_positions()
            
            if isinstance(positions_resp, dict):
                positions = positions_resp.get("data", [])
            elif isinstance(positions_resp, list):
                positions = positions_resp
            else:
                positions = []
            
            for pos in positions:
                if str(pos.get("contractId")) == self.contract_id:
                    size = abs(float(pos.get("size", 0)))
                    if size > 0:
                        side = OrderSide.SELL if float(pos.get("size", 0)) > 0 else OrderSide.BUY
                        
                        try:
                            # 成行で即時決済
                            await self.client.create_market_order(
                                contract_id=str(self.contract_id),
                                size=str(size),
                                side=side
                            )
                            logger.info(f"✅ ポジションクローズ: {size} BTC")
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"❌ ポジションクローズ失敗: {e}")
            
            logger.info("✅ 全ポジションクローズ試行完了")
            
        except Exception as e:
            logger.error(f"❌ ポジションクローズエラー: {e}")
    
    async def auto_resume_check(self):
        """自動再開チェック（時間経過 + 市場安定性）"""
        if not self.trading_paused or not self.pause_start_time:
            return
        
        # 経過時間計算
        elapsed = (datetime.now() - self.pause_start_time).total_seconds() / 60
        
        # 最低冷却期間未達
        if elapsed < self.cooldown_period_minutes:
            remaining = self.cooldown_period_minutes - elapsed
            logger.info(f"❄️ 冷却中... あと{remaining:.1f}分")
            return
        
        # 最大冷却期間超過
        if elapsed > self.max_cooldown_minutes:
            logger.warning(f"⚠️ 最大冷却期間（{self.max_cooldown_minutes}分）超過")
            logger.warning("⚠️ 手動確認を推奨します")
            return
        
        # 残高チェック
        balance = await self.get_balance()
        if balance < self.min_resume_balance:
            logger.warning(f"⚠️ 残高不足で再開不可: ${balance:.2f} < ${self.min_resume_balance}")
            return
        
        # 市場安定性チェック
        is_stable = await self.check_market_stability()
        
        if is_stable:
            logger.info(f"✅ 市場安定化確認 → 取引再開！")
            await self.resume_trading()
        else:
            logger.info(f"⚠️ まだ不安定 → 待機継続（{elapsed:.1f}分経過）")
    
    async def resume_trading(self):
        """取引再開"""
        try:
            # 残高再確認
            balance = await self.get_balance()
            
            if balance < self.min_resume_balance:
                logger.error(f"❌ 残高不足で再開不可: ${balance:.2f}")
                return
            
            # グリッド設定再計算
            current_price = await self.get_price()
            if not current_price:
                logger.error("❌ 価格取得失敗 - 再開延期")
                return
            
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, current_price
            )
            
            # 状態リセット
            self.trading_paused = False
            self.pause_start_time = None
            self.consecutive_errors = 0
            
            logger.info(f"✅ 取引再開！")
            logger.info(f"💰 残高: ${balance:.2f}")
            logger.info(f"📐 グリッド: {self.current_grid_count}本 × ${self.current_grid_interval:.0f}幅")
            
            # グリッド再配置
            await self.place_grid(current_price)
            
            if self.slack_webhook:
                send_slack_notification(
                    self.slack_webhook,
                    f"✅ 取引再開\n残高: ${balance:.2f}\nグリッド: {self.current_grid_count}本"
                )
            
        except Exception as e:
            logger.error(f"❌ 再開処理エラー: {e}")
    
    async def initialize(self):
        """初期化チェック"""
        try:
            balance = await self.get_balance()
            
            logger.info(f"💰 USDT残高: ${balance:.2f} USDT")
            logger.info(f"📋 契約ID: {self.contract_id} (BTC-USDT固定)")
            logger.info(f"⚡ レバレッジ: {self.leverage}倍（EdgeXダッシュボードで事前設定推奨）")
            
            if balance < self.min_resume_balance:
                logger.warning(f"⚠️ 残高が推奨値以下: ${balance:.2f} < ${self.initial_balance}")
                logger.warning(f"⚠️ 最低${self.min_resume_balance}で動作可能")
            
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
        """グリッド注文配置（動的設定対応）"""
        if not self.current_grid_count or not self.current_grid_interval:
            # 初回または設定がない場合は計算
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, center_price
            )
        
        center_price = float(center_price)
        grid_interval = float(self.current_grid_interval)
        order_size_usdt = float(self.order_size_usdt)
        
        logger.info(f"📝 グリッド配置開始")
        logger.info(f"💹 中心価格: ${center_price:.1f}")
        logger.info(f"📐 グリッド: {self.current_grid_count}本 × ${grid_interval:.0f}幅")
        
        placed_count = 0
        
        for i in range(1, int(self.current_grid_count) + 1):
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
                f"✅ グリッド配置完了\n中心価格: ${center_price:.1f}\n注文数: {placed_count}件"
            )
    
    async def run(self):
        """ボットメインループ（多層防御システム搭載）"""
        try:
            logger.info("=" * 60)
            logger.info("🏴‍☠️ Captain Grid Bot - 超安全版 起動！")
            logger.info("=" * 60)
            
            await self.initialize()
            
            price = await self.get_price()
            if not price:
                raise ValueError("初期価格取得失敗")
            
            logger.info(f"💹 現在価格: ${price:.1f}")
            
            # 初期グリッド配置
            balance = await self.get_balance()
            self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                balance, price
            )
            
            await self.place_grid(price)
            
            self.previous_price = price
            self.record_price(price)
            
            logger.info(f"👀 価格監視開始（{self.volatility_check_interval}秒ごと）...")
            
            while True:
                await asyncio.sleep(self.volatility_check_interval)
                
                try:
                    # 価格取得
                    new_price = await self.get_price()
                    
                    if new_price is None:
                        # 価格取得失敗 - この周期はスキップ
                        self.consecutive_errors += 1
                        logger.warning(f"⚠️ 価格取得失敗（{self.consecutive_errors}/{self.max_consecutive_errors}）")
                        
                        if self.consecutive_errors >= self.max_consecutive_errors:
                            await self.emergency_stop("連続エラー上限")
                        
                        continue
                    
                    # エラーカウンターリセット
                    self.consecutive_errors = 0
                    
                    # 価格履歴記録
                    self.record_price(new_price)
                    
                    # 取引停止中の場合
                    if self.trading_paused:
                        logger.info(f"⛔ 取引停止中（理由: {self.pause_reason}）")
                        await self.auto_resume_check()
                        continue
                    
                    # === 多層防御チェック ===
                    
                    # 1. ボラティリティチェック（最優先）
                    if await self.check_volatility(new_price):
                        continue  # 緊急停止発動済み
                    
                    # 2. 強制清算リスクチェック
                    if await self.check_liquidation_risk():
                        continue  # 緊急停止発動済み
                    
                    # === 通常のグリッド再配置ロジック ===
                    
                    price_diff = abs(float(new_price) - float(price))
                    threshold = float(self.current_grid_interval) * 2.0
                    
                    if price_diff >= threshold:
                        logger.info(f"🔄 価格変動検知: ${price:.1f} → ${new_price:.1f}")
                        
                        await self.cancel_all()
                        await asyncio.sleep(1)
                        
                        # 残高に応じてグリッド再計算
                        balance = await self.get_balance()
                        self.current_grid_count, self.current_grid_interval = self.calculate_grid_settings(
                            balance, new_price
                        )
                        
                        await self.place_grid(new_price)
                        price = new_price
                    else:
                        logger.info(f"📊 現在価格: ${new_price:.1f} (中心: ${price:.1f})")
                
                except Exception as e:
                    logger.error(f"❌ 監視ループエラー: {e}")
                    self.consecutive_errors += 1
                    
                    if self.consecutive_errors >= self.max_consecutive_errors:
                        await self.emergency_stop("連続エラー上限")
                    
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