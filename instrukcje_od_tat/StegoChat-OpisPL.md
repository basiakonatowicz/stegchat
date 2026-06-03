# StegChat — przegląd dla studenta

Ten dokument tłumaczy **co będziesz budować** i **jak będzie wyglądać Twoja praca**, zanim zaczniesz pisać kod. Nie ma tu instrukcji krok-po-kroku — od tego jest `install.md`. To jest mapa, żebyś wiedział, czego się spodziewać.

---

## Co budujesz

Aplikację webową do czatu z ukrytymi wiadomościami w obrazkach (steganografia). Użytkownicy logują się hasłem, piszą wiadomości widziane przez wszystkich, wysyłają obrazki — a do obrazków mogą "wkleić" ukrytą wiadomość zaszyfrowaną hasłem. Cała kryptografia i steganografia dzieje się w przeglądarce; serwer tylko przechowuje dane.

Projekt jest dobrym wprowadzeniem do:

- **fullstack** — Python na serwerze + JavaScript w przeglądarce
- **chmury** — wdrożenie aplikacji na Google Cloud Run zamiast uruchamiania lokalnie
- **NoSQL** — Firestore zamiast klasycznego SQL
- **podstaw bezpieczeństwa** — hashowanie haseł, sesje w cookies, prosta kryptografia

---

## Jak to się ze sobą łączy

Trzy elementy, każdy ma swoją robotę:

**Twoja przeglądarka** to "klient". Wyświetla okno czatu, obsługuje wprowadzanie tekstu, robi całą pracę z obrazkami (zmniejszanie, szyfrowanie XOR-em, ukrywanie wiadomości w bitach pikseli). Pisana w HTML + Bootstrap + waniliowym JavaScript. Bez React, bez Vue, bez żadnych frameworków.

**Serwer FastAPI** działa albo lokalnie na Twoim laptopie podczas developmentu, albo w chmurze Google po wdrożeniu. Robi tylko cztery rzeczy:

1. Generuje strony HTML na podstawie szablonów (Jinja2)
2. Sprawdza loginy i hasła
3. Zapisuje i odczytuje wiadomości
4. Przekazuje obrazki do magazynu i z powrotem

**Chmura Google** to dwa miejsca, gdzie trzymane są dane:

- **Firestore** — baza danych dla użytkowników i metadanych wiadomości
- **Cloud Storage** — magazyn na pliki obrazków (PNG-i)

Schemat:

```
przeglądarka  ←→  FastAPI  ←→  Firestore (dane, tekst)
                       ←→  Cloud Storage (obrazki, PNG)
```

---

## Strony generowane po stronie serwera

To pojęcie warto zrozumieć od razu. Są dwa style budowania aplikacji webowych:

**Single-page app (SPA)** — np. aplikacje w React. Przeglądarka pobiera jeden duży plik JavaScript, który *sam* maluje całe UI i komunikuje się z serwerem przez API zwracające JSON.

**Server-rendered** (tak robimy my) — serwer generuje gotowy HTML na każde żądanie i wysyła go do przeglądarki. JavaScript jest minimalny i dodaje tylko interaktywności (wysyłanie wiadomości, obsługa obrazków). Strona "istnieje" jako gotowy HTML w momencie, gdy trafia do przeglądarki.

Jinja2 to system szablonów: piszesz HTML z dziurkami `{{ user.username }}` i `{% if user.is_admin %}...{% endif %}`, a Python wypełnia te dziurki danymi przed wysłaniem. Końcowy HTML trafia do przeglądarki w normalny sposób.

Dlaczego tak? Bo to jest prostsze. Nie piszesz dwóch aplikacji (frontu i backu), nie uczysz się React-a, mniej kodu — szybciej widać efekty, łatwiej debugować.

---

## Czym są te chmurowe nazwy

**Google Cloud Platform (GCP)** — chmura Google, konkurencja AWS i Azure. Hostuje wszystko, czego potrzebujesz, za darmo w ramach *free tier* (limity są bardzo spore jak na taki projekt).

**Firestore** — baza w stylu NoSQL. Zamiast tabel z wierszami masz "kolekcje" (np. `users`, `messages`), zawierające "dokumenty" (każdy dokument to jakby obiekt JSON). Nie piszesz SQL — używasz biblioteki Pythona, np. `db.collection("users").document("alice").get()`.

**Cloud Storage** — taki "dysk" w chmurze. Wrzucasz pliki, dostajesz adres, możesz później pobrać. My trzymamy tu wyłącznie obrazki PNG.

**Cloud Run** — usługa, która uruchamia Twoją aplikację w kontenerze (Docker). Wrzucasz kod, Google buduje kontener i uruchamia go za darmo. Kiedy nikt nie korzysta z aplikacji, kontener śpi i nic nie kosztuje. Gdy ktoś wejdzie na URL — Google budzi go w sekundę.

**Firebase** — to marka Google dla deweloperów; pod spodem korzysta z tych samych usług co GCP. W naszym projekcie *nie używamy* Firebase Auth ani Firebase JS SDK — Firestore i Storage używamy bezpośrednio z poziomu Pythona. Słowo "Firebase" pojawia się głównie w opcjonalnym kroku 13 (wysyłka e-maili przez Gmail).

---

## Twój dzień pracy

Większość czasu siedzisz przy laptopie, bez chmury, w trzech oknach naraz:

1. **VS Code w WSL** — edytujesz kod. Otwórz folder przez `code .` w terminalu WSL.
2. **Terminal WSL** — uruchomiony serwer komendą `uvicorn app.main:app --reload --port 8080`. Flaga `--reload` sprawia, że gdy zapiszesz plik Pythona, serwer sam się przeładowuje. Tu pojawiają się błędy serwera.
3. **Przeglądarka** — pod adresem `http://localhost:8080`. Najlepiej **dwa okna obok siebie** (zwykłe + tryb incognito) z dwoma różnymi użytkownikami — wtedy od razu widzisz, że wiadomości przechodzą między klientami.

Pętla pracy:

- piszesz kawałek kodu w VS Code
- zapisujesz (Ctrl+S)
- przeładowujesz kartę w przeglądarce (Ctrl+R)
- jeśli coś nie działa → patrzysz w terminal albo DevTools

I to wszystko. Żadnego osobnego "buildowania", żadnej kompilacji. Python interpretuje kod od razu, przeglądarka interpretuje HTML i JS od razu. To największa zaleta tego stosu technologicznego dla początkującego.

---

## Kiedy zakładać konta w chmurze

**Krok 1 z install.md (skeleton FastAPI)** — nie potrzebujesz GCP. Wszystko lokalnie, w pięć minut.

**Krok 2 (Firestore)** — tutaj po raz pierwszy potrzebujesz konta. Plan:

1. Załóż konto Google (jeśli nie masz)
2. Wejdź na `https://console.cloud.google.com` — to graficzny panel GCP w przeglądarce
3. Stwórz projekt (np. `stegchat-XXXX`)
4. Włącz billing. Paradoksalnie nawet dla *free tier* Google wymaga podania karty. **Nie zapłacisz nic**, jeśli nie przekroczysz limitów — a w tym projekcie ich nie przekroczysz. Możesz dodatkowo ustawić budżetowy alert "powiadom mnie, gdy wydatki przekroczą 1 zł".
5. Wykonaj komendy `gcloud` z sekcji Prerequisites w `install.md`

**Krok 12 (deploy)** — wtedy po raz pierwszy używasz Cloud Run i Twoja aplikacja staje się dostępna publicznie w internecie.

**Praktyczna rada:** założenie konta GCP, instalacja `gcloud`, logowanie, weryfikacja karty — to wszystko zajmuje około 30 minut. Zrób to **na spokojnie, najlepiej rano**, *zanim* zaczniesz Krok 2. Nie zostawiaj tego na ostatnią chwilę przed terminem oddania projektu.

---

## Jak debugować, gdy coś nie działa

Sprawdzaj w tej kolejności:

1. **Terminal z `uvicorn`** — jeśli serwer wywalił się z błędem, masz tu stack trace w Pythonie. Czerwone linie. Czytaj od dołu — ostatnia linijka mówi *jaki* błąd, a wyższe — *gdzie*.
2. **DevTools w przeglądarce (F12)**:
   - zakładka **Console** — błędy JavaScript
   - zakładka **Network** — zobacz, czy request poszedł, jaką odpowiedź dostał, jaki kod statusu (200 = OK, 401 = nie zalogowany, 403 = brak uprawnień, 500 = błąd serwera)
3. **Konsola GCP w przeglądarce** (`console.cloud.google.com`) — wejdź w Firestore i zobacz, czy dane się zapisały. Wejdź w Cloud Storage i zobacz, czy obrazek tam jest. To często rozstrzyga "czy serwer dostał dane, ale ich nie zapisał" vs. "w ogóle nie dotarły".
4. **Logi Cloud Run** (po wdrożeniu) — w konsoli GCP: Cloud Run → Twoja usługa → zakładka "LOGS". Tu lądują wszystkie `print()`-y i błędy z aplikacji działającej w chmurze.

Generalna zasada: **`print()` jest Twoim przyjacielem**. W Pythonie pisz `print("DEBUG sender:", sender)`, w JS `console.log("DEBUG", obiekt)`. Po znalezieniu błędu — usuń te linijki, żeby nie zaśmiecać kodu.

---

## Koszty

Jeśli zostaniesz w skali tego projektu, **zapłacisz 0 zł**. Limity *free tier* Google'a na używane usługi:

- Firestore: 50 000 odczytów / dzień
- Cloud Storage: 5 GB
- Cloud Run: 2 miliony zapytań / miesiąc

Aplikacja dla pięciu znajomych nigdy nie zbliży się do tych limitów. Po obronie projektu możesz zostawić aplikację w chmurze za darmo, dopóki nikt nie zacznie jej spamić.

Dla bezpieczeństwa: w panelu GCP → **Billing** → **Budgets and alerts** → ustaw budżet np. 5 zł z alertem przy 50% wykorzystaniu. Wtedy Google wyśle Ci e-mail, gdyby coś poszło nie tak.

---

## Korzystanie z AI do kodowania

Plik `install.md` ma w każdym kroku sekcję **"Prompt for coding agent"**. To są gotowe polecenia dla narzędzi typu Claude Code, Cursor czy GitHub Copilot Chat. Pomysł: zamiast pisać każdą linijkę od zera, prosisz AI o wygenerowanie kodu na podstawie tych promptów. Potem czytasz wygenerowany kod, sprawdzasz że rozumiesz, testujesz, poprawiasz drobiazgi.

**To nie jest oszukiwanie — to standardowa praktyka w 2026 roku.** Ale uwaga: jeśli wkleisz prompt i nie zrozumiesz wyniku, na obronie projektu nie odpowiesz na pytanie "co robi linijka X". Zawsze przejedź wygenerowany kod własnymi oczami; dopytaj AI co robi dany fragment, jeśli czegoś nie rozumiesz. Lepiej napisać mniej, ale ze zrozumieniem, niż dużo i nie wiedzieć co się dzieje.

Jeśli nie używasz AI — wszystko da się napisać ręcznie. Każdy krok rozkłada się na 20–50 linijek kodu, które są w zasięgu pierwszego roku.

---

## Sugerowana kolejność

1. **Najpierw** przeczytaj `install.md` w całości (15 minut). Zobacz jak rośnie aplikacja od kroku do kroku. *Jeszcze nie pisz kodu.*
2. **Wtedy** załóż konto GCP, zainstaluj `gcloud`, zaloguj się, włącz API (sekcja Prerequisites).
3. **Następnie** zacznij od Kroku 1 i idź po kolei. Każdy krok testuj zanim ruszysz dalej. Nie rób trzech kroków naraz — gdy coś się wywali, nie będziesz wiedział co.
4. **Krok 12 (deploy)** zrób dopiero wtedy, gdy lokalnie wszystko działa. Nie wcześniej.
5. **Krok 13 (e-maile)** spokojnie zignoruj — jest opcjonalny i niczego nie dodaje do oceny.

Cały projekt to **jeden weekend**, jeśli wszystko idzie gładko. Realnie, z napotkanymi problemami: dwa, trzy weekendy. To normalne. Każdy programista grzęźnie w głupich błędach (literówka w nazwie zmiennej, źle przekierowane porty, plik nie zapisany) — to nie znaczy, że jesteś słaby. Wytrwałość bije talent.

Powodzenia!
