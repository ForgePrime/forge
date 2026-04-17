# Glossary

- **Slot** — przedział czasowy w grafiku lekarza. Długość = czas trwania procedury. Może być wolny lub zarezerwowany.
- **Bufor** — 10 min po każdym slocie, niedostępne do rezerwacji. Automatyczne.
- **Appointment / Wizyta** — rezerwacja konkretnego slotu przez pacjenta na konkretną procedurę.
- **Procedura** — typ wizyty z definicją czasu trwania (kontrola 15min, pierwsza wizyta 30min, EKG 20min, USG 45min, zabieg 60-90min).
- **Grafik (schedule)** — godziny pracy lekarza per day-of-week (np. poniedziałek 9-17) + absencje (pojedyncze dni wolne).
- **Absencja** — pojedyncze dni gdy lekarz nie pracuje (urlop, choroba, zastępstwo). Override dla grafika.
- **No-show** — pacjent nie pojawił się, nie anulował.
- **Auto-flag** — automatyczne oznaczenie pacjenta po 2 no-show z rzędu. Blokuje online booking po 3 no-show.
- **Nadrezerwacja** — dwie wizyty w tym samym slocie, zatwierdzone przez recepcję (audit required).
- **Zastępstwo** — drugi lekarz przyjmuje pacjentów zamiast niedostępnego głównego.
- **Reminder** — powiadomienie SMS (24h przed) + email (1h przed, fallback 2h przed jeśli SMS undelivered).
- **Strefa czasowa** — UTC w bazie, Europe/Warsaw domyślnie w UI, user może zmienić.
- **Reguła anulacji** — 48h = darmowa, 24-48h = 50%, <24h = 100% (z wyjątkami admin).
