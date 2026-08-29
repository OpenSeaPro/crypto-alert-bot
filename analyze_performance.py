"""
Считает реальную статистику по демо-счёту Bybit: win-rate, суммарный PnL,
количество сделок. Запускать периодически (раз в день/неделю), чтобы
увидеть настоящие цифры вместо теоретического "скора".

Запуск: python analyze_performance.py
"""
import logging

from bybit_demo import get_session, get_wallet_balance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyze")


def main():
    session = get_session()
    if session is None:
        print("Bybit demo ключи не настроены — нечего анализировать.")
        return

    print(f"Текущий баланс демо-счёта: {get_wallet_balance()}")

    try:
        result = session.get_closed_pnl(category="linear", limit=200)
        rows = result.get("result", {}).get("list", [])
    except Exception as e:
        print(f"Ошибка получения истории сделок: {e}")
        return

    if not rows:
        print("Закрытых сделок пока нет.")
        return

    total = len(rows)
    wins = sum(1 for r in rows if float(r.get("closedPnl", 0)) > 0)
    losses = total - wins
    total_pnl = sum(float(r.get("closedPnl", 0)) for r in rows)
    win_rate = (wins / total) * 100 if total else 0

    print(f"\n=== Реальная статистика демо-счёта (последние {total} сделок) ===")
    print(f"Прибыльных: {wins}   Убыточных: {losses}")
    print(f"Win-rate: {win_rate:.1f}%")
    print(f"Суммарный PnL: {total_pnl:.2f} USDT")
    print("\nЭто фактические цифры бота — именно на них стоит ориентироваться,")
    print("а не на внутренний 'скор уверенности' из strategy.py.")


if __name__ == "__main__":
    main()
