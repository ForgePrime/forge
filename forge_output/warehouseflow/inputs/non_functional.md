# Non-Functional Requirements

## Wydajność
- Strona z listą produktów (2000 pozycji): < 3s załadowanie
- Wprowadzenie pojedynczego ruchu magazynowego: < 1s od kliknięcia "zapisz"
- Raport miesięczny dla jednego magazynu: < 10s

## Skalowalność
- 3 magazyny × 10 operatorów = 30 użytkowników równocześnie
- ~500 ruchów magazynowych dziennie (peak)
- Historia ruchów: 3 lata → ~550k rekordów

## Dostępność
- 8:00-18:00 pon-pt: 99.5% uptime (krytyczne)
- Poza godzinami: best effort
- Zaplanowane przerwy: niedziela wieczór

## Bezpieczeństwo
- Hasła: bcrypt, min 10 znaków
- Sesje: wygasają po 8h braku aktywności
- Audit log: każda zmiana stanu magazynowego z timestampem, userId, starym i nowym stanem — retencja 5 lat
- Brak danych osobowych poza email kierowników — RODO minimalne

## Zgodność
- Ustawa o rachunkowości: zapisy księgowe nie mogą być usuwane, tylko korygowane (nowy rekord anulujący)
- Korekty inwentaryzacyjne muszą mieć podpisaną ścieżkę akceptacji

## Infrastruktura
- Hosting: preferowane on-prem w serwerowni MetalParts (Warszawa). Chmura tylko jeśli jest tańsza.
- Backup: pełny daily, retention 30 dni
