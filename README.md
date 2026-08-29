# Crypto Alert Bot

Бот мониторит цены по топ-10 биржам (через `ccxt`), считает технический сигнал
(EMA/RSI/MACD/объём + согласие бирж между собой), шлёт алерты в Telegram и
опционально открывает пробные позиции на **демо-счёте Bybit** (не реальные деньги).

## ⚠️ Важные честные ограничения

- **Скор 0–100 в алертах — это НЕ вероятность.** Это внутренняя эвристическая
  мера согласованности индикаторов, а не статистически откалиброванный прогноз.
  Никакая система не даёт 90%+ точность угадывания направления на крипторынке —
  это касается и этого бота, и любых платных сервисов.
- Единственный способ узнать **реальную** эффективность — копить сделки в
  `signals_log.csv` и `analyze_performance.py` минимум несколько недель на
  разных рыночных условиях, а не судить по паре первых сделок.
- Стратегия — это отправная точка (трендовые EMA + RSI + MACD + подтверждение
  объёмом и мульти-биржевым консенсусом), а не готовый Грааль. Параметры в
  `.env` (`MIN_CONFIDENCE_SCORE`, таймфрейм, список пар) стоит подбирать и
  тестировать под свой риск-профиль.
- Это НЕ финансовый совет. Ответственность за любые решения — на вас.

## Установка

```bash
git clone <этот проект> crypto-alert-bot
cd crypto-alert-bot
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Заполните `.env`:

1. **Telegram**: создайте бота через [@BotFather](https://t.me/BotFather),
   получите токен. Узнайте свой `chat_id` через [@userinfobot](https://t.me/userinfobot).
2. **Bybit Demo**: в приложении/на сайте Bybit переключите аккаунт в режим
   **Demo Trading** (не Testnet!), затем в этом режиме создайте API-ключ
   (Profile → API → Create API Key). Это отдельный контур с виртуальным
   балансом — реальные деньги не затрагиваются.

## Запуск

```bash
# Постоянный процесс (бесконечный цикл с паузами)
python main.py

# Разовый прогон (для cron / GitHub Actions)
python main.py --once
```

Проверка реальной статистики по демо-сделкам:

```bash
python analyze_performance.py
```

## Варианты бесплатного хостинга

По-настоящему бесплатный **вечный** 24/7-процесс — редкость почти на любой
платформе (это ограничение самих хостингов, не бота). Рабочие варианты:

### 1. GitHub Actions (рекомендую — реально бесплатно и стабильно)
Бот запускается по расписанию (`--once`), а не живёт постоянно — это как раз
подходит под режим "проверить рынок раз в N минут".

`.github/workflows/bot.yml`:
```yaml
name: crypto-alert-bot
on:
  schedule:
    - cron: "*/15 * * * *"   # каждые 15 минут
  workflow_dispatch: {}
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python main.py --once
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          BYBIT_DEMO_API_KEY: ${{ secrets.BYBIT_DEMO_API_KEY }}
          BYBIT_DEMO_API_SECRET: ${{ secrets.BYBIT_DEMO_API_SECRET }}
          SYMBOLS: "BTC/USDT,ETH/USDT,SOL/USDT"
          TIMEFRAME: "15m"
          MIN_CONFIDENCE_SCORE: "70"
          AUTO_TRADE_DEMO: "true"
```
Секреты добавляются в Settings → Secrets and variables → Actions.

### 2. Oracle Cloud Free Tier
Даёт полноценную бесплатную VPS "навсегда" (в отличие от триалов других
облаков) — можно держать `python main.py` постоянно запущенным через
`systemd` или `tmux`/`screen`.

### 3. Railway / Render (free tier)
Просто, но у бесплатных планов обычно есть засыпание процесса при
неактивности — для крипто-мониторинга 24/7 не идеально, но подходит для
тестового периода.

## Структура проекта

| Файл | Назначение |
|---|---|
| `config.py` | загрузка настроек из `.env` |
| `exchanges.py` | получение свечей с топ-10 бирж через `ccxt` |
| `indicators.py` | EMA, RSI, MACD, ATR |
| `strategy.py` | расчёт сигнала и скора уверенности |
| `telegram_notify.py` | отправка алертов |
| `bybit_demo.py` | открытие пробных позиций на демо-счёте Bybit |
| `logger_csv.py` | логирование сигналов в `signals_log.csv` |
| `analyze_performance.py` | подсчёт реального win-rate и PnL по демо-счёту |
| `main.py` | точка входа / цикл |

## Дальнейшие шаги, которые стоит сделать самому

- Погонять минимум 2–4 недели на демо в разных рыночных условиях, прежде
  чем доверять сигналам.
- Добавить фильтр по новостному/макро-фону (например, не торговать за
  30 минут до заседаний ФРС).
- Рассмотреть более строгий бэктест на исторических данных перед
  форвард-тестом (сейчас его нет — только форвард-тест на демо).
