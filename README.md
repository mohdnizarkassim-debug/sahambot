# 🤖 SahamBot MY v2.0 — Pilot Project

Bot analisa teknikal saham Bursa Malaysia dengan sistem adaptive candle.

---

## 📁 Struktur Fail

```
sahambot_v2/
├── bot.py          # Main bot — conversation flow
├── analisa.py      # Adaptive analysis engine (5–10 candle)
├── database.py     # SQLite — users, usage, pilot log
├── admin.py        — Admin tool + pilot stats
├── requirements.txt
└── README.md
```

---

## 🚀 Setup

```bash
pip install -r requirements.txt
# Edit TOKEN dalam bot.py
python bot.py
```

---

## 💬 Commands

| Command | Fungsi |
|---|---|
| `/start` | Register & welcome |
| `/analisa` | Mula analisa (conversation flow) |
| `/ticker MAYBANK` | Set nama ticker |
| `/status` | Semak tier & usage |
| `/upgrade` | Info plan |
| `/help` | Panduan |
| `/cancel` | Batal analisa |

---

## 🕯️ Sistem Candle

User bebas pilih 5–10 candle. Bot akan explain kesan setiap pilihan:

| Candle | RSI | MACD | Bollinger | Fibonacci |
|---|---|---|---|---|
| 5 | Estimated | ❌ | ❌ | ❌ |
| 6–7 | Acceptable | Weak | ❌ | ❌ |
| 8–9 | Reliable | OK | Acceptable | Terhad |
| 10 | Paling tepat | Reliable | Reliable | ✅ |

---

## 🎯 Tier Access

| Feature | Free | Premium | Pro |
|---|---|---|---|
| Daily | ✅ 5 candle | ✅ 5–10 | ✅ 5–10 |
| Weekly | ❌ | ✅ | ✅ |
| Monthly | ❌ | ✅ | ✅ |
| Yearly | ❌ | ❌ | ✅ |
| MTF | ❌ | ❌ | ✅ |
| CSV Upload | ❌ | ✅ | ✅ |
| MACD + BB | ❌ | ✅ | ✅ |
| Risk Management | ❌ | ❌ | ✅ |
| Had harian | 3x | ∞ | ∞ |

---

## 👑 Admin Commands

```bash
python admin.py activate 123456789    # Set Premium
python admin.py pro 123456789         # Set Pro
python admin.py deactivate 123456789  # Set Free
python admin.py check 123456789       # Semak user
python admin.py stats                 # Pilot stats
```

---

## 📊 Pilot Stats (3 Bulan)

Setiap analisa dilog secara automatik. Review stats:

```bash
python admin.py stats
```

Output:
- Total users & conversion rate
- Timeframe paling popular
- Bilangan candle paling kerap dipilih
- CSV vs manual usage

---

## 🚢 Deploy

**Railway.app (Recommended):**
1. Push ke GitHub
2. Connect Railway
3. Add env: `BOT_TOKEN=your_token`
4. Deploy

---

## ⚠️ Disclaimer

Analisa ini untuk tujuan pembelajaran sahaja. Bukan nasihat pelaburan rasmi.
