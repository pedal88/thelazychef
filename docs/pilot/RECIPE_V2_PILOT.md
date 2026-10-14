# Pilot: oppskriftsmodell v2, fase 0

Dato: 14.10.2026
Beslutning som testes: `docs/RECIPE_MODEL_V2.md`, avsnitt 7, fase 0.
Kode: `scripts/pilot_v2.py`, `schemas/recipe_v2.py`, `services/recipe_v2_validator.py`, `data/prompts/recipe_v2/`.
Resultater: `data/pilot_v2/results/` (én JSON per oppskrift, med kildetekst, alle forsøk og feil).

## Konklusjon

**Kravet er nådd med god margin.** 20 av 20 oppskrifter besto validatoren etter nye forsøk, og 19 av 20 besto i første forsøk. Kravet var 80 prosent etter maks to nye forsøk. Den eneste feilen var en metode utenfor katalogen («roux»), som ble rettet i andre forsøk.

**Visningene ser gode ut, med fire forbehold.** Alle 20 kan tegnes i de seks visningene uten feil, og planene gir fornuftige tider. Carbonara, tikka masala, lasagne og brøddelen av hamburgeren holder samme nivå som de håndlagde. Det som gikk galt, er ting validatoren ikke ser:

1. Klargjøring av utstyr uten ingredienser («kle formen») henger løst og havnet etter stekingen.
2. Når samme ovn varmes til to temperaturer, må ventetiden kobles til riktig oppvarming.
3. Maltekst med totale mengder gir feil når teksten sier «på hver» («8 skiver cheddar på hver burger»).
4. Feil i kildedataene blir mer synlige, ikke færre (navn med kuttbeskrivelse i, «chicken fat» der det skulle vært kraft).

Ingen av dem er grunn til å forenkle modellen. To krever en presisering av regelen for `setup`, én krever en promptregel, og den siste krever opprydding i pantryet før migreringen.

**Anbefaling:** gå videre til fase 1 og 2 som vedtatt, med endringene i avsnittet «Anbefalte endringer». Strukturering må gå som bakgrunnsjobb (median 86 sekunder).

## Oppsett

| | |
|---|---|
| Modell | `gemini-flash-latest`, som appen bruker. Svarte som `gemini-3.8-flash` |
| Nøkkel | Samme `GOOGLE_API_KEY` som Cloud Run-tjenesten i europe-west1 |
| Runde 1 | Fri tekst på norsk fra en kort beskrivelse (`recipe_v2/text.jinja2`). Bare for de fem rettene |
| Runde 2 | Strukturering med `RecipeV2Schema` som `response_schema` (`recipe_v2/structure.jinja2`). Ca. 6 500–7 500 tokens inn |
| Eksempler i promptet | Carbonara og lasagne fra prototypen. Når en av dem selv struktureres, byttes den ut med tikka masala eller brownies, så modellen ikke ser fasiten |
| Validering | Regel 1–8. Feilene sendes tilbake sammen med forrige svar, maks to nye forsøk |
| Katalogene | Ligger i promptet som tekst, ikke som `enum` i skjemaet. Det gjør regel 7 til en reell test |

Testsett:

- **Fasit (5):** de fem rettene fra `docs/prototypes/fem-retter.html`, generert fra én setning gjennom begge rundene. De håndlagde versjonene ligger som v2-JSON i `data/pilot_v2/fasit/` og består validatoren.
- **Database (15):** tilfeldig utvalg (frø 42) av 56 godkjente oppskrifter i produksjon, strukturert fra dagens ingredienslinjer og steg. Alle er på engelsk. Eksportert til `data/pilot_v2/inputs/db_recipes.json`.

## Resultater

| Sett | Bestått etter nye forsøk | Bestått i første forsøk | Snitt kostnad (USD) | Snitt tid (s) | Maks tid (s) |
|---|---|---|---|---|---|
| Fasit | 5/5 (100 %) | 4/5 (80 %) | 0,044 | 84 | 90 |
| Database | 15/15 (100 %) | 15/15 (100 %) | 0,044 | 83 | 138 |
| Alle | 20/20 (100 %) | 19/20 (95 %) | 0,044 | 83 | 138 |

| Regel | Forsøk som feilet | Oppskrifter berørt |
|---|---|---|
| 7 (katalogene) | 1 | 1 (lasagne, `method: roux`) |
| Øvrige regler | 0 | 0 |

Validatoren ga heller ingen advarsler (tidsord, steg uten tid). Per oppskrift:

| Sett | Oppskrift | Forsøk | Tokens inn/ut/tenk | USD | Tid (s) |
|---|---|---|---|---|---|
| fasit | Brownies | 1 | 7261/4049/7048 | 0,037 | 73 |
| fasit | Hamburger med hjemmelagde brød | 1 | 7773/4776/9240 | 0,046 | 89 |
| fasit | Spaghetti carbonara | 1 | 8597/3394/8765 | 0,041 | 82 |
| fasit | Lasagne med grønn salat | 2 | 17450/9147/4614 | 0,050 | 90 |
| fasit | Kylling tikka masala med ris | 1 | 7726/4398/9140 | 0,045 | 87 |
| db | Caramelized Onion Hummus | 1 | 6653/1119/2898 | 0,015 | 27 |
| db | Greek Chicken Gyros with Protein Tzatziki | 1 | 7243/3936/5452 | 0,032 | 57 |
| db | Lasagna alla Bolognese | 1 | 7453/4009/12280 | 0,053 | 103 |
| db | Tacos al Pastor | 1 | 7112/4117/11614 | 0,051 | 101 |
| db | Enchiladas Verdes | 1 | 7172/3989/7955 | 0,039 | 71 |
| db | Classic Cheeseburger on Brioche (177) | 1 | 6884/3225/5514 | 0,030 | 56 |
| db | Buffalo Wings | 1 | 6820/2962/10844 | 0,045 | 85 |
| db | Butter Chicken | 1 | 7222/2526/17133 | 0,063 | 132 |
| db | Rotisserie-Style Chicken Gyros (190) | 1 | 7208/4281/12411 | 0,054 | 94 |
| db | Spanish Seafood and Chicken Paella | 1 | 7187/4023/16406 | 0,065 | 127 |
| db | Loaded Baked Potato Soup | 1 | 6920/3570/11729 | 0,049 | 94 |
| db | Rotisserie-Style Chicken Gyros (209) | 1 | 7068/2451/7349 | 0,033 | 54 |
| db | Classic Cheeseburger on Brioche (212) | 1 | 6934/3060/5040 | 0,028 | 51 |
| db | Caramelized and Sticky Pork Neck | 1 | 6876/2907/5990 | 0,030 | 53 |
| db | Honey and Thyme Roasted Carrots | 1 | 6555/1088/21057 | 0,070 | 138 |

### Kostnad og tid

- **Kostnad:** 0,87 USD for alle 20, i snitt 0,044 USD per oppskrift. Runde 1 utgjør 0,008 USD og 23 sekunder av dette for de fem rettene. Prisen for `gemini-3.8-flash` er ukjent og er regnet som Gemini 3 Flash (0,50/3,00 USD per million tokens inn/ut). Tallet må sjekkes mot faktisk fakturering.
- **Tenketokens er 66 prosent av kostnaden.** Antallet varierer mye og henger ikke sammen med hvor vanskelig oppskriften er. Gulrøttene, den enkleste retten, brukte 21 000 tenketokens og 138 sekunder. Et lavere tenkenivå er det første som bør testes for å få ned tid og kostnad.
- **Tid:** median 86 sekunder, maks 138. Det er for lenge til å vente på i grensesnittet. Strukturering må kjøres som bakgrunnsjobb, slik bildegenerering gjøres i dag.
- **Migrering av 56 godkjente oppskrifter:** anslagsvis 2,50 USD og 15–20 minutter med fem parallelle kall.

### Trofasthet mot kilden (databasesettet)

Ingredienser og mengder ble sammenlignet automatisk med kilden for alle 15. Ingen ingredienser mangler, ingen er lagt til, og ingen mengder er endret. Der samme ingrediens brukes to ganger, er den delt i to linjer som summerer riktig.

Fire oppskrifter fikk færre steg enn kilden (lasagna 25 → 14, enchiladas 21 → 14, gyros 151 19 → 14, butter chicken 15 → 14). Ved gjennomlesing av lasagnaen er innholdet beholdt. Stegene er slått sammen etter regelen om én handling på ett sted.

## Visuell gjennomgang

Gått gjennom i `docs/prototypes/fem-retter-pilot.html` med planen «rolig»: alle fem rettene fra runde 1, og lasagna, gyros (190), paella, potetsuppe og honninggulrøtter fra databasen. Alle 20 tegnes uten feil i prototypens egen validator.

**Det som virker:**

- **Delte ingredienser er riktige** der det betyr noe. Pecorino er 80 g i eggeblandingen og 20 g til servering. Hvitløk, ingefær, garam masala og salt er delt mellom marinade og saus i tikka masala.
- **«Ferdig når» er konkret og sansebasert** i nesten alle steg. 209 av 263 steg har det, og bare to cook-steg mangler det.
- **Planen gir mening.** Eggeblandingen piskes mens guancialen steker. Salaten lages mens lasagnen hviler. Persille og sitron gjøres klar mens paellaen småkoker. Bechamel lages mens ragùen småkoker i 90 minutter.
- **Totaltidene ligger nær de håndlagde:** carbonara 25 mot 26 minutter, lasagne 97 mot 105, hamburger 2,5 mot 2,6 timer. Avvikene kommer av at runde 1 valgte andre tider (for eksempel 30 minutters marinering i stedet for 60).
- **`holds_minutes` er satt** på 136 av 263 steg, og marinering får fleksibel ventetid («minst 30 min, maks 24,5 t»).
- **Maltekst rendres riktig** og skaleres med porsjonene.

**Funn, etter alvor:**

1. **Klargjøring av utstyr henger løst (brownies).** «Smør og kle formen» har ingen ingredienser og ingen `after`. Siden `waits` ikke lagres, er det ingenting som sier at den må gjøres før røren helles i formen, og planen la den etter stekingen. Prototypen hadde dette som `waits` i den håndlagde versjonen.
2. **Samme ovn varmes til to temperaturer (hamburger).** Brødene stekes på 200 °C og pommes fritesen på 225 °C, med hvert sitt oppvarmingssteg. Regelen «vent på setup-steget for samme kokekar» valgte det første, så pommes fritesen gikk inn før ovnen var skrudd opp. I potetsuppen (db-203) mangler det oppvarming helt for begge ovnsstegene (200 og 250 °C), fordi kilden ikke har det.
3. **Maltekst og «per stykk» (hamburger).** «Legg umiddelbart 8 skiver cheddarost på hver burger»: `{i}` rendres som totalmengden, men teksten bruker den som mengde per burger. Samme risiko finnes for alle formuleringer med «hver», «each», «per».
4. **Kildedata blir mer synlige.** Pantrynavn som inneholder kutt og størrelse gir rare setninger når de settes inn i teksten: «Peel 1 red onion, medium, diced and slice it», «Wash 2 Roma tomatoes, chopped and chop them», «1 Beef Stock, Cube». Potetsuppen har «625 ml chicken fat (schmaltz)» der det åpenbart skulle vært kraft. Det er en feil i databasen som struktureringen trofast tok med.
5. **Ett sluttsteg tvinger frem koblinger når kilden mangler servering.** Gyros 190 har ikke noe «sett sammen»-steg. AI-en gjorde «hvil kjøttet» til sluttsteg og la tzatziki, pita og grønnsaker i `after` på det. Validatoren er fornøyd, men grafen sier at tzatzikien går inn i hvilingen.
6. **Komponentene varierer i oppdeling.** Lasagnen fra runde 1 har bare «Lasagne» og «Salat», mens den håndlagde har kjøttsaus, hvit saus, lasagne og salat. Databaseoppskriftene arver dagens komponenter, inkludert «Assembly and Garnish» og «Pasta Assembly», som ikke er noe man kan peke på på tallerkenen. Metrokartet og ingredienslisten per komponent blir dårligere av det.
7. **Passiv tid på komfyren er raus.** «Surr løken under omrøring i 8–10 minutter» får 3 minutter aktiv og 6 passiv tid. Planen tror da at kokken er ledig mens løken freses. Ingen planer ble urealistiske i utvalget, men det trekker i den retningen.
8. **Mindre ting:**
   - Brownies ble oppgitt som 16 porsjoner (biter), så prototypen viser «¾ egg» ved fire porsjoner. Modellen mangler et begrep for utbytte («én form, 16 biter»), som prototypen løser med `fixed`.
   - Steg slås sammen på tvers av faser («pensle brødene og stek»).
   - Databaseoppskriftene er på engelsk, mens grensesnittet er på norsk («mens simmer the ragù står»).
   - Melken varmes i «kjelen» som allerede brukes til smørbollen, fordi utstyret ikke skiller mellom to kjeler.

**Mise en place-brettet:** brettet tegnes for alle 20. Mise-elementene er utledet automatisk fra grafen, ikke laget av AI-en. Linjene følger prep-stegene til første steg som ikke er prep, og grupperes etter steg og vei inn. Grupperingen blir stort sett fornuftig. Navnene blir bare lister over ingredienser («Olivenolje til steking, gul løk, hvitløk …»). Siden brettet er en fast del av visningene, bør neste runde teste om AI-en skal navngi elementene, eller om utledningen holder med bedre navn.

### Endret i prototypen under gjennomgangen

Adapteren i `fem-retter-pilot.html` utleder nå ventetid slik som anbefalt under. Et steg venter på klargjøringen av samme kokekar, og når det finnes flere, på den med samme temperatur. Klargjøring er `setup`-steg og steg uten ingredienser og uten `after`. Med det kommer «kle formen» først i brownies, og ovnen skrus opp før pommes fritesen settes inn. De håndlagde rettene gir samme totaltid som før gjennom adapteren. Unntaket er brownies med «rolig», 114 mot 116 minutter.

## Anbefalte endringer

Til beslutningsnotatet og fase 1/2:

1. **`setup` betyr all klargjøring av utstyr**, ikke bare oppvarming: forvarm ovnen, kok opp vann, kle formen, smør formen. Ventetid utledes fra setup-steget for samme kokekar. Finnes det flere, velges det med samme `temp_c`. Dette erstatter forenkling 1 i notatet uten å gjeninnføre `waits`.
2. **Ny advarsel i validatoren:** et steg med `temp_c` på ovn eller airfryer uten et setup-steg med samme utstyr og temperatur.
3. **Promptregel for mengder:** `{iN}` er alltid totalmengden. Skriv «fordel {i4} på burgerne», ikke «{i4} på hver burger».
4. **Promptregel for sluttsteg:** mangler kilden et serveringssteg, legges det til et kort «Server»-steg som samler komponentene, i stedet for å bruke et annet steg som sluttsteg.
5. **Komponentdefinisjonen må skjerpes i promptet,** med eksempler: sauser og fyll som lages hver for seg, er egne komponenter selv om de havner inne i retten. «Assembly», «Garnish» og «Main Dish» er ikke komponenter. Ved migrering skal dagens komponentnavn ikke kopieres ukritisk.
6. **Rydd i pantryet før migreringen:** navn uten kutt og størrelse («red onion», med «diced» i `prep_style`), og en gjennomgang av åpenbare feil som schmaltz-linjen.
7. **Utbytte:** legg til `yield_text` eller tilsvarende for oppskrifter som ikke skaleres per porsjon (kaker, brød).
8. **Bakgrunnsjobb og tenkenivå:** strukturer asynkront, og test et lavere tenkenivå på de samme 20 oppskriftene før fase 2. Det er der tiden og to tredjedeler av kostnaden ligger.
9. **Mise-elementer:** test i neste runde om utledningen holder, eventuelt med navn fra AI-en, før det besluttes at AI-en skal lage dem (fase 3).

Det er ikke funnet noe som tilsier at modellen bør forenkles før fase 2. Regel 1–6 og 8 feilet aldri.

## Begrensninger

- **Lite utvalg** (20), og én kjøring per oppskrift. Variasjon mellom kjøringer er ikke målt.
- **Databaseoppskriftene var allerede ordnet** i steg og komponenter, så runde 2 hadde mye å støtte seg på. Nye oppskrifter fra fri tekst er bare testet med de fem rettene.
- **Ikke testet:** regel 9 (mise-elementer, fase 3) og advarselen om `holds_minutes` i «rolig»-planen. Den siste er ikke oversatt til Python. Prototypen viser den i tidslinjen.
- **Prisen er antatt**, se over.
- **Den visuelle gjennomgangen** er gjort av én leser, på ti oppskrifter.

## Hvordan kjøre på nytt

Kjør fra roten av repoet:

```
python scripts/pilot_v2.py --export-db      # krever databasetilgang og application default credentials
python scripts/pilot_v2.py --set all
python scripts/pilot_v2.py --summary
node scripts/pilot_v2_export_fasit.mjs       # eksporterer fasit fra prototypen på nytt
```

Med Python fra python.org trenger databasekoblingen `SSL_CERT_FILE="$(python -m certifi)"`.

Visningene vises ved å åpne `docs/prototypes/fem-retter-pilot.html` og bruke «Last inn oppskrift (JSON)» på filer i `data/pilot_v2/results/`. Alternativt startes en lokal server fra roten av repoet, og siden åpnes med `?src=../../data/pilot_v2/results/db/db-155.json`.
