# Oppskriftsvisninger: konsepter, status og datamodell

> **Beslutning om datamodell:** se `docs/RECIPE_MODEL_V2.md` (vedtatt 14.10.2026). Der notatet avviker fra dette dokumentet, gjelder notatet.

Dette dokumentet er kontekst for videre arbeid i oppskrift-appen. Det beskriver sju måter å vise en oppskrift på, hva dagens datamodell støtter, og hvilke tre endringer i oppskriftstrukturen som skal til for å lage dem ordentlig.

Visningene er valgt ut fra en idémyldring med 15 konsepter. Numrene (1, 2, 3, 4, 6, 7, 11) er beholdt fra den lista, så det er enkelt å referere til dem. De åtte som ble parkert, står kort beskrevet i vedlegget nederst.

Et gjennomgående mål er å skille tydelig mellom **prep** (forberedelse: kutte, måle, blande tørt) og **cook** (alt som skjer med varme, tid og timing). Datamodellen har allerede `phase` på hvert steg, så dette skillet finnes i dataene i dag.

---

## 1. Sammendrag

- Fire av de sju visningene kan lages i en enkel versjon på dagens data: kortmodus (4), baklengs fra servering (3, sekvensielt), mise en place (1, uten bollegruppering) og en enkel tidslinje (2, uten parallellitet).
- Tre visninger krever at stegene kobles til ingrediensene og til hverandre: ingredienser i steget (7), metrokartet (6) og tabellmetoden (11).
- Tre endringer i strukturen åpner for nesten alt:
  1. Lokale ID-er på ingredienser og steg, og at stegene peker på dem (`uses`, `after`). Da blir oppskriften en graf.
  2. Mal i stegteksten (`"Whisk {i3} until smooth"`) i stedet for mengder i fritekst.
  3. Strukturerte stegattributter: `action`, aktiv/passiv tid, utstyr, varme, temperatur, `done_when`, `text_short`.
- Grafen må valideres deterministisk før lagring. Gemini kommer til å lage brutte referanser.
- Eksisterende oppskrifter kan migreres med én LLM-kjøring per oppskrift, siden informasjonen allerede står i teksten.

---

## 2. Dagens datamodell (kort)

Se `ai_engine.py` (`Ingredient`, `IngredientGroup`, `Instruction`, `ComponentSchema`, `RecipeSchema`) og `process_recipe_workflow`.

- `recipe`: én rad per oppskrift. `prep_time_mins` gjelder hele oppskriften. `base_servings` er standard 4.
- `recipe_ingredient`: `ingredient_id`, `amount`, `unit`, `gram_weight`, `component` (fritekst, standard `"Main"`), `prep_style` (finnes i tabellen og vises i malene, men mangler i AI-skjemaet og er derfor trolig tomt).
- `instruction`: `phase` (`Prep`/`Cook`/`Serve`), `component` (fritekst, standard `"Main Dish"`), `step_number` (starter på 1 per komponent), `global_order_index` (rekkefølge på tvers, satt av AI), `text` (fritekst), `estimated_minutes` (valgfri, AI-anslag).
- `ingredient` (pantry): `default_unit`, `average_g_per_unit`, næring per 100 g, `sub_recipe_id`.

Kjente begrensninger som påvirker visningene:

1. **Steg og ingredienser er ikke koblet.** At «whisk the eggs» bruker de 3 eggene står bare i teksten.
2. **Komponenter er strenger.** `"Egg Custard"` i ingredienslista og `"Custard"` i steglista faller fra hverandre uten feilmelding.
3. **Ingen sammenslåing mellom komponenter.** At bunn, fyll og eggestand møtes i ett steg står bare i teksten.
4. **Tid og temperatur er fritekst.** Bare `estimated_minutes` er strukturert, og den skiller ikke mellom aktiv tid (du står og rører) og passiv tid (det står i ovnen).
5. **Mengder står i stegteksten.** Når brukeren skalerer fra 4 til 6 porsjoner, blir ingredienslista riktig, men teksten sier fortsatt «3 eggs». Dette er en bug uavhengig av visningene.
6. **`chef_note` og `hero_image_prompt` genereres, men forkastes** fordi det ikke finnes kolonner for dem.

---

## 3. De sju visningene

Hver visning er beskrevet med samme oppsett: hva den er, hvordan prep og cook vises, interaksjon, datakrav, hva som er mulig i dag og hva den fulle versjonen krever.

### 3.1 Visning 1: Mise en place-brettet

**Hva det er.** Prep-fasen vises som et brett med «skåler» brukeren fyller og huker av, ikke som en ingrediensliste. Hver skål er én ingrediens eller en gruppe ingredienser som skal samme vei. Brukeren kommer ikke videre til koking før brettet er klart (eller velger aktivt å hoppe over).

```
  ( Løk     )  ( Hvitløk )  ( Parmesan )  ( Persille )
  ( hakket  )  ( 3 fedd  )  ( revet    )  ( ✓ klar   )

  ┌──────────────── Tørt: mel, kakao, natron, salt ─────┐
  │ én bolle, siktes sammen                             │
  └─────────────────────────────────────────────────────┘

  [ 3 av 5 klare · Start koking → ]
```

**Hvorfor.** Profesjonelle kjøkken jobber slik, og det er den tydeligste måten å skille prep fra cook på. Koking blir roligere når alt er klart, fordi brukeren slipper å hakke løk mens smøret brenner.

**Prep og cook.** Hele visningen er prep. Overgangen til cook er en eksplisitt knapp som åpner kortmodus (4) eller tidslinjen (2).

**Interaksjon.**
- Trykk på en skål for å huke av. Avhukede skåler tones ned.
- Skåler grupperes i to nivåer: først etter komponent (bunn, fyll), deretter etter type arbeid (alt som skal hakkes, alt som skal rives, alt som bare måles).
- Ingredienser som går i samme bolle (for eksempel alt det tørre i en kake), vises som én stor skål med flere ingredienser.
- Prep-steg som ikke handler om en ingrediens («smør en form», «forvarm ovnen»), vises som egne oppgavekort på brettet.

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Ingrediensliste med mengder | `recipe_ingredient` | Ja |
| Hvordan ingrediensen skal klargjøres | `prep_style` | Kolonnen finnes, men er tom fordi AI-skjemaet mangler feltet |
| Gruppering etter type arbeid | `prep_style` fra fast liste | Nei |
| Hvilke ingredienser som går i samme bolle | `uses` på steget som først bruker dem | Nei (endring 1) |
| Prep-oppgaver uten ingrediens | steg med `phase = Prep` | Ja |

**Mulig i dag.** En enkel versjon: én skål per ingrediens, gruppert etter komponent, med `prep_style` når det finnes. Prep-steg vises som oppgavekort.

**Full versjon krever.**
- `prep_style` i `Ingredient`-skjemaet i `ai_engine.py`, helst fra en fast liste i `data/constraints/` (for eksempel `whole`, `chopped`, `finely_chopped`, `diced`, `sliced`, `grated`, `minced`, `zested`, `juiced`, `measured`). Fritekst kan ligge ved siden av for nyanser.
- Endring 1 (`uses`) for bollegruppering. Regel: en bolle er mengden ingredienser som brukes samlet av samme steg og ikke allerede er klargjort i et tidligere steg.

**Kanttilfeller.**
- Ingredienser som brukes i flere omganger (halve smøret i bunnen, resten i sausen). Krever `portion` på koblingen (se endring 1), ellers vises de som én skål.
- «Salt og pepper etter smak» skal ikke ha en skål. Bruk `unit = "to_taste"` eller tilsvarende og hopp over dem på brettet.
- Underoppskrifter (`sub_recipe_id`, for eksempel «Chilli Mayo») vises som én skål med lenke til egen mise en place.

---

### 3.2 Visning 2: Tidslinjen

**Hva det er.** En Gantt-visning av hele matlagingen. Hver oppgave er en stolpe langs en tidsakse, og en rød «nå»-strek beveger seg mens brukeren lager mat. Det viktigste visningen gjør er å vise parallellitet: vannet koker mens løken freser.

```
  Hakk løk      ████
  Kok vann         ░░░░░░░░░░            (passiv)
  Stek kylling        ██████
  Pasta                   ░░░░░░░░       (passiv)
  Saus                         █████
                     │ nå
  0 ──────── 10 ──────── 20 ──────── 30 min
```

**Hvorfor.** En vanlig oppskrift er skrevet som en fortelling, men matlaging er et parallelt løp. Det er her folk bommer: pastaen er ferdig fem minutter før sausen.

**Prep og cook.** Prep-stolper og cook-stolper har hver sin farge. Aktiv tid er heltrukket, passiv tid er skravert. Prep-stolpene havner naturlig til venstre, men kan overlappe cook når noe kan klargjøres mens noe annet står.

**Interaksjon.**
- Nå-streken følger klokka når brukeren har trykket start.
- Trykk på en stolpe for å se stegteksten.
- Neste aktive oppgave fremheves («Om 2 min: sett på pastaen»).
- På mobil: horisontal scroll med fast venstrekolonne, eller vertikal tidsakse.

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Rekkefølge | `global_order_index` | Ja |
| Varighet | `estimated_minutes` | Ja, men som ett tall |
| Aktiv vs. passiv tid | `active_minutes`, `passive_minutes` | Nei (endring 3) |
| Hva som må være ferdig før et steg kan starte | `after` | Nei (endring 1) |
| Fase | `phase` | Ja |

**Mulig i dag.** En trapp: stegene etter hverandre i `global_order_index`-rekkefølge med `estimated_minutes` som lengde. Den ser ut som en tidslinje, men er egentlig en liste, og totaltiden blir for lang fordi alt antas å skje sekvensielt.

**Full versjon krever.** Endring 1 (`after`) og endring 3 (aktiv/passiv tid), og en planleggingsalgoritme.

**Algoritme (enkel listeplanlegging med én kokk).**

```
input: steg med active_minutes, passive_minutes, after[]
regel: kokken kan bare gjøre ett aktivt steg om gangen.
       passiv tid (ovn, koking, hvile) kan overlappe alt annet.

ready = steg uten after
cook_free_at = 0
while det finnes uplanlagte steg:
    kandidater = ready-steg der alle after er planlagt
    velg kandidaten med lengst gjenværende kritisk sti
    start = max(cook_free_at, max(slutt for hvert steg i after))
    steg.start = start
    steg.active_end = start + active_minutes
    steg.end = steg.active_end + passive_minutes
    cook_free_at = steg.active_end
```

Prioriteringen etter lengst kritisk sti gjør at «forvarm ovnen» og «sett på vann» havner tidlig. Med to kokker (parkert visning 10) blir `cook_free_at` en liste med én verdi per kokk.

**Kanttilfeller.**
- Steg som krever oppmerksomhet midt i passiv tid («rør av og til»). Behandle som passiv tid i første versjon.
- Forvarming av ovn bør være et eget steg med `passive_minutes` og ingen `after`, slik at algoritmen legger det først.

---

### 3.3 Visning 3: Baklengs fra servering

**Hva det er.** Brukeren skriver når maten skal stå på bordet («18:30»), og appen regner ut klokkeslett for hvert steg.

```
  Middag klar kl. [ 18:30 ]

  17:45  Start prep
  18:05  Vann på
  18:12  Pasta i
  18:20  Saus
  18:30  Servér
```

**Hvorfor.** Folk tenker i klokkeslett, ikke i «etter 12 minutter». Spørsmålet de faktisk har er «når må jeg begynne?», og det svarer ingen oppskrift på i dag. Lite å bygge, stor effekt.

**Prep og cook.** Prep-blokken får sitt eget starttidspunkt øverst («Start prep 17:45»). Hvis brukeren har gjort mise en place (1) på forhånd, flyttes starttidspunktet for cook frem.

**Interaksjon.**
- Velg serveringstid. Standard er neste hele halvtime minst totaltid frem i tid.
- Valgfritt: varsel når neste steg skal starte.
- Hvis serveringstiden er umulig («du skulle startet for 10 minutter siden»), si det rett ut og foreslå tidligste mulige tid.

**Datakrav.** Samme som tidslinjen (2). Visningen er tidslinjen skrevet som klokkeslett.

**Mulig i dag.** Summer `estimated_minutes` bakover fra serveringstiden. Fungerer, men er pessimistisk fordi alt antas sekvensielt. Bruk summen av stegene, ikke `prep_time_mins`, så tallene henger sammen med stegene.

**Full versjon krever.** Endring 1 og 3. Kjør planleggingsalgoritmen fra 3.2 forover, og forskyv hele planen slik at siste steg slutter på serveringstiden.

**Kanttilfeller.**
- `prep_time_mins` og summen av stegene kan være uenige. Velg én kilde (summen av stegene, eller sluttiden fra planleggingsalgoritmen) og vurder å regne ut `prep_time_mins` i stedet for å la AI-en sette den.
- Oppskrifter med lang passiv tid (marinering over natt, heving) må vise dato, ikke bare klokkeslett.

---

### 3.4 Visning 4: Kortmodus

**Hva det er.** Ett steg per skjerm, stor tekst, timer på kortet og håndfri navigasjon. Dette er standardvisningen mens brukeren lager mat.

```
  ┌─────────────────────────────────┐
  │ Steg 6 av 9 · Cook              │
  │                                 │
  │ Vend pastaen inn i sausen       │
  │                                 │
  │ 200 g pasta · 3 dl saus         │
  │                                 │
  │ ⏱ 2:00          🎙 «neste»      │
  └─────────────────────────────────┘
```

**Hvorfor.** Under koking har brukeren melete hender og ser på skjermen fra en meter unna. En lang side med små bokstaver fungerer ikke da.

**Prep og cook.** Kortene får fargekode etter `phase`. Ved overgangen fra siste prep-kort til første cook-kort vises et skille («Prep ferdig. Nå starter kokingen»). Hvis brukeren har brukt mise en place-brettet (1), hoppes prep-kortene over.

**Interaksjon.**
- Sveip eller trykk for neste/forrige.
- Timer starter med ett trykk og fortsetter i bakgrunnen når brukeren går videre. Flere timere kan gå samtidig.
- Stemmestyring: «neste», «tilbake», «start timer», «gjenta».
- Skjermen skal ikke låse seg (Wake Lock API).

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Stegtekst i rekkefølge | `text`, `global_order_index` | Ja |
| Timer | `estimated_minutes` | Ja (anslag) |
| Fase | `phase` | Ja |
| Ingrediensene steget bruker | `uses` | Nei (endring 1) |
| Riktig mengde ved skalering | maltekst | Nei (endring 2) |
| Kort tekst for overskrift | `text_short` | Nei (endring 3) |
| Når steget er ferdig | `done_when` | Nei (endring 3) |

**Mulig i dag.** Ja, i en god versjon. Stegtekst, rekkefølge, fase og timer finnes. Dette bør bygges først.

**Full versjon krever.**
- Endring 1: ingrediensene vises nederst på kortet.
- Endring 2: mengdene i teksten skaleres med porsjonene.
- Endring 3: `done_when` vises under teksten («Ferdig når: gyllen kant»), og timeren bruker `active_minutes + passive_minutes` i stedet for et samlet anslag.

**Kanttilfeller.**
- Timer på steg der tiden er et intervall («30–40 min»). Lagre `minutes_min`/`minutes_max` eller bruk øvre verdi med varsel ved nedre.
- Parallelle steg: kortmodus er lineær. Når grafen finnes, kan kortet vise «Mens dette står: …» med neste aktive steg.

---

### 3.5 Visning 6: Metrokartet

**Hva det er.** Oppskriften tegnet som et T-banekart. Hver komponent (eller hver ingrediens) er en linje. Stegene er stasjoner. Linjer møtes der komponenter slås sammen, og alle ender i én endestasjon: retten.

```
  løk     ━━━━━━━┓
                 ●━━ fres ━━┓
  hvitløk ━━━━━━━┛          ┃
                            ●━━ saus ━━━━━━┓
  fløte   ━━━━━━━━━━━━━━━━━━┛              ┃
                                           ◉ servér
  pasta   ━━━━━ kok ━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Hvorfor.** Det gir oversikt før brukeren starter. Med ett blikk ser man at retten har tre deler som møtes til slutt, og hvilke ingredienser som hører til hvilken del. Visningen er pen og egner seg til deling, men den egner seg dårlig mens man lager mat. Bruk den som forhåndsvisning på oppskriftssiden.

**Prep og cook.** Linjene får prep-farge frem til første cook-stasjon og cook-farge etterpå. Da ser man hvor varmen kommer inn i hver gren.

**Interaksjon.**
- Trykk på en stasjon for å se steget.
- Trykk på en linje for å fremheve én komponent.
- Animasjon som tegner linjene fra venstre mot høyre er en fin detalj, men ikke nødvendig.

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Linjer (komponenter) | `component` | Ja, men som streng |
| Stasjoner (steg) | `instruction` | Ja |
| Hvilke ingredienser som går inn hvor | `uses` | Nei (endring 1) |
| Hvor komponenter møtes | `after` på tvers av komponenter | Nei (endring 1) |
| Kort navn på stasjonen | `action` eller `text_short` | Nei (endring 3) |
| Navn på mellomprodukt («the custard») | `output_label` | Nei (endring 1) |

**Mulig i dag.** Bare en svak versjon: én parallell linje per komponent som alle ender i samme punkt. Den viser ikke hvor komponentene faktisk møtes.

**Full versjon krever.** Endring 1 med `uses`, `after` og `output_label`, pluss en `component`-tabell så linjene får stabile ID-er. Endring 3 gir korte stasjonsnavn.

**Layout.** x-posisjon = rekkefølgen stegene starter i, hentet fra planleggeren (3.2), med én kolonne per steg. Da står et steg som «varm pitaene» til høyre for alt som skjer før det, selv om det er første steg i sin egen komponent. Topologisk nivå fungerer ikke som x-akse, fordi første steg i hver komponent da havner i samme kolonne uansett når det faktisk skjer. Skriv startminuttet under hver kolonne. y-posisjon = én bane per komponent. Linjen for en komponent begynner rett før komponentens første stasjon, ikke helt til venstre. Etiketter legges vekselvis over og under linjen, og under når linjen går oppover fra stasjonen. For mer enn tre-fire komponenter: bruk et layoutbibliotek for rettede grafer (for eksempel dagre eller elkjs) til banefordelingen.

**Kanttilfeller.**
- Én komponent som deles i to (halve sausen til servering, halve i gryta). Sjelden, men grafen blir da ikke et tre. Tegn som en forgrening.
- Oppskrifter med bare én komponent gir én rett linje. Skjul visningen eller vis ingredienser som linjer i stedet for komponenter.

---

### 3.6 Visning 7: Ingredienser i steget

**Hva det er.** Mengdene står inne i stegteksten, uthevet som små merkelapper. Brukeren slipper å scrolle mellom ingredienslista og fremgangsmåten.

```
  Steg 3
  Fres [løk · 1 stk] og [hvitløk · 2 fedd] i [smør · 2 ss]
  til det er blankt. Tilsett [fløte · 3 dl].
```

**Hvorfor.** Hoppingen mellom ingredienslista og stegene er den mest irriterende delen av en vanlig oppskrift. Hvis appen bare får én av disse visningene, bør det være denne. Den er også grunnlaget for at kortmodus (4) kan vise mengder på kortet.

**Prep og cook.** Merkelappen kan vise klargjøringen fra prep-fasen («løk · hakket») i cook-steg, så brukeren ser at løken skal være klar fra før.

**Interaksjon.**
- Trykk på en merkelapp for å se ingrediensen i pantry (bilde, næring, erstatninger).
- Merkelappen skaleres når brukeren endrer porsjoner.
- Valgfritt: veksle mellom volum og gram på merkelappen (`gram_weight` finnes allerede).

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Hvilke ingredienser steget bruker | `uses` | Nei (endring 1) |
| Hvor i teksten ingrediensen står | maltekst `{i3}` | Nei (endring 2) |
| Hvor mye av ingrediensen steget bruker | `portion` på koblingen | Nei (endring 1) |
| Mengde, enhet, gram | `recipe_ingredient` | Ja |

**Mulig i dag.** Bare med fuzzy matching av ingrediensnavn mot stegteksten. Det går an som nødløsning, men det bryter på bøyningsformer, synonymer og «the eggs» vs «whole eggs», og det løser ikke skalering. Ikke bygg på det.

**Full versjon krever.** Endring 1 og 2. Når de er på plass, er visningen ren rendering.

**Kanttilfeller.**
- Samme ingrediens i flere steg med ulik mengde («halve smøret»). Krever `portion`.
- Teksten refererer til et mellomprodukt («hell custarden over bunnen»). Det er ikke en ingrediens. Bruk `{s5}` som peker på et steg og rendres med stegets `output_label`.

---

### 3.7 Visning 11: Tabellmetoden

**Hva det er.** Metoden er kjent fra Cooking for Engineers (Michael Chu). Ingrediensene står i venstre kolonne i den rekkefølgen de brukes. Hver kolonne til høyre er en operasjon, og cellen dekker (med `rowspan`) nøyaktig de ingrediensene som går inn i operasjonen. Lest fra venstre mot høyre er det tid. Lest ovenfra og ned er det hva som går sammen med hva. Steg uten ingredienser («smør en form», «forvarm ovnen») står som rader øverst.

```
  ┌───────────────────────────────────────────────────────────────┐
  │ Smør og mel en 20×20-form                                     │
  │ Forvarm ovnen til 175 °C                                      │
  ├──────────────────────┬───────┬─────┬─────┬────────┬──────────┤
  │ Smør 115 g           │ smelt │     │     │        │          │
  ├──────────────────────┼───────┤ mix │     │        │          │
  │ Sukker 200 g, vanilje│       │     │ mix │        │  stek    │
  ├──────────────────────┤       │     │     │  vend  │  175 °C  │
  │ Espresso 60 ml       │       │     │     │   inn  │ 30–40 min│
  ├──────────────────────┼───────┴─────┤     │        │          │
  │ Egg 2 stk            │             │     │        │          │
  ├──────────────────────┼─────────────┴─────┤        │          │
  │ Mel 80 g, kakao 80 g │                   │        │          │
  ├──────────────────────┤       sikt        │        │          │
  │ Natron, salt         │                   │        │          │
  └──────────────────────┴───────────────────┴────────┴──────────┘
```

**Hvorfor.** Den viser at en oppskrift er et tre, og den gjør det kompakt. En hel brownie-oppskrift får plass på én skjerm. Det er en visning nesten ingen oppskriftsapper har, og den er rask å lese for den som har lært formatet.

**Svakheter.**
- Den viser rekkefølge, ikke minutter, og den viser ikke parallellitet.
- Den skalerer dårlig med mange grener. Tre komponenter som møtes sent gir en bred og vanskelig tabell.
- «Mix» skjuler teknikken. Brukeren må trykke for å få hele stegteksten.
- Den passer derfor best som oversikt før man starter, sammen med metrokartet. Visningene 6 og 11 er samme graf tegnet på to måter.

**Prep og cook.** Ingredienskolonnen og prep-operasjoner (sikt, hakk) får prep-farge. Operasjoner med `phase = Cook` får cook-farge. Skillet blir en tydelig vertikal grense i tabellen.

**Interaksjon.**
- Trykk på en operasjonscelle for full stegtekst og `done_when`.
- Porsjonsskalering endrer mengdene i venstre kolonne.
- På mobil: tabellen blir for bred. Vis den liggende, eller fall tilbake til en sammenleggbar trevisning.

**Datakrav.**
| Behov | Felt | Finnes i dag? |
|---|---|---|
| Ingredienser med mengde | `recipe_ingredient` | Ja |
| Hvilke ingredienser hvert steg bruker | `uses` | Nei (endring 1) |
| Hvilke steg som mater inn i neste | `after` | Nei (endring 1) |
| Kort verb per operasjon | `action` / `text_short` | Nei (endring 3) |
| Temperatur og tid i sluttcellen | `temp_c`, `active_minutes`, `passive_minutes` | Nei (endring 3) |

**Mulig i dag.** Nei. Hele visningen er grafen.

**Layout-algoritme.**

```
1. Finn sluttsteget (steget ingen andre har i after).
2. Bygg treet bakover: barna til et steg er stegene i after + ingrediensene i uses.
3. Ingrediensrekkefølge = dybde-først gjennom treet, venstre gren først
   (sorter barna etter global_order_index). Da ligger ingrediensene under
   hvert steg alltid i sammenhengende rader, som er det rowspan krever.
4. Kolonne for et steg = høyden i treet (avstand til lengste blad).
   Bladene (ingrediensene) er kolonne 0. Sluttsteget er siste kolonne.
5. Celle for et steg: rowspan = antall ingrediensrader under steget.
   Fyll hull mellom en ingrediens og første steg som bruker den med tomme celler.
6. Steg uten ingredienser og uten after (smør form, forvarm ovn) blir
   helbredde rader øverst i tabellen.
```

Hvis grafen ikke er et tre (et mellomprodukt brukes av to steg), kan ikke tabellen tegnes riktig. Fall da tilbake til metrokartet.

---

## 4. Status per visning (oppdatert)

«I dag» betyr hva som kan lages på dagens data uten skjemaendringer.

| # | Visning | I dag | Hva vi kan lage nå | Hva som mangler for full versjon | Avhenger av |
|---|---|---|---|---|---|
| 4 | Kortmodus | Ja | Ett steg per kort, fasefarge, timer fra `estimated_minutes` | Ingredienser på kortet, skalerte mengder i teksten, `done_when`, aktiv/passiv tid | 1, 2, 3 |
| 3 | Baklengs fra servering | Ja, sekvensielt | Klokkeslett fra summen av `estimated_minutes`, regnet bakover | Parallellitet (ellers blir totaltiden for lang), aktiv/passiv tid, én kilde for totaltid | 1, 3 |
| 1 | Mise en place-brett | Delvis | Én skål per ingrediens gruppert på komponent, prep-steg som oppgavekort | `prep_style` i AI-skjemaet (helst fast liste), bollegruppering via `uses`, `portion` for delte ingredienser | 1, 3 + `prep_style` |
| 2 | Tidslinje | Delvis | Trapp i `global_order_index`-rekkefølge, ingen parallellitet | `after`, aktiv/passiv tid, planleggingsalgoritme | 1, 3 |
| 7 | Ingredienser i steget | Nei | (bare skjør fuzzy matching) | Kobling steg ↔ ingrediens, maltekst, `portion` | 1, 2 |
| 6 | Metrokartet | Svakt | Parallelle linjer per komponent som ender i ett punkt | Sammenslåing via `after` på tvers av komponenter, `component`-tabell, `output_label`, korte stasjonsnavn | 1, 3 |
| 11 | Tabellmetoden | Nei | – | Hele grafen (`uses`, `after`), kort verb per steg, temperatur og tid strukturert | 1, 3 |

Hvilke visninger hver endring åpner for:

| Endring | 1 | 2 | 3 | 4 | 6 | 7 | 11 |
|---|---|---|---|---|---|---|---|
| 1. ID-er + `uses`/`after` | ● | ● | ● | ◐ | ● | ● | ● |
| 2. Maltekst | | | | ● | | ● | |
| 3. Stegattributter | ◐ | ● | ● | ◐ | ◐ | | ● |

● = nødvendig for full versjon. ◐ = gjør visningen bedre.

---

## 5. Tre endringer som åpner for nesten alt

### Endring 1: Lokale ID-er og koblinger (oppskriften blir en graf)

Dette er den viktigste endringen. Gi hver ingredienslinje, hver komponent og hvert steg en ID som er lokal for oppskriften (`i1`, `c1`, `s1`). La stegene peke på ingrediensene de bruker (`uses`) og på stegene som må være ferdige først (`after`).

Med dette blir oppskriften en rettet asyklisk graf. Sammenslåing mellom komponenter faller ut av seg selv: et steg i «Assembly» som har `after` på siste steg i både bunnen og fyllet, *er* sammenslåingen. Det trengs ikke et eget `merges_into`-felt.

**AI-skjema (`ai_engine.py`).**

```python
class Ingredient(typing.TypedDict):
    id: str                       # NY: "i1", "i2", ... unik i oppskriften
    name: str
    amount: float
    unit: str
    gram_weight_estimate: float
    prep_style: typing.NotRequired[str]   # NY: fra fast liste
    pantry_id: typing.NotRequired[str]

class IngredientUse(typing.TypedDict):
    ingredient_id: str            # "i3"
    portion: typing.NotRequired[float]    # 0–1, utelatt = hele mengden

class Instruction(typing.TypedDict):
    id: str                       # NY: "s1", "s2", ...
    step_number: int
    phase: str
    text: str                     # NY semantikk: maltekst, se endring 2
    uses: list[IngredientUse]     # NY
    after: list[str]              # NY: steg-ID-er som må være ferdige
    output_label: typing.NotRequired[str] # NY: "the custard", "the dough"
    estimated_minutes: int
    global_order_index: int

class ComponentSchema(typing.TypedDict):
    id: str                       # NY: "c1"
    name: str
    steps: list[Instruction]

class IngredientGroup(typing.TypedDict):
    component_id: str             # ENDRET: peker på komponent-ID, ikke navn
    ingredients: list[Ingredient]
```

At ingrediensgrupper peker på `component_id` i stedet for navn, fjerner problemet med «Egg Custard» vs «Custard».

**Database.**

```
component
  id, recipe_id, local_id ("c1"), name, sort_order

recipe_ingredient            (eksisterende)
  + local_id ("i1")
  + component_id → component (erstatter fritekst-component)

instruction                  (eksisterende)
  + local_id ("s1")
  + component_id → component (erstatter fritekst-component)
  + output_label

instruction_ingredient       (ny koblingstabell)
  instruction_id → instruction
  recipe_ingredient_id → recipe_ingredient
  portion (float, nullable; null = hele mengden)

instruction_dependency       (ny koblingstabell)
  instruction_id → instruction        (steget som venter)
  depends_on_id → instruction         (steget som må være ferdig)
```

Behold fritekst-`component` på `recipe_ingredient` og `instruction` i en overgangsperiode, slik at eldre maler og oppskrifter fungerer til migreringen er ferdig.

**`global_order_index`** beholdes som AI-ens foretrukne lineære rekkefølge. Kortmodus bruker den. Den skal ikke lenger være sannheten om hva som kan skje parallelt. Det er `after` som avgjør det. Validatoren sjekker at rekkefølgen er en gyldig topologisk sortering av grafen.

**Promptinstruks til Gemini (utdrag).**
> Give every ingredient an id (i1, i2, …), every component an id (c1, c2, …) and every step an id (s1, s2, …). For each step, list in `uses` the ingredients it adds for the first time, and in `after` the steps whose result it needs. A step that combines two components must list the last step of each in `after`. Steps that need nothing (preheat oven, grease pan) have an empty `after`. Every ingredient must be used by exactly one step, unless it is split, in which case use `portion` so the portions sum to 1.

### Endring 2: Maltekst i stegene

I dag står mengdene i fritekst: `"Whisk 3 eggs until smooth"`. Når brukeren skalerer til 6 porsjoner, blir ingredienslista riktig, men teksten fortsatt feil. Med maltekst lagres steget som:

```
"Whisk {i3} in a medium bowl until smooth."
```

og rendres som «Pisk **3 egg** i en middels bolle til glatt», med riktig mengde for valgt antall porsjoner.

**Syntaks.**

| Mal | Rendres som | Bruk |
|---|---|---|
| `{i3}` | «3 egg» (mengde, enhet, navn, skalert) | Standard |
| `{i3:name}` | «eggene» | Når mengden allerede er nevnt |
| `{i3:amount}` | «3» | Sjelden, for egen formulering |
| `{s5}` | `output_label` fra steg s5 («custarden») | Mellomprodukter |

Når `portion` er satt på koblingen, bruker `{i3}` den andelen av mengden («halvparten av smøret» → «60 g smør»).

**Regler.**
- Alle `{iN}` i teksten må finnes i `uses` for steget, eller i `uses` for et tidligere steg (for `:name`-referanser).
- Alle ingredienser i `uses` bør forekomme i teksten. Validatoren gir advarsel, ikke feil, hvis ikke.
- Renderen må tåle tekst uten maler, slik at gamle oppskrifter vises som før.
- Maltekst løser også visning 7 helt: merkelappene er bare `{iN}` rendret som en pille i stedet for tekst.

### Endring 3: Strukturerte stegattributter

Dette er bare nye felter i AI-skjemaet og nye kolonner på `instruction`. Ingen nye relasjoner. Det er den billigste av de tre endringene, og den bør gjøres først.

| Felt | Type | Eksempel | Brukes av |
|---|---|---|---|
| `action` | enum fra fast liste | `whisk` | 6, 11 (stasjons- og cellenavn), parkert 8 (piktogram) |
| `text_short` | streng, maks ~5 ord | `"Whisk eggs"` | 4 (overskrift), 6, 11 |
| `active_minutes` | int | `3` | 2, 3 |
| `passive_minutes` | int | `0` | 2, 3 |
| `equipment` | enum | `bowl`, `saucepan`, `oven` | 1 (utstyrsliste), parkert 5 (komfyrkartet) |
| `heat` | enum, nullable | `low`, `medium`, `high` | 4, parkert 5 |
| `temp_c` | int, nullable | `175` | 4, 11 (sluttcellen) |
| `done_when` | streng, nullable | `"No streaks of white left"` | 4, 11, parkert 9 |

**Fast liste for `action`** (legges i `data/constraints/` sammen med de eksisterende listene): `chop`, `slice`, `grate`, `measure`, `mix`, `whisk`, `fold`, `knead`, `melt`, `saute`, `fry`, `sear`, `boil`, `simmer`, `bake`, `roast`, `grill`, `rest`, `chill`, `marinate`, `blend`, `season`, `assemble`, `plate`, `serve`. Utvid etter behov, men hold lista kort nok til at hvert verb kan få et ikon.

**`estimated_minutes`** beholdes i overgangsperioden som `active_minutes + passive_minutes`, slik at eksisterende kode fungerer.

**`chef_note`** bør få en kolonne samtidig, siden den allerede genereres og kastes.

---

## 6. Validering før lagring

Gemini vil lage grafer med feil: referanser til ID-er som ikke finnes, ingredienser som aldri brukes, sirkulære avhengigheter. Legg en deterministisk validator i `process_recipe_workflow`, før noe skrives til databasen.

**Feil (avvis og prøv på nytt):**
1. Alle ID-er er unike innenfor sin type.
2. Alle ID-er i `uses`, `after`, `component_id` og maltekst finnes.
3. Grafen har ingen sykler.
4. Det finnes nøyaktig ett sluttsteg (et steg som ingen andre har i `after`). Unntak: rene `Serve`-steg kan henge etter sluttsteget.
5. Hver ingrediens brukes minst én gang. Summen av `portion` for samme ingrediens er 1 (med litt toleranse).
6. `action`, `equipment` og `heat` har gyldige verdier fra de faste listene.

**Advarsler (lagre, men flagg med `is_flagged_for_review`):**
1. `global_order_index` er ikke en gyldig topologisk sortering.
2. En ingrediens i `uses` står ikke i stegets tekst.
3. Et `Cook`-steg kommer før et `Prep`-steg det ikke avhenger av (ikke nødvendigvis feil, men verdt å se på).
4. Summen av stegtid avviker mye fra `prep_time_mins`.

**Ved feil:** send feilmeldingene tilbake til Gemini sammen med forrige svar («Fix these errors: s7.after references s12, which does not exist») og be om et korrigert svar. Maks to forsøk, deretter lagres oppskriften som draft med flagg. Dette er billigere og mer pålitelig enn å la `recipe_evaluation` gi lav score i etterkant.

Vurder også en ny delscore i `recipe_evaluation` for grafkvalitet (er sammenslåingene riktige, gir `done_when` mening).

---

## 7. Migrering av eksisterende oppskrifter

Informasjonen som trengs, står allerede i dagens stegtekst. Én LLM-kjøring per oppskrift kan fylle ut grafen:

> Input: ingrediensliste (med recipe_ingredient-ID-er) og steg (med instruction-ID-er og tekst).
> Output: per steg `uses`, `after`, `output_label`, `action`, `text_short`, `active_minutes`, `passive_minutes`, `equipment`, `heat`, `temp_c`, `done_when`, og teksten omskrevet til maltekst.

Fremgangsmåte:
1. Legg til `schema_version` på `recipe` (1 = dagens, 2 = med graf). Renderen velger visninger ut fra versjonen.
2. Kjør migreringen på et utvalg draft-oppskrifter først og se på resultatet manuelt.
3. Kjør samme validator som for nye oppskrifter. Oppskrifter som feiler, beholdes på versjon 1.
4. Visningene som krever grafen (6, 7, 11), skjules for versjon 1-oppskrifter. Kortmodus og baklengs fra servering fungerer for begge versjoner.

---

## 8. Foreslått rekkefølge

1. **Fase 0, på dagens data.** Kortmodus (4) og baklengs fra servering (3, sekvensielt). Gir verdi med en gang og tester hvordan brukerne faktisk lager mat med appen.
2. **Fase 1, endring 3.** Nye felter i AI-skjemaet og kolonner på `instruction`, `prep_style` i `Ingredient`, kolonne for `chef_note`. Gir `done_when` i kortmodus og en bedre mise en place-visning (1).
3. **Fase 2, endring 1 og 2 sammen.** Begge krever ID-er på ingrediensene, så de bør gjøres i samme runde. Inkluderer `component`-tabellen, koblingstabellene og validatoren.
4. **Fase 3, migrering.** Backfill av eksisterende oppskrifter til `schema_version = 2`.
5. **Fase 4, grafvisningene.** Ingredienser i steget (7), tidslinjen med parallellitet (2), bollegruppering i mise en place (1), metrokartet (6) og tabellmetoden (11).

Tabellmetoden og ingredienser i steget er de to visningene som skiller appen mest fra andre oppskriftsapper. Kortmodus er den brukerne vil bruke mest.

---

## 9. Avklaringer etter prototypen (oktober 2026)

Prototypen `docs/prototypes/grill-kreta.html` tegner sju oppskrifter fra samme datamodell. Arbeidet med den ga avklaringene under. Der de avviker fra kapitlene over, gjelder dette kapitlet.

### 9.1 `after` og `waits` er to forskjellige ting

- `after`: maten går videre fra et steg til et annet (marinaden går inn i kjøttet).
- `waits`: steget må bare vente på noe (grillen må være varm, pitaen varmes etter at kjøttet er ferdig).

Tabellmetoden og metrokartet bruker bare `after`. Planleggeren bruker begge. Lagres en ren ventetid som `after`, havner kjøttet «inni» pitaen i tabellen.

### 9.2 Definisjon av fasene

`phase` skal ikke velges fritt av AI-en. Den utledes av to spørsmål per steg, i denne rekkefølgen:

1. **Brukes det varme i steget, eller hviler maten rett etter varme?** Da er det `cook`. Det gjelder også oppvarming av utstyr (forvarm ovn, tenn grill, kok opp vann). Slike steg får i tillegg `setup: true`, fordi de kan gå mens man gjør prep.
2. **Er dette siste hånd på maten rett før den spises?** Da er det `serve`: skjære ferdig kjøtt, vende salat i dressing, sette sammen, anrette.
3. **Alt annet er `prep`**: kutte, måle, blande, marinere, forme, pakke inn.

Regelen kan sjekkes maskinelt når `method` finnes (9.6): varmemetoder gir `cook`.

Fasene er en egenskap ved steget, ikke tre sammenhengende tidsblokker. I en lasagne kommer de i rekkefølgen cook (saus), prep (legg lagvis), cook (stek), serve. Derfor trengs ett begrep til:

- **Forhåndssteg** = et prep-steg der ingen steg oppstrøms (`after`/`waits`) er `cook`. Dette er det som kan gjøres før varmen er på, og det er dette mise en place-brettet og «prep-fasen» i grensesnittet viser. Det utledes fra grafen og lagres ikke.

### 9.3 Hva bestemmer rekkefølge og tidspunkt

1. **Avhengighetene** (`after`, `waits`). De er absolutte.
2. **Varighetene** og regelen om at én kokk bare gjør ett aktivt steg om gangen. Passiv tid kan overlappe alt.
3. **Hvor lenge ting tåler å stå** (9.4).
4. **Strategien**, som er et valg og ikke en egenskap ved oppskriften:
   - `jit` («akkurat i tide»): hvert steg legges så sent som mulig før servering. Prep flettes inn mens noe annet står. Gir kortest tid og ferskest mat, men mer å holde styr på.
   - `prep_first` («prep først»): alle forhåndssteg gjøres ferdig før første cook-steg som ikke er `setup`. Gir en rolig kokefase og passer med mise en place. Kan gi lengre totaltid når det ikke finnes ventetid å fylle.

Begge er implementert i prototypen (`schedule(r, mode)`). Rekkefølgen blir ulik i fire av sju oppskrifter. Totaltiden ble lik i alle sju, fordi kullene uansett trenger 30 minutter. Det vil ikke gjelde generelt.

Strategien bør være en brukerinnstilling, med `prep_first` som standard. Oppskriften lagrer bare graf og varigheter. `global_order_index` blir da en avledet verdi per strategi.

### 9.4 Fleksibel ventetid (marinering, heving, kjøling)

To felter på steget dekker både «minst 30 minutter, maks 4 timer» og «kan gjøres dagen før»:

| Felt | Betydning | Marinade | Tzatziki | Grillet biff |
|---|---|---|---|---|
| `passive_minutes` | Minste ventetid før resultatet kan brukes | 30 | 30 | 0 |
| `holds_minutes` | Hvor lenge resultatet tåler å stå etter det | 210 | 1440 | 5 |

Maksimum er summen. Planleggeren regner med `passive_minutes`, og bruker `holds_minutes` som grense for hvor tidlig et steg kan flyttes. Validering: ventetiden fra et steg er ferdig til resultatet brukes, skal ikke overstige `holds_minutes`.

I visningene:
- **Tidslinje:** skravert stolpe for minstetiden. Prikket omriss for tiden resultatet faktisk venter. Rødt hvis den går over grensen.
- **Baklengs fra servering:** «klar 18:39, tåler å stå til 22:09». Et steg med stor `holds_minutes` kan tilbys som «gjør dette tidligere på dagen».
- **Kortmodus:** timeren går på minstetiden. Kortet viser «minst 30 min, maks 4 t».
- **Mise en place:** forhåndssteg med `holds_minutes` over noen timer kan merkes «kan gjøres på forhånd».
- **Metrokart og tabell:** viser bare minstetiden i tekst.

### 9.5 Erstatninger, forenklet

- Generelle par i pantryet: `substitution(ingredient_id, substitute_id, ratio)`.
- Valgfri overstyring per oppskrift på ingredienslinjen: `substitutes: [{ingredient_id, form_id, ratio}]`.
- Ingen merknad om effekt. Ingen lagring av valg per bruker. Et bytte er tilstand i klienten for den økten.
- Byttet virker bare fordi stegteksten bruker referanser (`{i3}`). Ingrediensliste, stegtekst, bilde og handleliste følger da med av seg selv.

### 9.6 Metode, utstyr og innstilling, forenklet

*Utstyrsdelen er erstattet av 9.10, der `equipment` er en liste per steg. `method`, `temp_c` og `mode` gjelder fortsatt.*

Fire felter per steg, alle fra faste lister i `data/constraints/`:

| Felt | Eksempel |
|---|---|
| `method` | `bake`, `airfry`, `pan_fry`, `grill`, `boil`, `none` |
| `equipment` | `oven`, `airfryer`, `frying_pan`, `saucepan`, `grill`, `bowl` |
| `temp_c` | `220` |
| `mode` | `fan`, `top_bottom`, `grill_element` for ovn. `low`, `medium`, `high` for plate og grill |

Utstyrslisten for hele oppskriften utledes fra stegene. Utelatt med vilje: rillehøyde, lokk, egen utstyrstabell og varianter per utstyr (ovn eller airfryer).

**Utstyrsbanken (22.10.2026).** Hovedformålet er å vise med symboler hva man trenger av utstyr til retten. Katalogen er `data/constraints/equipment.json`, uten noe mer avansert enn den hadde:

- **To nivåer:** `standard` (det de fleste kjøkken har, grunnutstyr og vanlig utstyr slått sammen) og `special` (sous vide, frityrgryte, wok, kjøkkenmaskin, vaffeljern …). Spesialutstyr vises med stiplet kant.
- **Forbruksvarer** (`kind: supply`: plastfolie, bakepapir, folie, kjøkkenhåndkle, tallerken, serveringsfat, lokk) brukes i planen, men vises ikke som utstyr.
- **Duplikater** slås sammen med `same_as`: stor bolle vises som bolle, støpejernsgryte som vid gryte, form 20 × 30 som ildfast form. Id-ene beholdes, så lagrede oppskrifter virker som før.
- **Nytt:** hullsleiv, potetstapper, måleskjeer, kjøkkensaks, vaffeljern, riskoker og trykkoker. 69 oppføringer, 59 symboler.
- **Symboler** i samme stil som ingrediensene (labboppgaven `equipment_image`, «vector_textured»): tomt redskap, fast vinkel skrått ovenfra, ingen merkenavn, fyller 80 %. `scripts/equipment_symbols.py` lager dem (først åtte som prøve, sjekket i 48 og 32 px), laster dem opp og setter `image` i katalogen.
- **Vises** på Gjør klart som fliser med symbol, i den rekkefølgen utstyret brukes. Ikke på Overview.
- **Tre sett til prøving (23.10.2026):** realistisk (`image`), malt og strek med én farge (`image_variants`), 59 i hvert. Admin bytter med «Tools» i admin-brikken; besøkende ser det realistiske. Erfaring fra kjøringene: bildemodellen tegner det som nevnes i prompten, også det den blir bedt om å la være («no spoon» ga en skje), og la en skje i nesten alle tomme boller og gryter uansett. Det som virket, var å redigere bildet: det eksisterende bildet og «Remove the spoon», resten beholdes (`scripts/equipment_symbols.py edit`).

### 9.7 Bilder som harmonerer

I dag lages komponentbildene uavhengig av bildet av retten. `generate_component_images` i `app.py` sender bare komponentnavnet til bildemodellen («just {comp} alone … on white background»). Bildene kan derfor ikke stemme med hverandre annet enn ved flaks.

Anbefalt rekkefølge:

1. **Oppskriften ferdig og validert.** Bilder lages aldri før dataene er låst.
2. **Utseendebeskrivelse per komponent** (`appearance`), utledet fra dataene: kutt og størrelse, farge etter tilberedning, garnityr, antall per porsjon. «Fire spyd med 3 cm terninger av lam, mørk grillskorpe, rosmarin.»
3. **Felles stil for oppskriften** (`image_style`): vinkel, lys, underlag, servise. Én blokk som brukes i alle bilder av denne retten.
4. **Bildet av hele retten først.** Prompten settes sammen av alle `appearance`-tekstene, anretningen og stilen. Dette er det viktigste bildet og bør ha færrest bindinger.
5. **Kontroll av rettbildet** med en synsmodell mot komponentlisten: er alle komponentene synlige, og stemmer antall og kutt?
6. **Komponentbildene til slutt, med rettbildet som referansebilde.** Modellen får bildet av retten og beskjed om å vise bare denne komponenten, slik den ser ut der. Det krever en bildemodell som tar bilde inn. Finnes ikke det, brukes veien dere allerede har: en synsmodell beskriver komponenten slik den ser ut i rettbildet, og den beskrivelsen pluss `image_style` blir prompten.
7. **Kontroll av hvert komponentbilde** mot rettbildet.

Metadata som trengs: `appearance` og `image_filename` på komponenten, `image_style` og `hero_image_prompt` på oppskriften, og `derived_from` på komponentbildet. Lages rettbildet på nytt, er komponentbildene foreldet og må lages på nytt.

Ingrediensbildene hører ikke hjemme her. De ligger i pantryet, har én felles stil for hele appen og lages én gang per ingrediens og form.

### 9.8 Ingrediensformer og enheter

Se kravlisten fra gjennomgangen: en ingrediens har flere *former* (hel hvitløk, fedd; egg, plomme, hvite; sitron, saft, skall), hver med navn i entall og flertall, gram per stykk, bilde og forholdet til det man kjøper. Enheter ligger i en egen tabell med ml per enhet og et flagg for omtrentlige mål (klype). Fra volum til gram trengs tetthet per ingrediens og form. Dette er forutsetningen for riktig mengdevisning, handleliste på tvers av komponenter og bilder per form.

---

### 9.9 Sammenligningssiden: fem retter, seks visninger

`docs/prototypes/fem-retter.html` tegner fem retter med ulik oppbygning i de seks gjenværende visningene. **Visning 3, baklengs fra servering, er parkert inntil videre.**

| Rett | Komponenter | Hva den tester |
|---|---|---|
| Spaghetti carbonara | 1 | Ingrediensformer (egg og eggeplommer), ingrediens delt mellom steg, biprodukt som brukes senere |
| Brownies | 1 | Baking i gram, tabellmetoden, prep både før og etter varme |
| Kylling tikka masala med ris | 2 | Fleksibel marinering, mange krydder, ingredienser delt mellom marinade og saus |
| Lasagne | 3 | Komponentene møtes midt i oppskriften, fasene går cook, prep, cook, serve |
| Hamburger med brød og pommes frites | 3 | Komponent som kan kjøpes i stedet (av/på), to ting i samme ovn, tung serve-fase |

Det som er nytt i datamodellen på denne siden:

- **Delte ingredienslinjer.** En ingrediens som brukes på to tidspunkter, står som to linjer (pecorino 60 g og 20 g). Dette erstatter andel per bruk (`pe@0.75`), som ble brukt i første versjon av siden. Se 9.10.
- **Handleliste for hele retten.** Ingredienslinjer med samme navn summeres på tvers av komponenter. En form kan peke på det man kjøper (`buy`): 2 egg + 4 eggeplommer gir «6 egg, 4 eggehviter til overs».
- **Utstyr som ressurs.** Steg med `excl: true` kan ikke overlappe andre steg på samme utstyr. Brød og pommes frites i samme ovn legges derfor etter hverandre.
- **`hold` håndheves.** I «prep først» flyttes et forhåndssteg aldri tidligere enn resultatet tåler å stå. Tåler det ikke ventetiden, faller det tilbake til siste mulige plass.
- **Metode, utstyr og innstilling** (`eq`, `temp`, `mode`) vises i kortmodus, ingredienser i steget og tabellen.
- **Variant.** Hamburgeren finnes med hjemmelaget og kjøpt brød. Byttet endrer komponenter, ingrediensliste og plan.
- **Mise en place** deler skålene i to: det som kan gjøres klart på forhånd, og det som bare settes frem og brukes underveis.

Funn fra siden:

- «Prep først» koster tid når det ikke finnes ventetid å fylle: brownies 118 mot 112 minutter, hamburger med kjøpt brød 61 mot 52. For de tre andre er totaltiden lik.
- Metrokartet gir lite for retter med én komponent. Det blir én rett linje.
- Tabellmetoden blir høy når retten har mange ingredienser (tikka masala har 29 rader), men den er fortsatt lesbar.
- Fasene veksler i brownies og lasagne. Faseskillene i metrokartet tegnes derfor hver gang fasen skifter, ikke bare én gang.

---

### 9.10 Mise-element og utstyr (forenklet modell)

**Mise-element** er det faste begrepet. Et mise-element er *det som står klart når prep er ferdig, og helles i på samme tidspunkt*. Eksempler: marinert kylling, krydderblandingen, løk og gulrot hakket sammen, eggeblandingen.

Forholdet til de andre nivåene:

**ingrediens → mise-element → (cook-steg → mellomprodukt)… → komponent → rett**

- *Komponent* er det som kommer ut: det du kan peke på på tallerkenen (kjøttsaus, ris, pommes frites).
- *Mise-element* er det som går inn: det som står i en skål og venter på å bli helt i.
- *Mellomprodukt* er resultatet av et cook-steg (den brunede kjøttdeigen). Det er verken mise-element eller komponent.
- Prep lager mise-elementer, cook bruker dem. Mise en place er derfor ikke en egen visning, men fasen mellom ingredienslisten og stegene.

Regler for AI-en:
1. Alt som helles i samme steg på samme tidspunkt, er ett mise-element.
2. Samme ingrediens på to tidspunkter blir to ingredienslinjer i hvert sitt mise-element.
3. Ting som blandes i prep (marinade og kylling), er ett mise-element når prep er ferdig.
4. Olje til steking og alt «etter smak» er basisvarer og får ikke mise-element.

Datamodell:

```
mise_element
  id
  recipe_id
  name            «Krydderblandingen»
  used_in_step    steget der det helles i

recipe_ingredient
  + mise_element_id   (tom for basisvarer)
```

Alt annet utledes:
- komponent fra steget elementet brukes i
- rekkefølge på brettet fra planen
- hvilke prep-steg som lager det fra stegene som bruker linjene
- klar-tilstand (mykt, romtemperert) er fritekst i `prep_style`, og tid som trengs, er et eget prep-steg med passiv tid

**Delte linjer erstatter andel per bruk.** Pecorinoen i carbonaraen er to linjer, 60 g og 20 g. Ingredienslisten summerer linjer med samme ingrediens og form. `portion` og koblingstabellen trengs ikke.

**Validering:**
- hver linje unntatt basisvarer har et mise-element
- hvert mise-element brukes av et steg som finnes
- hver linje i elementet når steget elementet brukes i, gjennom prep-stegene

Den siste regelen fanger feilen fra første versjon av siden, der skålen «Løken» inneholdt smør og olje.

**Utstyr:**

```
steg
  equipment: ['vid_gryte', 'tang']    første er kokekaret
  temp_c, mode                        gjelder kokekaret

data/constraints/equipment.json       fast katalog: id, navn, rolle (koke, forberede, avlastning)
```

Utstyrslisten for retten er unike verdier sortert etter første bruk. Størrelse står bare i katalog-ID-en der den betyr noe (`stor_kjele`, `form_20x30`). Forvarming er `setup`-steg. Antall droppes. Det faste oppsettet (skjærebrett, kniv, kluter, avfallsbolle, salt, pepper, olje) er én fast liste i appen.

Prototypen `fem-retter.html` bruker denne modellen. Der er mise-elementene lagt inn som en liste med linjer per element, og `eq` pluss `tools` på steget tilsvarer `equipment`.

### 9.11 Forkant og økter (forslag)

En lang ventetid, som pinnekjøtt i vann over natten eller fire timers marinering, gjør at «prep-fasen» ser ut som mange timer, selv om du jobber i fem minutter. Problemet er at én tidsakse blander medgått tid og innsats.

Forslaget krever ingen nye felter. `passive_minutes` og `holds_minutes` holder.

- **Fase** er fortsatt en egenskap ved steget. Kutting er alltid prep.
- **Økt** er et nytt, utledet begrep for *når* du gjør det. Et forhåndssteg med lang ventetid (for eksempel 90 minutter eller mer) legges i en egen **forkant-økt**, med eget tidspunkt («i går kl. 21: legg pinnekjøttet i vann, 5 min»).
- Resten deles i **prep-økt** og **koke-økt**.
- Tidslinjen viser øktene med brutt akse: «… 4 t marinering …» i stedet for fire timer tom flate.
- Tidsangivelsen splittes: «Prep 25 min · Koking 40 min · Forkant: 5 min, kvelden før». Aldri «Prep 4 t 25 min».

---

### 9.12 Tre planstrategier, med «rolig» som standard

Når et steg gjøres, er ikke en egenskap ved oppskriften. Oppskriften lagrer bare avhengigheter, varigheter og hvor lenge ting tåler å stå. Planleggeren velger tidspunkt etter en strategi, som er en brukerinnstilling:

| Strategi | Regel |
|---|---|
| **Rolig** (standard) | Prep gjøres før kokingen, men et prep-steg kan legges i en fri periode der bare varmen jobber (ovn, småkoking, heving). Det krever at perioden ikke har aktive steg, at steget får plass med 2 minutters slingring, og at resultatet brukes etter perioden. Prep havner aldri mellom to aktive cook-steg |
| **Prep først** | Alt som ikke trenger varme, gjøres før første cook-steg (streng mise en place) |
| **Akkurat i tide** | Hvert steg så sent som mulig, også mellom aktive cook-steg |

Begrunnelse: mise en place skal beskytte de *aktive* kokeperiodene. Å kutte salaten mens lasagnen står i ovnen bryter ikke med det. Å hakke løk mens kjøttdeigen brunes, gjør det.

Totaltid i prototypen (minutter):

| Rett | Rolig | Prep først | Akkurat i tide |
|---|---|---|---|
| Lasagne med grønn salat | 105 | 115 | 105 |
| Hamburger med kjøpt brød | 52 | 61 | 52 |
| Brownies | 116 | 118 | 112 |
| Carbonara, tikka masala, hamburger med hjemmelaget brød | lik i alle tre | | |

**Stegtekst uten tidsord.** Stegteksten sier hva du gjør, ikke når. «Mens lasagnen står» genereres fra planen (`during` = det passive cook-steget et prep-steg legges i). Formuleringer om teknikk inne i ett steg, som «spe med melk mens du visper», er greit.

**Mise en place per økt.** Brettet grupperer mise-elementene etter når forarbeidet gjøres i den valgte planen: «Før du starter» og «Mens lasagnen står». Elementene er de samme i alle strategier.

---

### 9.13 Skåler, «ta frem» og «på benken»

Definisjonen av mise-element står uendret. To ting er endret:

1. **Alle ingredienslinjer får et mise-element**, også olje til steking og salt i kokevannet. Validatoren krever det uten unntak.
2. **Basisvarer er en egenskap ved ingrediensen i pantryet** (`is_staple` på salt, pepper og oljer), ikke en liste per oppskrift.

Brettet deler mise-elementene i tre. Inndelingen utledes og lagres ikke. **Reglene for skål er strammet inn i 9.15** (oktober 2026), så lasagnen får fire skåler i stedet for ti. Tabellen under er den første versjonen:

| Type | Regel | Vises som |
|---|---|---|
| Skål | Flere linjer, eller forarbeid (et prep-steg rører den, eller `prep_style` beskriver kutt, riving, temperatur eller tilstand) | Skål sett ovenfra med opptil fire ingrediensbilder (tre og «+N» ved flere), og liste med mengder |
| Ta frem | Én linje uten forarbeid | Flis med bilde, mengde og navn |
| På benken | Ta frem-element der ingrediensen er basisvare, og alle linjer «etter smak» | Liten rad nederst |

Basisvarer som blandes med noe (olivenolje i dressingen), blir i skålen. `prep_style` som bare er en merknad («til kokevannet»), regnes ikke som forarbeid.

Nummereringen følger rekkefølgen elementene helles i, på tvers av skåler og fliser, og alt grupperes per økt («Før du starter», «Mens lasagnen står»).

**Ingrediensbilder:** ett bilde per ingrediens i pantryet, felles for hele appen, laget med den eksisterende bildeveien (`regenerate_image`). Fast stil sett ovenfra, gjennomsiktig bakgrunn (fjernes automatisk etter generering), 512 px med mindre utgaver. Reservekjede: form → ingrediens → kategoriikon → forbokstav i kategorifarge. Prototypen viser forbokstaven. Kuttet tilstand vises som et lite merke på bildet (kniv, rivjern), ikke som egne bilder.

---

### 9.14 Tabellmetoden følger planen

Kolonnene i tabellmetoden er ikke en tidsakse. Et steg står i kolonnen som tilsvarer antall bearbeidingsledd foran det, så alle grener starter i kolonne 1. Med planstrategiene ga det et misvisende bilde: salaten sto lengst til venstre, selv om den kuttes mens lasagnen står i ovnen.

Regel: **steg som starter etter at kokingen er i gang, høyrejusteres inntil steget som bruker dem.** Steg i prep-økten står som før. Med «Rolig» havner salaten i samme kolonne som «Stek lasagnen», og den hvite sausen flytter seg til høyre for kjøttsausen. Med «Prep først» står salaten til venstre, og «Vend salaten» står rett før servering.

Teksten under tabellen er rettet til: «Kolonnene viser rekkefølgen innenfor hver del av retten. Det som gjøres underveis, står inntil steget det brukes i.» Den gamle teksten («Kolonnene går fra venstre mot høyre i tid») var feil.

---

### 9.15 Telefonflyten (steg 7a, oktober 2026)

Prototype: `docs/prototypes/telefon.html`, laget i tre runder med tilbakemelding 19.10.2026. Oppskriftene, planleggeren og mise-utledningen er de samme som i `fem-retter.html`, og symbolene er ingredienssymbolene fra produksjon.

**Fordeling:** telefonen er for å lage maten, stor skjerm for å forstå og planlegge den. Av de seks visningene fungerer kortmodus og ingredienser i steget godt på telefon, og mise en place-brettet fungerer som sjekkliste. Tidslinjen, metrokartet og tabellmetoden fungerer ikke i 375 px bredde. De vises ikke på telefon. Det nyttige fra tidslinjen, «nå og neste», er flyttet inn i kortmodus.

| | Telefon | Stor skjerm |
|---|---|---|
| Før du starter | Oversikt | Oversikt og metrokartet |
| Forberedelse | Gjør klart | Gjør klart ved siden av handlelisten |
| Matlaging | Kort med «pågår», eller liste over steg | Ingredienser i steget med tidslinjen ved siden av |
| Plan og oversikt | Ikke tilgjengelig | Tidslinjen, metrokartet og tabellmetoden |

Telefonflyten bygges først (steg 7b). Utformingen på stor skjerm gjøres i 7c. Nettbrett på kjøkkenbenken regnes som stor skjerm.

**Flyten:** tre steg i toppfeltet: Oversikt, Gjør klart, Lag mat. I appen heter fanene Overview, Prep og Cook (21.10.2026). Mengde, plan og variant (brødet til hamburgeren) ligger bak en meny (☰) og gjelder alle tre.

**Oversikt** viser totaltid, aktiv tid, mengde, delene retten består av, én handleliste og utstyret. Handlelisten har hver ingrediens én gang, summert, med en merknad når den brukes flere ganger («brukes 2 ganger») eller i flere deler («Kjøttsaus og salat»). En liste per del ble valgt bort: når samme ingrediens brukes to ganger i samme del (hvitløk i marinaden og i sausen), sto den to ganger under samme overskrift. Fordelingen per del og steg kommer i Gjør klart og på kortene, der den brukes.

**Gjør klart** viser bare det som trenger en skål, som skål. Et mise-element er en **skål** når minst ett av disse gjelder:

1. **Forarbeid:** et prep-steg rører linjen, eller `prep_style` beskriver kutt, riving, temperatur eller tilstand. Produktbeskrivelser som «hakkede» og «knuste» tomater er ikke forarbeid. De hører hjemme i pantryet som egne varer.
2. **Blanding:** minst tre små mengder (ts, ss, klype eller høyst 30 g) går i samme steg, som en krydderblanding.
3. **Tidspress:** minst to linjer går i et steg med varme på middels eller høyere og høyst 2 aktive minutter, så det ikke er tid til å måle ved komfyren.

Resten er **ta frem**: et rutenett av fliser med symbol, mengde og navn, som måles når de brukes. Basisvarer alene og alt «etter smak» står **på benken**. Ett trykk per skål og per flis merker den som klar, uten avkrysning per linje. Bare skålene nummereres, i den rekkefølgen de brukes.

| Rett | Nummererte elementer før | Skåler nå | Ta frem nå |
|---|---|---|---|
| Carbonara | 4 | 3 | 1 |
| Brownies | 4 | 2 | 3 |
| Tikka masala | 8 | 6 | 5 |
| Lasagne | 10 | 4 | 11 |
| Hamburger | 9 | 7 | 2 |

**Mise-elementene utledes fra grafen med disse reglene. AI-en trenger ikke lage dem** (spørsmålet i `RECIPE_MODEL_V2.md`, avsnitt 5). Den kan eventuelt foreslå bedre navn på skålene.

**Lag mat** er kortmodus med fire tillegg:

- **Din del og ventetiden er skilt.** Kortet gjelder det du gjør. Har steget passiv tid, heter hovedknappen «Start, så videre», og steget legges i et **pågår**-felt øverst med nedtelling og «ferdig når». Når tiden er ute, blir det rødt, piper og vibrerer.
- **«Mens pastaen står»** vises på alle steg som etter planen starter i et annet stegs ventetid, ikke bare prep-steg.
- **«Venter på … , ca. 3 min»** vises når et steg trenger resultatet fra et steg som fortsatt står.
- **Du trenger** viser det som faktisk står foran deg: skålene fra Gjør klart som helles i her (nummer, symboler og innhold), ingredienser som ikke ligger i en skål, og resultater fra tidligere steg («Pastaen, fra steg 5»). Resultater av prep som er gjort i Gjør klart, ligger allerede i en skål og vises ikke to ganger.

I tillegg: listen over alle steg (ingredienser i steget) med symbolet inne i mengdepillen, sveip som gjør det samme som hovedknappen, skjermen holdes våken, og fremgangen lagres på enheten.

**`prep_style` i stegteksten:** i cook- og serve-steg vises klargjøringen i parentes etter ingrediensen («Tilsett 3 fedd hvitløk (finrevet)»). I prep-steg vises den ikke, fordi teksten der beskriver klargjøringen selv. Før dette sto det bare «3 fedd hvitløk» der hvitløken skulle inn finrevet.

**Utstyr** vises med plassholdere etter rolle (koke, forberede, avlastning) til utstyrskatalogen får egne symboler i 7c.

**Ikke testet ennå:** matlaging med prototypen på telefonen. Det er siste del av 7a.


---

### 9.16 Ingrediensbildene bærer sidene, og ingrediensene grupperes (oktober 2026)

**Bildene.** Ingrediensbildene er det som skiller appen fra andre, så de er gjort større på alle tre sidene. Bildene er 512 px med hvit bakgrunn, og maten fyller bare 65–77 % av dem. Før lå de i tillegg i en grå boks med kant, så på en 36 px plass ble ingrediensen rundt 24 px.

- Rammen er borte. Bildet skaleres 1,25 ganger forbi den hvite kanten, og `mix-blend-mode: multiply` gjør det hvite usynlig mot papiret.
- Større plass: handlelisten 36 → 56 px (basisvarer 36), piller i stegteksten 20 → 24, Prep-fliser 44 → 64, Cook: skålbilder 26 → 36 og fliser 40 → 64, elvedeltaet 28/36 → 36/48.
- Forbokstaven (ingrediens uten bilde) beholder boksen.
- Et blekt (avkrysset) element må ha bakgrunn eller tegnes over. `opacity` på en boks uten bakgrunn rundt bildet gjør at det hvite vises igjen.
- Senere: tett beskårne kopier laget av et skript gir lik luft rundt alle bilder. Det skriver til GCS i prod og må godkjennes.

**Grupper.** Ingrediensene grupperes etter kategorien i spiskammeret (`main_category`, `sub_category`), slått sammen til grupper i den rekkefølgen man går i butikken: frukt og grønt (med ferske urter), kjøtt og fisk, meieri og egg, brød, «pantry» (pasta, korn, mel, sukker, nøtter og hermetikk), krydder, sauser, olje og fett, drikke, annet, og til slutt «You probably have» (basisvarene i `mise.STAPLES`). Reglene står i `services/recipe_v2/groups.py`. Handlelisten på Overview vises i disse gruppene.

**Prep er forenklet.** «Take out» og «On the counter» (9.13) er slått sammen til én «Take out» i de samme gruppene, med gruppene side om side. En ingrediens som brukes i flere steg, er én flis med mengdene og stegene («½ tsp + to taste», «step 3, 6»), så salt vises én gang i stedet for tre. Basisvarene er én rad med navn: du har dem, og stegene gir mengdene. Skillet mellom «mål opp når du bruker den» og «står fremme» står ikke lenger på Prep. Cook viser fortsatt per steg hva som skal inn.


**Skålene på Gjør klart (23.10.2026).** En skål viser alltid bare nøkkelinfo: nummeret, et kort navn og ingrediensene med mengde og tilstand. Antall står som et merke på bildet når linjen telles i stykker eller fedd (3× på tre fedd), og tilstanden («finhakket») som en etikett under. Et trykk på skålen åpner resten: hvilket steg den er til, hvorfor den er en skål og forarbeidet per ingrediens. Avkryssingen er nummeret, en egen knapp på 44 px.

**Ingrediensbordet på Gjør klart (23.10.2026).** Alle ingrediensene står i ett rutenett med de samme flisene, og rammen sier hva slags de er: skålene (hel ramme i fasefargen, nummer og avkrysning), «Take out» (stiplet ramme, «step 4» på hver flis, sortert etter kategori uten overskrifter) og «You probably have» (små, grå fliser; mengden står i stegene). Høyrespalten er borte; utstyret står under. Tilstanden kommer fra forarbeidssteget når linjen selv mangler kutt.

**Tilstand og mengde i bilder, trinnvis.** Prep skal vise hvilke ingredienser, hvilke som hører sammen, hvor mye og tilstanden etter forarbeid. Første trinn er det enkle som er gjort: skålen samler, merket viser antall, etiketten og kuttmerket viser tilstanden. Neste trinn, bare hvis det trengs: enhetsbilder for varer der det man kjøper og det man bruker er forskjellig (hvitløk og fedd, urter og kvist), gjentatt for små antall; deretter bilder av tilstanden (ingrediens og kutt, slått sammen til rundt seks synlige tilstander), laget ved behov, med kuttmerket som reserve. Datamodellen har allerede det som trengs (`cut`, `amount`, `unit`).


---

### 9.17 Prep og koking på én side (prøve, 23.10.2026)

Pål lener mot å samle prep og koking i én fane, med ingrediensene og fakta om retten bak knapper, men med et tydelig skille mellom prep og cook. Strukturelt er det enkelt: prep- og cook-steg er samme slags rad (`recipe_step`), og bare `phase` (prep, cook, serve) og planen skiller dem; Gjør klart er utledet fra prep-stegene og ingrediensene.

`/recipe/<id>/make`, bare for admin, med «Flow: Tabs / One page» i admin-brikken (besøkende får fanene). Faner: Overview og Make. Siden:

1. **Get ready** (grønn): ingrediensbordet fra Gjør klart, med måler.
2. **Milepæl:** «All ready? Then the heat can go on.»
3. **Cook** (oransje): kokemodus slik den er, ett steg om gangen med tidtakere, stegliste og hele retten. Prep-steg som planen legger i en ventetid, kommer der de hører hjemme, i grønt. Bunnlinjen vises først når kokingen er på skjermen.
4. **Knapper:** «Ingredients» (listen fra Overview) og «Servings and facts» (porsjoner, plan, fakta, næring) som ark.

Delene deles med Gjør klart og Lag mat (`components/prep_board.html`, `components/cook_flow.html`, `components/dish_info.html`), så de tre sidene ikke glir fra hverandre mens prøven pågår.

**Visningene underveis:** stegene er hovedsaken; tilleggene kommer når de trengs, ikke ved å veksle. Midt i et steg: stegkortet. Mellom steg eller mens noe står: nå/neste med tidtakere (statuslinjen). Når man har mistet tråden: hele retten i et ark, med tidslinje, T-banekart og elvedelta som faner. Stor skjerm: ved siden av.

---

## Vedlegg: parkerte visninger

Disse ble vurdert, men er ikke med i første omgang. Flere av dem blir billige når endringene over er gjort.

| # | Visning | Kort beskrivelse | Hva som skal til |
|---|---|---|---|
| 5 | Komfyrkartet | Komfyren sett ovenfra med hva som står på hver plate og ovn, med nedtelling per plate | `equipment`, `heat`, `temp_c`, parallellitet. Krever mest |
| 8 | Piktogram | IKEA-manual for mat: ikon per handling, nesten uten tekst | `action` (endring 3) |
| 9 | Sansebaserte sjekkpunkter | «Ferdig når: gyllen kant, lysere frestelyd» i stedet for bare tid | `done_when` (endring 3). Inngår i kortmodus |
| 10 | To kokker | Oppgavene fordelt på to svømmebaner med felles møtepunkt | Samme som tidslinjen, med to ressurser i planleggingsalgoritmen |
| 12 | Vekt-modus | Én bolle på tarert vekt, appen viser løpende sum («hell i sukker til 315 g») | `gram_weight` finnes. Trenger `uses` for bollegruppering og et flagg for hva som veies |
| – | Ingrediensrutenett på Overview | Handlelisten som et rutenett av store bilder (rundt 80 px) gruppert etter kategori, som et «flat lay» av alt du trenger. Tydeligst kjennetegn for appen, men dårligere å handle etter: mengdene står ikke på linje og lange navn brekker | Gruppene fra 9.16 finnes. Bare mal og CSS |
| 13 | Klokkeskiven | Hele økta som urskive, prep i ytre ring og cook i indre | `phase` + tid finnes. Mulig i dag, sekvensielt |
| 14 | Zoom-nivåer | Samme oppskrift i flere detaljnivåer, fra én linje til full forklaring | `text_short` (endring 3) og eventuelt `text_detailed`/`why` |
| 15 | Ratio-kortet | Oppskriften som forholdstall, med glidebryter for ønsket resultat | Visningen kan regnes ut fra `gram_weight` i dag. Glidebryteren krever kunnskap om retten |
