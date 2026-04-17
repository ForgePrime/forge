# E-mail od dyrektora operacyjnego (po otrzymaniu SOW)

**Od:** marek.nowak@metalparts.pl
**Do:** dostawca
**Temat:** Re: WarehouseFlow — uzupełnienia

Dzień dobry,

Rzuciłem okiem na wasz SOW i widzę że pominęliśmy kilka ważnych rzeczy:

1. **Braki magazynowe vs rezerwacje** — u nas czasem klient zarezerwuje towar 2 tygodnie naprzód. Musi być możliwość rezerwowania stanu (blokada części zapasu) zanim jest fizyczne wydanie. Operator musi widzieć: stan fizyczny, stan zarezerwowany, stan dostępny.

2. **Zwroty od klienta** — to nie to samo co przyjęcie od dostawcy. Inna ścieżka księgowa. Potrzebujemy osobnej funkcji "zwrot od klienta" ze wskazaniem oryginalnego wydania.

3. **Przesunięcia międzymagazynowe** — zapomniałem o tym. Zdarza się że trzeba przenieść towar z Warszawy do Poznania. Wymaga dwóch kroków: operator W-wa robi "wydanie transferowe", operator Poznań "przyjęcie transferowe". Stan w tranzycie powinien być widoczny.

4. **Co do autoryzacji** — kierownik W-wy MUSI widzieć stany innych magazynów żeby wiedzieć gdzie jest towar gdy u niego brakuje. Czyli kierownicy widzą wszystkie stany (read-only dla cudzych), ale zatwierdzają tylko swój magazyn.

5. **Alerty** — chcielibyśmy mailowe powiadomienie o przekroczeniu stanu alarmowego, raz dziennie zbiorczo o 8:00 rano.

6. **Jeden log** — operator czasem się myli i wpisuje złą ilość. Musi być możliwość anulowania ostatniej operacji (do 1h wstecz) bez korekty inwentaryzacyjnej. Kierownik musi widzieć w audycie kto co anulował.

Jeszcze jedno — **NIE POTRZEBUJEMY raportów eksportowanych do PDF**, wystarczy widok web + eksport do CSV/Excel. PDF robimy ręcznie w innych narzędziach.

Pozdrawiam,
Marek Nowak
Dyrektor Operacyjny, MetalParts
