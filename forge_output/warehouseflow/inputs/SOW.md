# Statement of Work — WarehouseFlow MVP

**Klient:** MetalParts Sp. z o.o. — dystrybutor części stalowych, 3 magazyny regionalne (Warszawa, Poznań, Wrocław).

**Problem biznesowy:** Obecnie pracownicy magazynu używają Excela do śledzenia stanów. Raz w tygodniu ktoś ręcznie konsoliduje arkusze z 3 lokalizacji — zajmuje to 4-6h. Średnio raz na kwartał gubimy towar (niezgodność stanu magazynowego vs rzeczywistość) o wartości 20-40 tys. zł.

**Cel:** Aplikacja webowa która pozwoli operatorom wprowadzać przyjęcia/wydania w czasie rzeczywistym, kierownikowi — widzieć stany online, a zarządowi — generować raporty miesięczne.

## Zakres MVP

### Aktorzy

- **Operator magazynu** (10 osób) — skanuje/wprowadza przyjęcia i wydania towaru. Pracuje w jednym konkretnym magazynie.
- **Kierownik magazynu** (3 osoby) — widzi stany swojego magazynu, zatwierdza korekty inwentaryzacyjne.
- **Dyrektor operacyjny** (1 osoba) — widzi wszystkie magazyny, generuje raporty, ustawia stany alarmowe.

### Funkcje

1. **Katalog produktów** — lista ~2000 pozycji. Każdy produkt: SKU, nazwa, jednostka (szt/kg/m), cena jednostkowa, min. stan alarmowy.
2. **Przyjęcia towaru** — operator wybiera produkt, wprowadza ilość, dostawcę, numer faktury, datę. Stan magazynowy rośnie.
3. **Wydania towaru** — operator wybiera produkt, ilość, klienta/zlecenie. Stan spada. Nie może zejść poniżej zera.
4. **Inwentaryzacja** — okresowa, operator wprowadza stan rzeczywisty, system liczy różnicę. Kierownik zatwierdza korektę.
5. **Stany alarmowe** — jeśli stan < min, produkt pojawia się na liście alertów kierownika.
6. **Raporty miesięczne** — obroty per produkt, per magazyn, wartość stanów na koniec miesiąca.

### Wymagania niefunkcjonalne

- Web UI dostępne na tablecie (operatorzy używają Samsung Galaxy Tab 10")
- Responsywne dla desktop 1920×1080 (kierownicy, dyrektor)
- Max 3 sekundy na załadowanie widoku listy produktów
- Backup danych codziennie
- Logowanie użytkowników (email + hasło)
- Autoryzacja — operator widzi tylko swój magazyn, kierownik swój, dyrektor wszystkie

### Poza zakresem MVP

- Integracja z ERP (planowane w fazie 2)
- Kody kreskowe / skaner (fazy 2)
- Zamówienia do dostawców (fazy 2)
- Aplikacja mobilna natywna (fazy 2 — teraz tylko PWA jeśli łatwo)

## Harmonogram

- Start: ASAP
- Deadline MVP: 6 tygodni
- Pilot w Warszawie: tydzień 7-8
- Roll-out na 3 magazyny: tydzień 9-10

## Budżet

W gestii dostawcy, rozliczenie time & material. Szacunek max 240 mandays.
