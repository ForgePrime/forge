# HIDDEN EXPECTATIONS — AppointmentBooking

## Stack oczekiwany
- Backend: FastAPI + SQLAlchemy + Postgres + Alembic
- Frontend: React + TypeScript (odchylenia akceptowalne)
- Jobs (reminders): Celery lub APScheduler
- Testy: pytest

## Tabele minimum (12)
- users (base), patients, doctors, receptionists, admins (inheritance lub role field)
- specializations, procedures (z duration_min)
- schedules (per day-of-week), absences (overrides)
- appointments (slot_start_utc, duration_min, status enum)
- notifications (sms/email queue + delivery_status)
- audit_log
- consent_log (RODO)

## Endpointy minimum 22
- Auth: login, logout, me, refresh-token
- Doctors: list, by-specialization, schedule for doctor/date
- Availability: GET /slots?doctor=&procedure=&from=&to= (CRITICAL)
- Appointments: create, get, cancel, reschedule, by-patient, today (reception)
- Procedures: list
- Schedules (admin): set, override absence
- Notes (doctor): add, update (only own patient appointments)
- GDPR: data-export, delete-me
- Audit: search

## Edge cases wymagane
1. Concurrent booking same slot — race, tylko 1 wygrywa, druga dostaje 409
2. Reschedule own appointment < 24h → 100% fee (lub block if no payment module)
3. Book outside doctor schedule → 422
4. Book during doctor absence → 422 (empty availability)
5. Appointment cross midnight in user's timezone → zachowanie spójne (UTC in DB)
6. Daylight saving time boundary (kwiecień i październik) — slot 2:30 w nocy nie znika
7. Procedure longer than remaining work hours → 422 (nie może wystawać)
8. Bufor 10min kolizja — nie można zarezerwować slotu który wchodzi w bufor poprzedniego
9. Nadrezerwacja (override) — tylko receptionist+ może, audit log
10. Doctor absence w trakcie zarezerwowanej wizyty → auto-oferuj reschedule / substitute
11. Pacjent 3× no-show → online book DISABLED, manual tylko recepcja
12. Timezone change user mid-session — nie psuje UI

## Powinno być jasno zasygnalizowane
- Zawsze UTC w DB, konwersja w UI
- Bufor = automatyczna rezerwacja systemowa, nie dostępna dla pacjenta
- Anulacja ≠ usunięcie — appointment.status = CANCELLED, rekord zostaje
- Notatki medyczne: szyfrowane at-rest, widoczne tylko dla lekarza wizyty + pacjenta

## Red flags
- Appointments w local time bez UTC
- Brak bufora (pacjent rezerwuje minute-by-minute, lekarz nie ma czasu na notatki)
- Reguła anulacji nie zaimplementowana (kluczowe biznesowo)
- No-show auto-flag nie działa (email był wyraźny o 3× blokadzie)
- Dane medyczne w plaintext
- Brak audit log na nadrezerwacji
- DST boundary nie testowany
- Race condition przy concurrent booking (2 pacjentów, jeden slot)
- Brak retry queue dla undelivered SMS/email
