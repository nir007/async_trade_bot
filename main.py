import os
import asyncio
import http.client
import json
from dotenv import load_dotenv
from math import fabs
import sys
import time
from aiohttp import ClientSession, TCPConnector
from aiohttp_socks import ProxyConnector

MIN_SPREAD_PERCENT = 0.01

KUCOIN_FILE_NAME = "kukion_prices.json"
BINANCE_FILE_NAME = "binance_prices.json"

BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
KUCOIN_PRICE_URL = "https://api.kucoin.com/api/v1/market/allTickers"

coins = ("BTC", "ETH", "ZRO", "STRK", "SOL", "ZK")

class TradeBot:
    def __init__(self, session: ClientSession, coins: tuple):
        self.__session = session
        self.__coins = coins

    async def get_price_from_binance(self, *, url, file_name: str):
        start = time.time()
        res = []

        async with self.__session.get(url) as resp:
            if resp.status != http.client.OK:
                raise RuntimeError(f"Bad response code: {resp.status}")

            content = await resp.json()

            for symbol in self.__coins:
                for token in content:
                    if f"{symbol}USDT" == token.get("symbol"):
                        res.append({
                            "symbol": symbol,
                            "price": token.get("price")
                        })

            self.__write_to_file(file_name=file_name, data=res)

        end = time.time()
        print(f"Request to binance: {end - start:.3f} seconds")

    async def get_price_from_kukoin(self, *, url: str, file_name: str):
        res = []
        start = time.time()

        async with self.__session.get(url) as resp:
            if resp.status != http.client.OK:
                raise RuntimeError(f"Bad response code: {resp.status}")

            content = await resp.json()

            for symbol in self.__coins:
                for token in content["data"]["ticker"]:
                    if f"{symbol}-USDT" == token['symbol']:
                        res.append({
                            "symbol": symbol,
                            "price": token["last"]
                        })

            self.__write_to_file(file_name=file_name, data=res)

        end = time.time()
        print(f"Request to kukoin: {end - start:.3f} seconds")

    def __write_to_file(self, file_name: str, data: any):
        with open(file_name, "w") as file:
            file.write(json.dumps(data, indent=4))

    def read_file(self, file_name: str):
        with open(file_name, "r") as file:
            return json.loads(file.read())

    def get_percent_spread(self, price_1, price_2: float) -> float:
        return (fabs(price_1 - price_2)) / ((price_1 + price_2) / 2) * 100

async def main():
    load_dotenv()

    proxy = os.getenv("PROXY")

    session = ClientSession(
        connector=ProxyConnector.from_url(f"http://{proxy}") if proxy else TCPConnector(),
    )

    try:
        bot = TradeBot(session=session, coins=coins)

        tasks = [
            bot.get_price_from_kukoin(url=KUCOIN_PRICE_URL, file_name=KUCOIN_FILE_NAME),
            bot.get_price_from_binance(url=BINANCE_PRICE_URL, file_name=BINANCE_FILE_NAME)
        ]

        await asyncio.gather(*tasks)

        kucoin_prices = bot.read_file(KUCOIN_FILE_NAME)
        binance_prices = bot.read_file(BINANCE_FILE_NAME)

        for k in kucoin_prices:
            for b in binance_prices:
                if k.get("symbol") ==  b.get("symbol"):
                    spread = bot.get_percent_spread(float(k.get("price")), float(b.get("price")))

                    if spread >= MIN_SPREAD_PERCENT:
                        print(f"\nНашел спред на монете {k.get('symbol')} между Binance и Kucoin.")

                        if float(k.get("price")) > float(b.get("price")):
                            print(f"Покупка: {b.get('price')}$")
                            print(f"Продажа: {k.get('price')}$")
                        else:
                            print(f"Покупка: {k.get('price')}$")
                            print(f"Продажа: {b.get('price')}$")

                        print(f"Профит: {fabs(float(k.get('price')) - float(b.get('price'))):.4f}$")
    except Exception as e:
        _, _, exc_tb = sys.exc_info()
        print(f"Something went wrong on line {exc_tb.tb_lineno}: {e}")
    finally:
        await session.close()

asyncio.run(main())





