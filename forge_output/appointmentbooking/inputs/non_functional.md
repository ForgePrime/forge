# Non-Functional Requirements

## Wydajność
- Lista dostępnych terminów (search): < 2s dla zakresu 7 dni, 12 lekarzy
- Utworzenie rezerwacji: < 1s od submit
- Panel recepcji (dzisiejsze wizyty): < 500ms

## Skalowalność
- 500 concurrent users peak
- ~2000 appointments/tydzień
- Historia 10 lat = ~1M rekordów

## Dostępność
- 24/7 (pacjenci rezerwują wieczorami) — 99.5%
- Planowane przerwy: wtorek 2:00-4:00

## Bezpieczeństwo
- RODO compliant — consent log, prawo do zapomnienia, export JSON
- **Dane medyczne szyfrowane at-rest** (notatki lekarza)
- JWT access tokens, refresh tokens, short TTL (15 min access)
- Rate limiting: 10 rezerwacji/godzinę z jednego IP
- MFA dla admin i lekarzy
- Audit log: każda rezerwacja, anulacja, modyfikacja notatki — retencja 10 lat

## Zgodność
- Ustawa o prawach pacjenta: dokumentacja medyczna nie jest kasowana, tylko "zamknięta"
- GDPR: eksport i skasowanie konta pacjenta (pseudonimizacja historii medycznej)
- Planowana integracja HL7/FHIR w fazie 2 — schema powinna pozwalać mapowanie

## Powiadomienia (external)
- SMS: Twilio lub Infobip (provider TBD przez admin)
- Email: SendGrid lub AWS SES
- Fallback: jeśli provider down, retry queue, po 3 próbach email do adminów o incydencie
