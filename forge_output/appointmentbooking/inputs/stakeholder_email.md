# Email: zastrzeżenia kierownika recepcji

Od: anna.lewandowska@plantana.pl
Do: dostawca

Doszły mnie wasze pytania po call'u, więc uzupełniam:

1. **Długość wizyty zależy od TYPU**. Kontrola to 15 min. Pierwsza wizyta — 30 min. Zabieg zależy od procedury (nawet 90 min). System musi pozwalać definiować procedury z czasem ich trwania, a nie tylko "wolny slot 15 min".

2. **Bufor 10 min między wizytami** — lekarz musi mieć czas na notatki. System automatycznie dodaje 10 min po każdym slocie. To NIE jest slot dostępny dla pacjenta.

3. **Reguła anulacji** — pacjent anuluje bezpłatnie do **48h** przed. Między 24-48h — 50% opłaty. Poniżej 24h — 100% opłaty (chyba że siła wyższa i admin akceptuje). Recepcja może anulować zawsze bez opłat (awaria, choroba lekarza).

4. **Podwójna rezerwacja** — WYJĄTKI muszą być możliwe. Np. gdy lekarz przyjmuje pilny przypadek, drugi pacjent jest 2 min wizytą "recepta na kontynuację". Dla tego musi być funkcja "nadrezerwacja przez recepcję" — zostawia audit log.

5. **Strefy czasowe** — pacjenci z zagranicy rezerwują online. Zapisujemy ZAWSZE w UTC + wyświetlamy w Europe/Warsaw domyślnie. Pacjent może zmienić strefę w ustawieniach. Email potwierdzeniowy ma obie strefy.

6. **No-show** — jeśli pacjent nie pojawi się 2× z rzędu, system go AUTO-FLAGUJE. Przy 3 no-show przyszłe rezerwacje wymagają przedpłaty (funkcjonalność oznaczona ale płatności poza MVP — czyli po prostu BLOKADA rezerwacji online dopóki admin nie odblokuje).

7. **Grafiki** — lekarz może mieć inne godziny w różne dni (pon 9-13, wt 14-20, środa wolna, czw-pt 9-17). Musi być możliwość definiowania per day-of-week. Plus pojedyncze odstępstwa (np. 2026-05-10 nieobecny całą środę).

8. **Wizyta z zastępstwem** — gdy główny lekarz niedostępny, pacjent ma wybór: (a) przełożyć termin, (b) przyjść do zastępcy, (c) anulować. To widoczny proces.

9. **Reminders** — SMS nie zawsze dochodzi. Plan B: drugi email 2h przed wizytą jeśli SMS nie dostarczony (provider zwraca delivery status).

Pozdrawiam,
Anna Lewandowska
Kierownik recepcji, Centrum Plantana
