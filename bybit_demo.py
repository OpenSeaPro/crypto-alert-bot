"""
Работа с Bybit Demo Trading (официальный demo-контур Bybit, реальные деньги не используются).

Важно: ключ должен быть создан именно в режиме "Demo Trading" в интерфейсе Bybit
(переключатель аккаунта -> Demo Trading -> API), а не в Testnet и не в обычном
режиме — иначе будет ошибка авторизации домена.
"""
import logging
from pybit.unified_trading import HTTP

import config

logger = logging.getLogger("bybit_demo")

_session = None


def get_session() -> HTTP | None:
    global _session
    if _session is not None:
        return _session
    if not config.BYBIT_DEMO_API_KEY or not config.BYBIT_DEMO_API_SECRET:
        logger.warning("Bybit demo API ключи не заданы — торговля отключена")
        return None
    _session = HTTP(
        testnet=False,
        demo=True,  # ключевой флаг: направляет запросы на api-demo.bybit.com
        api_key=config.BYBIT_DEMO_API_KEY,
        api_secret=config.BYBIT_DEMO_API_SECRET,
    )
    return _session


def to_bybit_symbol(ccxt_symbol: str) -> str:
    """BTC/USDT -> BTCUSDT"""
    return ccxt_symbol.replace("/", "")


def set_leverage(symbol: str, leverage: int) -> None:
    session = get_session()
    if session is None:
        return
    try:
        session.set_leverage(
            category="linear",
            symbol=to_bybit_symbol(symbol),
            buyLeverage=str(leverage),
            sellLeverage=str(leverage),
        )
    except Exception as e:
        # Часто прилетает "leverage not modified", если уже выставлено — это не ошибка
        logger.info(f"set_leverage {symbol}: {e}")


def place_market_order(symbol: str, direction: str, qty_usdt: float, price: float,
                        atr: float, leverage: int) -> str:
    """
    Открывает рыночную позицию на демо-счёте со стопом и тейком на основе ATR.
    Возвращает текстовое описание результата (для алерта в Telegram).
    """
    session = get_session()
    if session is None:
        return "пропущено (нет ключей демо-счёта)"

    bybit_symbol = to_bybit_symbol(symbol)
    set_leverage(symbol, leverage)

    side = "Buy" if direction == "LONG" else "Sell"
    qty_coin = round((qty_usdt * leverage) / price, 5)

    # Стоп/тейк на основе волатильности (ATR): SL = 1.5*ATR, TP = 3*ATR (RR 1:2)
    if direction == "LONG":
        stop_loss = round(price - 1.5 * atr, 4)
        take_profit = round(price + 3 * atr, 4)
    else:
        stop_loss = round(price + 1.5 * atr, 4)
        take_profit = round(price - 3 * atr, 4)

    try:
        result = session.place_order(
            category="linear",
            symbol=bybit_symbol,
            side=side,
            orderType="Market",
            qty=str(qty_coin),
            stopLoss=str(stop_loss),
            takeProfit=str(take_profit),
            timeInForce="IOC",
        )
        order_id = result.get("result", {}).get("orderId", "?")
        return (f"открыта {direction} {qty_coin} {bybit_symbol} @~{price}, "
                f"SL={stop_loss}, TP={take_profit}, orderId={order_id}")
    except Exception as e:
        logger.error(f"Ошибка открытия ордера {symbol}: {e}")
        return f"ОШИБКА: {e}"


def get_wallet_balance() -> str:
    session = get_session()
    if session is None:
        return "нет данных (ключи не заданы)"
    try:
        result = session.get_wallet_balance(accountType="UNIFIED")
        coins = result["result"]["list"][0]["coin"]
        usdt = next((c for c in coins if c["coin"] == "USDT"), None)
        if usdt:
            return f"{float(usdt['walletBalance']):.2f} USDT (equity: {float(usdt['equity']):.2f})"
        return "USDT баланс не найден"
    except Exception as e:
        return f"ошибка получения баланса: {e}"
