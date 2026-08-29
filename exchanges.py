"""
Получение OHLCV-данных с топ-10 бирж через ccxt.
Публичные market-data эндпоинты не требуют API-ключей.
"""
import logging
import pandas as pd
import ccxt

import config

logger = logging.getLogger("exchanges")


def get_exchange_instance(exchange_id: str):
    """Создаёт объект биржи ccxt с базовыми настройками."""
    try:
        klass = getattr(ccxt, exchange_id)
        ex = klass({
            "enableRateLimit": True,
            "timeout": 15000,
        })
        return ex
    except Exception as e:
        logger.warning(f"Не удалось создать инстанс {exchange_id}: {e}")
        return None


def fetch_ohlcv(exchange_id: str, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame | None:
    """
    Тянет свечи с одной биржи. Возвращает None, если биржа/пара недоступна
    (не все топ-10 бирж листят одни и те же пары — это нормально).
    """
    ex = get_exchange_instance(exchange_id)
    if ex is None:
        return None
    try:
        if symbol not in getattr(ex, "symbols", None) or []:
            ex.load_markets()
        if symbol not in ex.symbols:
            return None
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["exchange"] = exchange_id
        return df
    except Exception as e:
        logger.info(f"{exchange_id}/{symbol}: пропуск ({e})")
        return None


def fetch_multi_exchange(symbol: str, timeframe: str, limit: int = 200) -> dict[str, pd.DataFrame]:
    """Тянет данные по одной паре со всех бирж из config.EXCHANGES."""
    results = {}
    for ex_id in config.EXCHANGES:
        df = fetch_ohlcv(ex_id, symbol, timeframe, limit)
        if df is not None and len(df) > 20:
            results[ex_id] = df
    return results
