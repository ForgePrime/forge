# Statement of Work — MediSlot Appointment System

**Klient:** Centrum Medyczne Plantana — prywatna klinika, 12 lekarzy różnych specjalizacji, 2 gabinety zabiegowe, rejestracja.

**Problem:** Rezerwacje telefoniczne + Google Calendar. Pacjenci dzwonią w godz. 8-20, recepcja nie nadąża. Podwójne rezerwacje przy ręcznym wpisywaniu (~3-5× w tygodniu). Brak przypomnień SMS = 15% no-show rate.

**Cel:** System rezerwacji online dla pacjentów + panel recepcji + automatyczne przypomnienia.

## Zakres MVP

### Aktorzy
- **Pacjent** — rezerwuje sam przez web/mobile, widzi swoje wizyty, może anulować.
- **Recepcja** — rezerwuje w imieniu pacjenta (gdy dzwoni), przekłada, anuluje, widzi wszystkie wizyty.
- **Lekarz** — widzi swój kalendarz na dziś/tydzień, ma możliwość dodania/edycji notatki po wizycie.
- **Admin** — ustawia grafiki lekarzy, ceny wizyt, specjalizacje.

### Funkcje
1. **Katalog lekarzy** — specjalizacja, zdjęcie, opis, ceny wizyt.
2. **Przeglądanie dostępnych terminów** — pacjent wybiera specjalizację, system pokazuje wolne sloty u wszystkich lekarzy tej specjalizacji na 7/14/30 dni.
3. **Rezerwacja** — wybór slotu → dane pacjenta → potwierdzenie → email confirmation.
4. **Panel recepcji** — lista dzisiejszych wizyt, wyszukiwanie pacjenta, szybka rezerwacja, anulacja.
5. **Przypomnienia** — SMS 24h przed wizytą, email godzinę przed.
6. **Historia pacjenta** — wizyty archiwalne, notatki lekarskie (widoczne tylko dla lekarza wizyty i samego pacjenta).
7. **Grafik lekarzy** — admin definiuje godziny pracy (np. pon-pt 9-17 z przerwą 13-14), absencje, zastępstwa.

### NFR
- Pacjent nie czeka > 2s na wyświetlenie wolnych terminów
- System obsługuje min. 500 jednoczesnych użytkowników (peak rejestracji po feriach)
- Backup codzienny, retencja 10 lat (medyczne)
- GDPR: pacjent może pobrać swoje dane i skasować konto
- HL7/FHIR: integracja z NFZ w fazie 2 (nie teraz)

### Poza MVP
- Płatności online (faza 2)
- Telewizyty (faza 2)
- Aplikacja mobilna natywna (teraz tylko PWA jeśli łatwo)

## Harmonogram
Pilot z lekarzami pilotażowymi: tydzień 6. Pełny roll-out: tydzień 10.
