# HIDDEN EXPECTATIONS — WarehouseFlow pilot

Te oczekiwania NIE są pokazywane agentowi. Służą do oceny wyniku po zakończeniu E2E.

## Oczekiwany stack
- Backend: FastAPI + SQLAlchemy + Postgres + Alembic (dopuszczalne odchylenie: Django + DRF)
- Frontend: React + TypeScript + Tailwind (dopuszczalne: Vue, Svelte)
- Auth: JWT lub session cookie, bcrypt dla haseł
- Testy: pytest dla backendu, minimum integration tests na endpointach

## Oczekiwana struktura modułów backendu
- `app/models/` — minimum 8 tabel: users, warehouses, products, batches, stock_movements, reservations, inventory_counts, audit_log
- `app/api/` — routery per domena (products, movements, reservations, inventory, reports, auth)
- `app/services/` — logika domenowa (stock_calculator, reservation_engine, report_generator)

## Oczekiwane endpointy API (minimum 18)
### Auth
- POST /auth/login
- POST /auth/logout
- GET /auth/me

### Products
- GET /products (filter: warehouse_id, low_stock=true)
- POST /products (admin)
- GET /products/{sku}
- PUT /products/{sku}/min-stock

### Movements
- POST /movements/incoming (przyjęcie)
- POST /movements/outgoing (wydanie)
- POST /movements/return (zwrot od klienta)
- POST /movements/transfer (transfer między magazynami)
- POST /movements/{id}/cancel (anulowanie do 1h)
- GET /movements (filter: warehouse, product, date range)

### Reservations
- POST /reservations
- DELETE /reservations/{id}
- GET /reservations (active)

### Inventory
- POST /inventory/counts (rozpoczęcie inwentaryzacji)
- POST /inventory/counts/{id}/approve (zatwierdzenie przez kierownika)
- GET /stock/alerts (lista przekroczeń min)

### Reports
- GET /reports/monthly?warehouse_id=&year=&month= (JSON + CSV)
- GET /reports/stock-value

### Audit
- GET /audit (filter: user, entity_type, date)

## Oczekiwane widoki UI (minimum 7)
1. **Login screen**
2. **Dashboard** — alerty, ostatnie ruchy, skrót do akcji
3. **Products list** — filtry: magazyn, low_stock, search po SKU/nazwie
4. **Product detail** — historia ruchów, stan fizyczny/zarezerwowany/dostępny per partia
5. **New movement form** — typ (in/out/return/transfer), produkt (autocomplete), ilość, meta
6. **Inventory count** — wprowadzanie stanu rzeczywistego, widok różnic, akceptacja
7. **Monthly report** — tabela z eksportem CSV

## Oczekiwane edge cases które muszą być pokryte
1. Wydanie większej ilości niż dostępne → REJECT 422
2. Wydanie gdy stan dostępny = rezerwacje → REJECT (nie można zjeść rezerwacji)
3. Anulowanie ruchu starszego niż 1h → REJECT
4. Anulowanie ruchu który był już częściowo konsumowany (np. transfer przyjęty) → REJECT
5. Transfer do tego samego magazynu → REJECT 422
6. Operator próbuje zmodyfikować ruch w innym magazynie niż swój → REJECT 403
7. Negative value w ilości → REJECT 422
8. Zero w ilości → REJECT 422
9. Równoczesne wydanie ostatniej sztuki przez 2 operatorów → race condition, jedna musi dostać REJECT (tylko jedna transakcja się powiedzie, druga dostaje 409/422)
10. Korekta inwentaryzacyjna > 10% wartości stanu → WARNING dla kierownika (ale nie blokuje)

## Oczekiwane role i uprawnienia
| Endpoint | operator | kierownik (own) | kierownik (other) | dyrektor |
|----------|----------|-----------------|-------------------|----------|
| GET products | ✓ own | ✓ | ✓ read | ✓ |
| POST movements | ✓ own | - | - | ✓ |
| POST cancel | ✓ own within 1h | ✓ own | - | ✓ |
| POST inventory approve | - | ✓ own | - | ✓ |
| GET reports | - | ✓ own | - | ✓ all |
| PUT min-stock | - | ✓ own | - | ✓ |

## Oczekiwane rzeczy które mogą być pominięte (akceptowalne)
- Email notifications (wymaga SMTP) — wystarczy że jest logika, bez faktycznego wysyłania
- PWA — opcjonalne
- Konkretne kolory/design systemu — oceniam po funkcjonalności, nie estetyce

## Red flags — rzeczy które byłyby błędem
- Przechowywanie haseł plaintext
- Brak transakcji DB przy ruchach magazynowych (race condition)
- Brak walidacji że stan nie zejdzie poniżej zera (SOW explicit)
- Brak wyróżnienia "stan fizyczny" vs "zarezerwowany" vs "dostępny" (email wymaga)
- Brak zwrotów od klienta jako osobnej ścieżki (email wymaga)
- Brak transferów międzymagazynowych (email wymaga)
- Dyrektor nie widzi wszystkich magazynów (SOW wymaga)
- Kierownicy nie widzą cudzych stanów read-only (email wymaga)
- Brak audit loga na ruchach (NFR wymaga 5 lat retencji)
- Brak testów — nawet jeden integration test per endpoint jest minimum
