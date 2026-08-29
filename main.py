"""
Точка входа. Раз в CHECK_INTERVAL_SECONDS:
  1. тянет данные по каждому символу со всех доступных бирж из топ-10
  2. считает сигнал (LONG/SHORT/NONE) через strategy.py
  3. если скор >= MIN_CONFIDENCE_SCORE — шлёт алерт в Telegram
  4. если AUTO_TRADE_DEMO=true — открывает пробную позицию на Bybit demo
  5. логирует всё в signals_log.csv для честного подсчёта win-rate

Запуск: python main.py
Остановка: Ctrl+C
"""
import logging
import time
import sys

import config
from exchanges import fetch_multi_exchange
from strategy import build_signal, HIGHER_TIMEFRAME_MAP
from telegram_notify import send_message, format_signal_message
from logger_csv import log_signal
from funding_oi import get_funding_and_oi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


def process_symbol(symbol: str):
    logger.info(f"Анализ {symbol}...")
    data = fetch_multi_exchange(symbol, config.TIMEFRAME)
    if not data:
        logger.warning(f"{symbol}: нет данных ни с одной биржи, пропуск")
        return

    htf = HIGHER_TIMEFRAME_MAP.get(config.TIMEFRAME)
    htf_data = fetch_multi_exchange(symbol, htf) if htf else None

    base_symbol = symbol  # уже в формате BTC/USDT
    funding_info = get_funding_and_oi(base_symbol)

    signal = build_signal(symbol, data, htf_data=htf_data, funding_info=funding_info)
    if signal is None or signal.direction == "NONE":
        reason = getattr(signal, "filtered_out_reason", None) if signal else None
        if reason:
            logger.info(f"{symbol}: сигнал заглушен фильтром — {reason}")
        else:
            logger.info(f"{symbol}: явного сигнала нет")
        return

    logger.info(f"{symbol}: {signal.direction}, score={signal.score}")

    demo_result = None
    if signal.score >= config.MIN_CONFIDENCE_SCORE:
        if config.AUTO_TRADE_DEMO:
            from bybit_demo import place_market_order
            demo_result = place_market_order(
                symbol=symbol,
                direction=signal.direction,
                qty_usdt=config.POSITION_SIZE_USDT,
                price=signal.price,
                atr=signal.atr,
                leverage=config.LEVERAGE,
            )
            logger.info(f"{symbol}: демо-сделка -> {demo_result}")

        message = format_signal_message(signal, demo_result)
        send_message(message)
        log_signal(signal, demo_result or "")
    else:
        logger.info(f"{symbol}: скор {signal.score} ниже порога {config.MIN_CONFIDENCE_SCORE}, алерт не шлём")


def main_loop():
    logger.info("Бот запущен. Символы: %s. Таймфрейм: %s. Интервал: %sс. Авто-торговля demo: %s",
                config.SYMBOLS, config.TIMEFRAME, config.CHECK_INTERVAL_SECONDS, config.AUTO_TRADE_DEMO)

    send_message(
        f"🤖 Бот запущен.\nСимволы: {', '.join(config.SYMBOLS)}\n"
        f"Таймфрейм: {config.TIMEFRAME}\nАвто-торговля demo: {config.AUTO_TRADE_DEMO}"
    )

    while True:
        for symbol in config.SYMBOLS:
            try:
                process_symbol(symbol)
            except Exception as e:
                logger.exception(f"Ошибка обработки {symbol}: {e}")
        logger.info(f"Цикл завершён, спим {config.CHECK_INTERVAL_SECONDS}с")
        time.sleep(config.CHECK_INTERVAL_SECONDS)


def run_once():
    """Для запуска через cron / GitHub Actions без постоянного процесса."""
    for symbol in config.SYMBOLS:
        try:
            process_symbol(symbol)
        except Exception as e:
            logger.exception(f"Ошибка обработки {symbol}: {e}")


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_once()
    else:
        try:
            main_loop()
        except KeyboardInterrupt:
            logger.info("Остановлено пользователем")
