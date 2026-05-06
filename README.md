# ⚾ Pesiksen siirtoseuranta

Seuraa automaattisesti [pesistulokset.fi/seurasiirrot](https://v1.pesistulokset.fi/seurasiirrot) -sivua ja lähettää Telegram-ilmoituksen kun uusia seurasiirtoja ilmestyy tai olemassa olevia siirtoja päivitetään.

## Miten se toimii

GitHub Actions ajaa skriptin kerran tunnissa kello 07–23 Suomen aikaa. Skripti hakee siirtosivun, vertaa sitä tallennettuun tilannekuvaan (`snapshot.json`) ja lähettää Telegram-viestin jos:

- **Uusia siirtoja** on ilmestynyt listalle
- **Olemassa olevan siirron tietoja** on päivitetty (esim. Lisätiedot-sarake, sarjatason korotus)

## Ilmoitusesimerkki

```
⚾ 2 uusi siirto pesäpallossa!

📅 06.05.2026 — Virtanen Mikko
  Sotkamon Jymy ➡️ Seinäjoen Maila-Jussit
  Täyssiirto | Hyväksytty
  Miesten Superpesis

✏️ 1 siirto päivitetty!

📅 27.1.2026 — Leskinen Janni
  Ilomantsin Urheilijat ➡️ Joensuun Maila
  📝 Lisätiedot: Siirto purettu 10.2.2026 16:37

🔗 https://v1.pesistulokset.fi/seurasiirrot
```

## Tiedostorakenne

```
├── check_transfers.py        # Pääskripti: hakee siirrot, vertaa ja ilmoittaa
├── snapshot.json             # Viimeisin tilannekuva (päivittyy automaattisesti)
└── .github/
    └── workflows/
        └── watch.yml         # GitHub Actions -ajastus
```

## Asennus

### 1. Telegram-botti

1. Avaa Telegram ja etsi **@BotFather**
2. Lähetä `/newbot` ja seuraa ohjeita
3. Kopioi saatu **bot token**
4. Lähetä botille viesti, sitten avaa selaimessa:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
5. Etsi `"chat":{"id":XXXXXXX}` — tämä numero on **Chat ID**

### 2. GitHub Secrets

Mene repositorion **Settings → Secrets and variables → Actions** ja lisää:

| Nimi | Arvo |
|------|------|
| `TELEGRAM_BOT_TOKEN` | Botin token BotFatherilta |
| `TELEGRAM_CHAT_ID` | Oma chat ID |

### 3. Actions-oikeudet

Mene **Settings → Actions → General → Workflow permissions** ja valitse **"Read and write permissions"**.

### 4. Ensimmäinen ajo

Mene **Actions → Pesis Transfer Watcher → Run workflow**. Ensimmäinen ajo tallentaa nykyiset siirrot pohjaksi — ilmoitusta ei lähetetä. Seuraavista ajoista lähtien kaikki muutokset ilmoitetaan.

## Ajastus

Skripti ajetaan kerran tunnissa tasatunnein klo 04–20 UTC (07–23 Suomen aikaa).
```yaml
cron: "0 4-20 * * *"
```
