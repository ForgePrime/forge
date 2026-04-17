# Glossary — MetalParts domain

- **SKU** (Stock Keeping Unit) — unikalny kod produktu, np. `MP-STL-05-100` = stal MetalParts, arkusze 0.5mm, 100×200.
- **Partia** — towar przyjęty jedną dostawą, ma wspólną cenę zakupu i datę. Stan magazynowy = suma partii minus wydania.
- **Stan fizyczny** — ile towaru jest w magazynie (wszystkie partie razem).
- **Stan zarezerwowany** — ile towaru ma przypisanych rezerwacji (jeszcze nie wydane, ale obiecane).
- **Stan dostępny** = fizyczny − zarezerwowany.
- **Min stan alarmowy** — ustawiany per produkt per magazyn. Poniżej tej wartości trafia na listę alertów.
- **Inwentaryzacja** — okresowe porównanie stanu systemowego ze stanem rzeczywistym. Różnica = manko (brak) lub nadwyżka.
- **Korekta inwentaryzacyjna** — księgowa zmiana stanu na podstawie inwentaryzacji. Wymaga akceptacji kierownika.
- **Transfer międzymagazynowy** — dwa ruchy magazynowe: wydanie transferowe (źródło) + przyjęcie transferowe (cel). Między nimi towar jest "w tranzycie".
- **Operator** — pracownik magazynu, wprowadza ruchy.
- **Kierownik** — osoba odpowiedzialna za jeden magazyn, zatwierdza korekty.
- **Jednostka miary** — szt (sztuki), kg (kilogramy), m (metry bieżące).
