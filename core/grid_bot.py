    async def get_price(self) -> Optional[float]:
        """現在価格取得（2026年仕様 - aiohttp直叩き）"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.client.base_url}/api/v1/public/ticker?contractId={self.contract_id}"
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price_data = data.get("data", {})
                        price = price_data.get("markPrice") or price_data.get("lastPrice")
                        if price:
                            price_float = float(price)
                            self.last_valid_price = price_float
                            return price_float
        except Exception as e:
            logger.error(f"❌ 価格取得エラー: {e}")
        return self.last_valid_price