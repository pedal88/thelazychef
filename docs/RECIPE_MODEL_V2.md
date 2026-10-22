# Beslutningsnotat: oppskriftsmodell versjon 2

Dato: 14.10.2026, revidert 18.10.2026 (to ganger)
Status: vedtatt
Bakgrunn og begrunnelser: `docs/RECIPE_VISUALIZATIONS.md`, særlig kapittel 9.
Fase 0: `docs/pilot/RECIPE_V2_PILOT.md`.
Prototyper: `docs/prototypes/fem-retter.html` (fem retter, seks visninger), `docs/prototypes/fem-retter-pilot.html` (pilotresultatene) og `docs/prototypes/grill-kreta.html`.

## 1. Beslutning

Vi går fra dagens listemodell (ingredienser og steg som fritekst) til en grafmodell der stegene peker på ingrediensene de bruker og på stegene de bygger på.

**Revisjon 18.10.2026: rent kutt i stedet for gradvis migrering.** De eksisterende oppskriftene har liten verdi, og appen har foreløpig én bruker. Vi migrerer derfor ikke gamle oppskrifter. De relevante genereres på nytt med den nye modellen, og de gamle arkiveres og slettes etterpå. Det fjerner det dyreste kravet i den opprinnelige planen: at gamle felter skulle regnes ut fra nye så dagens visninger virket hele veien. Fase 1 og 2 slås sammen til ett bygg.

Å beholde den gamle modellen med tilpasninger er vurdert og forkastet. Verdien ligger i koblingen mellom steg og ingredienser, og så fort den legges til, er det den nye modellen.

## 2. Rammer for appen

| | Vedtak |
|---|---|
| Brukere | Appen skal bli et offentlig verktøy med brukere. Generering og admin er bare for administrator |
| Språk | Engelsk er førstespråk. Norsk skal støttes senere for det vanlige brukere ser, ikke for generering og admin. Ingenting bygges for norsk nå, men tekster i grensesnittet samles slik at de kan oversettes |
| Tekst-AI | Claude (Anthropic) for oppskriftstekst, strukturering og bildeprompter. Fase 0b valgte Opus 5.5 med effort `low` for både tekst og strukturering |
| Video-AI | Gemini beholdes for å gjøre video om til tekst, fordi Claude ikke tar video |
| Bilde-AI | Googles Gemini-bildemodell erstatter Imagen 4. Den tar referansebilder og kan redigere, og det trengs for stilkonsistens og for komponentbilder som passer til rettbildet. Modell-ID bekreftes mot Googles modelliste når vi bygger |
| Modellnavn | Alle modellnavn står ett sted i koden. De pensjonerte Gemini 2.0-modellene viste hvorfor |

## 3. Hva som er vedtatt i modellen

| | Vedtak |
|---|---|
| Forenkling 1 (revidert etter piloten) | `waits` lagres ikke. `setup` betyr **all klargjøring av utstyr**: forvarm ovnen, kok opp vann, kle eller smør formen. Et steg venter automatisk på setup-steget for samme kokekar. Finnes det flere, velges det med samme `temp_c`. Sjeldne tilfeller som «varm pitaen etter kjøttet» modelleres ikke |
| Forenkling 2 | Maltekst bare for ingredienser (`{i3}`). Ingen referanser til mellomprodukter (`{s2}`) og ingen `output_label`. Stegteksten sier «sausen» i vanlig tekst |
| Forbedring 1 | Generering i to runder: først naturlig tekst, så strukturering til graf med validator i løkke (avsnitt 7) |
| Forbedring 2 | Ingrediensformer og enheter (avsnitt 5) |
| Versjon | `schema_version` og `revision` på oppskriften. Ingen historikk foreløpig |
| Tabeller | `recipe` beholdes, slik at ID-er og URL-er overlever. Barnetabellene byttes ut (avsnitt 5) |
| Språk (21.10.2026) | Én oppskrift er samme oppskrift på alle språk. Graf, mengder, tider og metadata deles; bare teksten (tittel, komponent- og linjenavn, stegene, kokkens notat) har språk. `recipe.language` er språket teksten ble laget på, engelsk som standard, og en versjon arver grunnrettens. Andre språk kommer senere som oversatt tekstlag per språk, nøklet på `local_id`, med originalen som reserve. Ikke egne oppskrifter per språk |
| Ikke vedtatt | Standardverdier for `holds` per handling og tilsyn i passiv tid |

## 4. Avklaringer

1. **`schema_version`** (heltall): 1 = gamle lister, 2 = graf. Visningene velger ut fra den så lenge begge finnes.
2. **`revision`** (heltall) og **`revised_at`** (tidspunkt): øker når innholdet endres (ingredienser, steg, komponenter, mise-elementer, mengder, tekst). Status, bilder og evaluering øker den ikke. Tidligere utgaver lagres ikke. `user_recipe_interaction` får `revision`, satt når brukeren markerer retten som laget.
3. **`phase` lagres.** Validatoren sjekker at steg med varme (`method` er en varmemetode) er `cook`. Regel: varme er cook, siste hånd før spising er serve, alt annet er prep.
4. **Steggranularitet:** ett steg er én handling på ett sted, med ett «ferdig når». Nytt steg ved ny beholder eller ventetid. Regelen står med eksempler i promptet.
5. **Komponenter, ikke underoppskrifter.** `sub_recipe_id` på komponenten kan komme senere.
6. **Komponentdefinisjon (skjerpet etter piloten):** sauser og fyll som lages hver for seg, er egne komponenter selv om de havner inne i retten. «Assembly», «Garnish» og «Main Dish» er ikke komponenter.
7. **`holds_minutes` er valgfri.** Mangler den, er det ingen grense. AI-en skal sette den for ting som forringes: kuttet frukt, salat med dressing, stekt mat, kokt stivelse.
8. **Validatoren avviser og prøver på nytt, maks to ganger.** Deretter lagres oppskriften som utkast med `is_flagged_for_review` og feilene i `validation_errors`. Ingen ugyldig oppskrift publiseres.
9. **Originalteksten lagres** (`source_text`), slik at oppskriften kan struktureres på nytt når skjemaet endres.
10. **Redigering for hånd:** teksten redigeres og strukturering kjøres på nytt. Enkle felter (mengde, tid) kan redigeres direkte, og validatoren kjører ved lagring.
11. **Ingen migrering.** Gamle oppskrifter genereres på nytt fra tittel og kilde (avsnitt 1).
12. **Planstrategi er en brukerinnstilling**, med «rolig» som standard (`RECIPE_VISUALIZATIONS.md` 9.12).
13. **Promptregel for mengder:** `{iN}` er alltid totalmengden. «Fordel {i4} på burgerne», ikke «{i4} på hver burger».
14. **Promptregel for sluttsteg:** mangler kilden et serveringssteg, legges det til et kort «Server»-steg som samler komponentene.
15. **`prep_style` i stegteksten (steg 7a):** `{iN}` rendres med mengde og navn. I cook- og serve-steg legges klargjøringen til i parentes («3 fedd hvitløk (finrevet)»), i prep-steg ikke, fordi teksten der beskriver klargjøringen. Promptet må vite det, så modellen ikke skriver klargjøringen to ganger.
16. **Mise-elementer utledes** fra grafen med faste regler for skål, ta frem og på benken (`RECIPE_VISUALIZATIONS.md` 9.15). AI-en lager dem ikke.

## 5. Modellen

### Oppskrift (`recipe`, beholdes)

| Felt | Nytt | Merknad |
|---|---|---|
| `schema_version` | ja | 1 eller 2 |
| `revision`, `revised_at` | ja | Se avsnitt 4 |
| `source_text` | ja | Teksten fra første runde |
| `source_url`, `source_type` | – | `source_type`: idé, tekst, nettside, video |
| `validation_errors` | ja | JSON, tom når oppskriften er gyldig |
| `chef_note` | ja | Genereres i dag og kastes |
| `yield_text` | ja | For oppskrifter som ikke skaleres per porsjon («én form på 24 cm», «12 boller») |
| `prep_time_mins` | – | Blir utledet (aktiv prep-tid i «rolig»-planen) |
| `component_images`, `social_hooks` | fjernes | Erstattes av `image_filename` på komponenten. `social_hooks` går ut med Media Hub |

### Barnetabeller

Nye tabeller erstatter `recipe_ingredient` og `instruction`: `recipe_component`, `recipe_line`, `recipe_step` og `recipe_step_after` (migrering `ce7d5aeeecf0`, steg 7b). De gamle beholdes bare til de gamle oppskriftene er slettet, og fjernes deretter sammen med koden som leser dem.

**Komponent** (`component`): `id`, `recipe_id`, `local_id` (`c1`), `name`, `sort_order`, `image_filename`.

**Ingredienslinje:**

| Felt | Merknad |
|---|---|
| `local_id` | `i3`, brukes i malteksten |
| `component_id` | Fremmednøkkel, ikke fritekst |
| `ingredient_id` | Pantry-ingrediensen |
| `amount`, `unit` | `amount` er null bare for «etter smak». `unit` må finnes i enhetstabellen |
| `ingredient_form_id` | Formen som brukes (fedd, eggeplomme). Tom betyr hele varen |
| `prep_style` | Klargjøring i oppskriften fra fast liste (hakket, finhakket, revet, presset, romtemperert), med fritekst for nyanser. Hører til linjen, ikke ingrediensen |
| `gram_weight` | Regnes ut fra mengde og enhet med tetthet eller gram per stykk (avsnitt 5, Ingrediensmodellen) |
| `mise_element_id` | Fase 3 |

**Delte linjer:** en ingrediens som brukes på to tidspunkter, står som to linjer (pecorino 60 g og 20 g). Ingredienslisten summerer dem.

**Steg:**

| Felt | Merknad |
|---|---|
| `local_id` | `s3` |
| `component_id` | Fremmednøkkel |
| `phase` | Lagres, valideres mot `method` |
| `short` | Kort navn, maks ca. 4 ord. Brukes i metrokart, tabell og kort |
| `text` | Maltekst med `{iN}`. Ingen tidsord som «mens». Teknikk inne i steget («mens du visper») er greit |
| `uses` | `step_id` på ingredienslinjen. Hver linje brukes av nøyaktig ett steg, så det er en kolonne og ikke en koblingstabell |
| `after` | Koblingstabell steg → steg. Bare der maten går videre |
| `active_minutes`, `passive_minutes` | |
| `holds_minutes` | Valgfri. Null betyr ingen grense |
| `method` | Fra metodekatalogen. Varmemetoder gir cook |
| `equipment` | Liste av ID-er fra utstyrskatalogen. Første element er kokekaret |
| `temp_c`, `mode` | Gjelder kokekaret |
| `setup` | Klargjøring av utstyr, se avsnitt 3 |
| `done_when` | Sansebasert sjekkpunkt |

Rekkefølge (`step_number`, `global_order_index`) lagres ikke. Den utledes fra planen.

Alle koblinger får `ON DELETE CASCADE`, slik at sletting av en oppskrift eller fletting av ingredienser aldri etterlater foreldreløse rader.

### Mise-element (`mise_element`, fase 3)

`id`, `recipe_id`, `local_id`, `name`, `used_in_step_id`. Definisjon: det som står klart når prep er ferdig, og helles i på samme tidspunkt. Alle ingredienslinjer har et mise-element. **Avgjort i steg 7a:** elementene utledes fra grafen, og AI-en lager dem ikke (avklaring 16). Det åpner for å flytte dem fram fra fase 3, siden de ikke koster noen ekstra AI-runde.

### Ingrediensmodellen (revidert 18.10.2026)

Fire ting holdes atskilt: ingrediensen, formen, tilstanden og mengden.

**Ingrediensen** (`ingredient`) er det man kjøper: hvitløk. Navn, kategori, næring per 100 g, bilde, alias og basisvare. Regel: **må handlelisten skille to varer, eller har de ulik næring eller bruk, er de to ingredienser.** Hvitløkspulver, hvitløkspasta og syltet hvitløk er egne ingredienser, ikke former.

**Formen** (`ingredient_form`) er en fysisk utgave av samme vare: hel hvitløk og fedd, helt egg, plomme og hvite, hel sitron, saft og skall. Formen har:
- navn i entall og flertall
- gram per stykk (1 fedd ≈ 5 g)
- forhold til kjøpevaren (1 hvitløk ≈ 10 fedd, 1 egg = 1 plomme + 1 hvite), slik at handlelisten summerer i det man kjøper
- valgfri egen næring per 100 g, fordi plomme og hvite er svært ulike
- eget bilde, med reserve til ingrediensens bilde

**Tilstanden** er to ulike ting:
- **Slik varen kjøpes** (fersk, fryst, hermetisk, tørket, røkt): egen ingrediens etter regelen over, med `base_ingredient_id` til grunnvaren («fryst hakket løk» → «løk»). Koblingen brukes til erstatninger og gruppering senere.
- **Klargjøring i oppskriften** (hakket, revet, romtemperert): `prep_style` på ingredienslinjen. Vises som et lite merke på bildet, ikke som eget bilde.

**Mengden** står på ingredienslinjen som skrevet (`amount`, `unit`), og `gram_weight` regnes ut: vekt direkte, volum × tetthet, antall × gram per stykk for formen. Gram driver næring, skalering og handleliste. Standard måleenhet ligger på formen når den finnes («fedd»), ellers på ingrediensen.

**Allergener og kosthold** (gluten, laktose, melk, egg, nøtter, peanøtter, skalldyr, fisk, soya, sesam, selleri, sennep, sulfitt, lupin, bløtdyr, og vegansk/vegetarisk) lagres per ingrediens. Kostholdstaggene på en oppskrift **utledes fra ingrediensene** i stedet for å gjettes av AI-en. For et offentlig verktøy er det både mer pålitelig og et ansvarsspørsmål. Tallene settes i pantry-ryddingen før nygenereringen, og de som er usikre, merkes for gjennomgang.

### Pantry og kataloger

| | Når | Innhold |
|---|---|---|
| `ingredient.is_staple` | Finnes | Salt, pepper og oljer |
| `ingredient_alias` (ny tabell) | Grunnmur, ferdig | Navn → ingrediens. Leses av matcheren og skrives av flettingen |
| `ingredient.density_g_per_ml` | v2-bygget | For omregning fra volum til gram |
| `ingredient.base_ingredient_id` | v2-bygget | Fra variant til grunnvare |
| Allergener og kosthold | v2-bygget | Per ingrediens, oppskriften utleder sine |
| `unit` (ny tabell) | v2-bygget | Navn i entall og flertall, type (volum, vekt, antall, omtrentlig), ml per enhet |
| `ingredient_form` (ny tabell) | **v2-bygget** (flyttet fra fase 3) | Se Ingrediensmodellen |
| Næringskilde | v2-bygget | Se avsnitt 9 |
| `data/constraints/equipment.json` | v2-bygget | ID, navn, rolle (koke, forberede, avlastning) |
| `data/constraints/methods.json` | v2-bygget | ID, navn, om det er en varmemetode |

**Hvorfor formene flyttes fram:** oppskriftene lages på nytt i steg 8. Hvis formene først kom i fase 3, måtte alle oppskriftene struktureres en gang til for at «2 fedd hvitløk» skulle peke på formen. Mise en place blir værende i fase 3.

### Kjerne og lang hale (vedtatt 19.10.2026)

Pantryet skal dekke det man trenger til de fleste retter, uten å bøye oppskriftene etter det. Den gamle genereringen tvang AI-en til å bruke pantrynavn, og byttet derfor ut ingredienser (rød currypasta ble «chilli paste»). v2 bytter aldri. Ingredienser deles i to nivåer (`ingredient.tier`):

- **Kjerne:** en ingrediens en hjemmekokk kjøper i en vanlig butikk, som brukes i mange retter eller er nødvendig for et vanlig kjøkken (indisk, thai, italiensk, meksikansk, nordisk og så videre). Kjernen kurateres fullt: symbol, næring, tetthet og allergener.
  - Én oppføring per vare handlelisten må skille: fersk og malt ingefær er to, tre slags cherrytomater er én.
  - Kutt på det nivået oppskrifter faktisk bruker: «beef sirloin» er kjerne, «reindeer leg roast» er lang hale.
  - Drikke bare når det lages mat med det: vin, øl og kokosmelk er med, brus er ikke.
- **Lang hale:** ingredienser som finnes fordi en oppskrift trenger dem. De beholdes og får symbol, men vises ikke som standard i pantry-oversikten og hjelpen til handling.

**Ikke en matlagingsingrediens** (brus, juice til å drikke) settes som inaktiv, ikke slettet. Rødvin og enkelte øltyper kan bli en del av appen senere.

**Nye ingredienser (variant C2):** når en oppskrift trenger noe som ikke finnes, foreslår AI-en en ny ingrediens med kategori, grunnvare (`base_ingredient_id`, «thai basil» → «basil») og næring. Koden sjekker mot navn, alias og nære navn. Er den klart ny, legges den til som lang hale og får symbol. Kan den være et duplikat eller en variant, går den i en godkjenningskø. Admin får jevnlig en kort liste over det som er lagt til, og kan flette eller flytte til kjernen. Grunnvaren gir erstatninger og gruppering senere.

**Første gjennomgang:** alle aktive ingredienser sorteres av Claude mot definisjonen over (kjerne, lang hale, ikke en matlagingsingrediens, duplikat av), og Claude foreslår kjerneingredienser som mangler per kjøkken. Admin går gjennom forslagene i et ark før noe endres (`scripts/pantry_review.py`). Duplikater flettes ved at navnet blir alias for vinneren og taperen blir inaktiv, så alt kan reverseres.

Gjennomført 19.10.2026 (kjøring `pantry-20261019-1349`, migrering `0d4f84fc82e7`): 278 kjerne og 313 lang hale, 40 inaktive som ikke er matlaging, 23 duplikater flettet, 41 nye kjerneingredienser og 28 aliaser. Fire rettelser i Claudes forslag: «almond butter» og «nut butters (e.g. almond)» pekte på hverandre (almond butter beholdes), «paprika» (grønnsaken) gir ikke alias til paprika, fordi «paprika» i engelske oppskrifter er krydderet (aliaset peker på ground paprika), «filet» gir ikke alias til laksefilet, og «cumin» blir alias for ground cumin i stedet for en ny ingrediens. De nye fikk næringsdata (`scripts/ingredient_nutrition.py`, migrering `9482c2b9d672`, USDA der den finnes, ellers estimat fra produktetiketter) og symboler (kjøring `symbols-20261019-1411`, migrering `edb2c0f81d8a`) samme dag.

### Basisvarer og grunnlager (vedtatt 22.10.2026)

`tier` er en stige med fire trinn, der hvert trinn er en delmengde av det neste: **staple** ⊂ **foundation** ⊂ **core** ⊂ **long_tail**.

- **Nivå 1, basisvarer (`staple`):** det vi antar at alle brukere alltid har: vann, salt, sort pepper, nøytral olje, olivenolje, sukker og hvetemel (migrering `a3d7f2c9e1b6`). Oppskriftssidene viser dem under «You probably have», ikke på handlelisten, og Gjør klart viser dem som én rad med navn. `is_staple` er den gamle markeringen som v1-genereringen leser; v2 bruker `tier`.
- **Nivå 2, grunnlager (`foundation`):** et grunnlag på tvers av kategorier som gjør det mulig å lage svært mange retter, og som oppskriftene gjenbruker. Størrelsen er ikke bestemt (40–120 varer). Prinsippene:
  - **Standardvalg, ikke regel.** Der retten gir et reelt valg (hvilken del av kyllingen, hvilken løk, hvilken ost), bruker genereringen varen i grunnlageret: kyllingfilet er standard for kylling. Ingrediensen som gjør retten til det den er, byttes aldri (lårfilet i en langtidskokt gryte, fiskesaus i pad thai). Avvik fra standarden får en kort begrunnelse som admin ser. Dette holder vedtaket over om at pantryet ikke skal bøye oppskriftene.
  - **Standardvarianten** er den av variantene til en grunnvare (`base_ingredient_id`) som ligger i grunnlageret. Det trengs ikke noe eget felt.
  - **Nøkkelsmaker for de største kjøkkenene** hører hjemme i grunnlageret (for eksempel garam masala, fiskesaus, soyasaus), selv om de ikke brukes på tvers.
  - **«+N ekstra»** (varer utenfor grunnlageret og basisvarene) vises per oppskrift som et tall, ikke som en grense.
  - Bygget slik at det kan bli brukerens eget skap senere: grunnlageret er da et forslag brukeren krysser av i.

### Gjenstående pantry-feil

Funnet under gjennomgangen av ingredienssymbolene 18.10.2026. De ryddes i v2-bygget, før nygenereringen, med fletting (linjene flyttes, navnet blir alias) og nye navn:

- **Duplikater:**
  - `mozzarella` (188) og `mozzarella cheese` (612).
  - Tahini: `tahini` (509), `seed butters (tahini)` (394) og `sesame butter` (209).
  - Peanøttsmør: `peanut butter` (516) og `nut butters (peanut` (393).
  - Mandelsmør: `almond butter` (517) og `nut butters (e.g. almond)` (210).
- **Navn kuttet i databasen:** `nut butters (peanut` (393) og `herbal tea (e.g. chamomile` (595).
- **Uklart navn:** `filet` (56, fisk, underkategori «salmon») kan ikke stå alene. Trolig laksefilet, som finnes fra før som `salmon fillet` (656).
- **Kanel:** `cinnamon` (361, under «flavorings» i bakevarer) ved siden av `cinnamon sticks` (266) og `ground cinnamon` (271). Bestem om den generelle skal flettes inn i en av dem.
- **Smør i to kategorier:** `butter` (371) ligger under fett og oljer, mens `salted butter` og `unsalted butter` ligger under meieri. Smørvariantene hører sammen, og blir varianter av grunnvaren `butter` med `base_ingredient_id`.
- **Produktbeskrivelser i `prep_style`:** «hermetiske tomater, hakkede» og «, knuste» beskriver produktet, ikke klargjøring. De skal være egne varer i pantryet, ellers regnes de som forarbeid i Gjør klart.
- **Varer som mangler:** ni av ingrediensene i de fem prototyperettene finnes ikke i pantryet: fersk ingefær, garam masala, tomatpuré, oksebuljong, mørk sjokolade, vaniljesukker, basmatiris, dijonsennep og rødvinseddik. Pantryet må fylles før nygenereringen.
- **Underkategorier som samler ulike varer:** «flavorings» blander ekstrakter med krydder, og honning ligger under «sugar». Symbolene er løst med egen form per ingrediens, men kategoriene bør ryddes når allergenene og grunnvarene settes.

### Utledes, lagres ikke

Plan og rekkefølge per strategi, økter og «mens …»-formuleringer, aktiv og total tid, ingrediensliste for hele retten, inndelingen av mise-elementer i skål, ta frem og på benken, komponenten til et mise-element, kolonnene i tabellmetoden og ventetid på utstyr.

## 6. Validering

Kjøres før lagring, i strukturerings-runden og ved redigering:

1. Alle `local_id` er unike innenfor sin type.
2. Alle referanser finnes (`uses`, `after`, `component_id`, `{iN}` i teksten).
3. Hver `{iN}` i teksten står i stegets `uses`.
4. Hver ingredienslinje brukes av nøyaktig ett steg.
5. Ingen sykler. Nøyaktig ett sluttsteg.
6. Steg med varmemetode har `phase = cook`.
7. `equipment`, `method` og `unit` finnes i katalogene.
8. `amount` er større enn 0, eller null med «etter smak».
9. `ingredient_form_id` hører til linjens ingrediens, og enheten kan regnes om til gram (tetthet eller gram per stykk finnes).
10. Fase 3: hver linje har et mise-element, hvert mise-element brukes av et steg som finnes, og linjene når det steget gjennom prep-stegene.

Advarsler (lagres, men flagges):
- `holds_minutes` overskrides i «rolig»-planen.
- Stegteksten inneholder tidsord som «mens» og «i mellomtiden».
- **Ny etter piloten:** et steg med `temp_c` på ovn eller airfryer uten et setup-steg med samme utstyr og temperatur.

## 7. Generering

### Kilder

New Recipe har **ett input-felt** som tar imot idé, innlimt tekst eller lenke. Appen avgjør selv hvilken adapter som brukes:

| Input | Adapter | Leverer |
|---|---|---|
| TikTok-, Instagram- eller YouTube-lenke | Video: laster ned, henter bildetekst og miniatyrbilde, Gemini gjør video om til tekst | Kildetekst og miniatyrbilde |
| Annen lenke | Nettside: skraper siden | Kildetekst og URL |
| Tekst | Ingen | Idé eller innlimt oppskrift |

Nedlasting fra TikTok og Instagram er skjør og endres når plattformene endrer seg. Den holdes derfor isolert i én adapter. TikTok Sidecar og Bulk Generate fjernes. Nygenerering i bulk gjøres med skript.

### To runder

1. **Runde 1, tekst:** Claude skriver eller normaliserer oppskriften som naturlig tekst med ingredienser og fremgangsmåte. Lagres i `source_text`.
2. **Runde 2, strukturering:** Claude gjør teksten om til modellen over med strukturert output mot skjemaet, med pantry-treff for ingrediensene.
3. **Validering:** feiler den, sendes feilmeldingene tilbake sammen med forrige svar. Maks to nye forsøk.
4. **Lagring:** gyldig gir `schema_version = 2`. Ugyldig etter tre forsøk gir utkast med flagg og `validation_errors`.

### Bakgrunnsjobb

Strukturering tar rundt 90 sekunder (median i piloten) og kan ikke gå i én HTTP-forespørsel. **Cloud Tasks** brukes: New Recipe oppretter oppskriften som `pending` og legger én oppgave i en kø, og køen kaller et internt endepunkt i appen som kjører rundene. Brukeren ser en statusside.

- **Hvorfor Cloud Tasks:** én oppgave per oppskrift, innebygde nye forsøk, og køen begrenser hvor mange som kjører samtidig, slik at vi holder oss innenfor API-grensene. Nygenerering av mange oppskrifter er bare mange oppgaver i samme kø.
- **Forkastet: Cloud Run Jobs.** Laget for batcher. Oppstart per kjøring og parametre via overstyringer passer dårlig for én oppskrift om gangen.
- **Forkastet: tråder i appen.** Cloud Run kan stoppe instansen eller strupe CPU når svaret er sendt, så jobben kan dø halvveis. Media Hub gjør dette i dag.
- Tidsavbruddet på Cloud Run-tjenesten må økes for det interne endepunktet.

## 8. Prompter og prompt-lab

Promptene er filer i repoet (Jinja), redigeres i Claude Code og versjoneres i git. Prompt Studio fjernes.

- **Lag:** felles basis → kategori → det unike per element. For ingrediensbilder betyr det felles stil, et lag per kategori (krydder, sauser, kjøtt) og en kort beskrivelse per ingrediens fra pantryet («hele stjerneanis, ikke malt»). Hvert lag er én fil, og malene arver fra hverandre.
- **Varianter:** hvert lag kan ha varianter (`a`, `b`, `c`). Et skript kjører valgte varianter mot et lite utvalg og lager et kontaktark: én rad per element og én kolonne per variant.
- **Logg over kjøringer:** hver kjøring lagres med promptversjon (git-hash), modell, input, output og eventuelle poeng. Bilder fra kjøringene lagres privat, ikke i repoet, siden repoet er offentlig.
- **Evaluering, senere:** manuelt valg eller poeng i kontaktarket først, deretter automatisk vurdering med Claude mot en rubrikk (gjenkjennelig, riktig ingrediens, følger stilen). For oppskrifter er målene validatoren og en rubrikk på testsettet. Resultatene kan brukes til å foreslå endringer i promptene.

## 9. Næring

Tallene per 100 g kommer i dag fra Edamam, med AI-anslag der Edamam ikke fant ingrediensen (`scripts/backfill_nutrition_full.py`). `ingredient.data_source` sier hvilken. De trenger ikke være helt riktige fra start, men modellen skal gjøre det mulig å legge inn riktige tall:

- `data_source` beholdes, og vi legger til en markering for verifiserte tall som overstyrer kilden.
- Enhetstabell og tetthet kommer i v2-bygget, fordi gram trengs for næring og skalering.
- Én næringsberegning erstatter de to som finnes i dag.
- Næring vises som omtrentlig, og bare når alle linjer kan regnes om til gram.

## 10. Bilder og symboler

- **Ingredienssymboler er illustrasjoner,** med tydelig silhuett som kan kjennes igjen i liten størrelse, fast vinkel og lys, felles palett og ren hvit bakgrunn.
- **Navnet vises sammen med symbolet** i oppskriftene (overlegg eller etikett). Bildet trenger derfor ikke skille alle varianter (risedikk fra hvitvinseddik) alene, og navnet kan oversettes og brukes som alt-tekst. Selve bildet inneholder aldri tekst.
- **Stilen fra prompt-laben** (runde 1–5, 18.10.2026): `gemini-2.5-flash-image`, «vector_textured», felles regler (én ingrediens, ingen rekvisitter, ren hvit bakgrunn, ingen tekst) og en regel per underkategori for hvordan varen vises (flaske, glass, papirpose, krukke eller hel vare). Enkeltingredienser som ikke passer kategorien sin, får egen form (`image_form`), og notater fra gjennomgangen ligger i `image_notes`. Valget står i `[final]` i oppgaven, og appen, admin og batch-skriptet bygger samme prompt.
- **Hele pantryet har symboler** fra 18.10.2026: 654 bilder i én kjøring, to runder gjennomgang og omtrent 28 USD. Flyten (lag, gjennomgå, lag på nytt, rull ut) er beskrevet i `docs/PROMPT_LAB.md`. Mangler en ingrediens bilde, vises forbokstaven i kategorifargen (`RECIPE_VISUALIZATIONS.md` 9.13).
- **Symboler for innhold** (kosthold, kjøkken, utstyr, metoder) lages i samme stil som ingrediensene. **Kontrollikoner** (meny, lukk, del) kommer fra ett ferdig ikonbibliotek.
- **Retter og komponenter:** rettbildet lages når oppskriften er validert. Komponentbildene lages med rettbildet som referanse (`RECIPE_VISUALIZATIONS.md` 9.7).

## 11. Plan

| # | Steg | Innhold |
|---|---|---|
| 0 | Fase 0 med Gemini | **Gjennomført.** 20/20 besto validatoren etter nye forsøk, og 19/20 i første forsøk, mot kravet om 80 %. Kostnad ca. 0,044 USD og median 86 sekunder per oppskrift. Ingen grunn til å forenkle modellen. Se pilotrapporten |
| 1 | Kutt | **Ferdig 18.10.2026** (PR #39–#42). Fjern Media Hub, TikTok Sidecar (adapterkoden beholdes), Photo Studio, Prompt Studio, Style Center, Concept Visuals, Recipe Card Lab, Bulk Generate, siden for manglende ingredienser, kokketipsene på oppskriftssiden, automatisk rettbilde, `social_hooks`, tabellen for innlegg til sosiale medier, videofilene i `static/` og død kode. Engangsskript arkiveres |
| 2 | Grunnmur | **Ferdig 18.10.2026** (PR #43–#48): Migreringskjede som stemmer med modellene, cascade ved sletting, fletting som flytter linjer i stedet for å slette dem, én AI-modul med modellnavn, alias-tabell, og bare publisert innhold på offentlige endepunkter |
| 3 | Pantry-rydding | **Ferdig 18.10.2026** (PR #49, #50): 27 flettet, 19 nye navn, 23 aktivert, alle navn med små bokstaver, og fuzzy-matching som krever samme ord. Formene, tettheten, allergenene og koblingen til grunnvaren fylles inn i v2-bygget |
| 4 | Prompt-lab | **Ferdig 18.10.2026** (PR #51, #53, #54). Avsnitt 8 og `docs/PROMPT_LAB.md` |
| 5 | Fase 0b med Claude | **Gjennomført 19.10.2026** (PR #61). Opus 5.5 med effort `low` for runde 1 og 2: 23 av 24 gyldige i første forsøk, 29 sekunder og ca. 0,07 USD per strukturering, og alltid pantry-ID. Sonnet trengte flere nye forsøk, Gemini er tre ganger tregere. Ni promptendringer til bygget. Se `docs/pilot/RECIPE_V2_PILOT_0B.md` |
| 6 | Stil på ingredienssymboler | **Ferdig 18.10.2026** (PR #57–#59). Stil satt etter fem lab-runder, 654 symboler laget, gjennomgått og rullet ut med en datamigrering som kan rulles tilbake. Avsnitt 10 |
| 7a | Mobil og stor skjerm | **Nesten ferdig 19.10.2026:** telefonflyten er satt etter tre runder (`docs/prototypes/telefon.html`, `RECIPE_VISUALIZATIONS.md` 9.15). Gjenstår: lage mat med den på telefonen. Før bygget, i prototypen. Hvilke visninger som finnes på telefon og på stor skjerm, hvordan de fungerer i en smal skjerm, og hvordan man går mellom stegene mens man lager mat. Telefonen er førstevalget, stor skjerm brukes til planlegging og oversikt. Avsnitt 13 |
| 7b | v2-bygget, tynn skive | Én oppskrift hele veien i produksjon: input-feltet, begge rundene som bakgrunnsjobb, de nye tabellene og én visning på oppskriftssiden, bygget på design-tokens med dagens uttrykk. Finner integrasjonsproblemene (Cloud Tasks, planleggeren i Python, databasemodellen) mens de er billige |
| 7c | v2-bygget, i bredden | Gjenstående pantry-feil (avsnitt 5), resten av tabellene (former, enheter, tetthet, allergener og grunnvare), alle kildeadapterne, resten av visningene, næring og redigering |
| 7d | Helhetlig uttrykk | Etter den tynne skiven og før steg 9, gjerne parallelt med 7c og 8: palett, typografi, avstander, symboler, logo og merkevare, og en stilguide-side som viser tokens og komponenter rett fra koden. Gjøres med ekte oppskrifter foran seg. Avsnitt 13 |
| 8 | Nygenerering | De relevante oppskriftene lages på nytt. De gamle arkiveres, og gamle tabeller og kode slettes når resultatet er godkjent |
| 9 | Bilder av retter og komponenter | Avsnitt 10 |
| 10 | Fase 3 | Mise en place |

## 12. Senere

Nevnt så de ikke glemmes, men ikke del av planen over:

- **Kostnadstak og varsler** for AI hos Anthropic og Google. Stoppet på forhåndsbetalt kreditt 17.10.2026 viser at det trengs.
- **Edamam-nøklene:** to Edamam-apper har hatt nøklene sine hardkodet i det offentlige repoet siden februar 2026 (fjernet fra koden i PR #38). Abonnementet er avsluttet, men appene må slettes eller nøklene byttes i Edamam-dashbordet. Det må også bestemmes hvor næringstall skal hentes fra framover (avsnitt 9).
- **Innholds-API for sosiale medier:** lese-API med token for publisert innhold med `updated_since`, bilder med stabile URL-er i faste formater (original, 1:1, 4:5, 9:16) med alt-tekst og AI-merking, og varsel ved publisering (webhook eller JSON-feed).
- **Ressurser, samlinger og kokker som filer** i repoet som synkes til databasen, redigert i Claude Code.
- **Raskere sider, om det trengs igjen** (målt 21.10.2026). Etter at sidene fikk få spørringer og mellomlager (PR #103) svarer `/recipes` på ca. 0,6 s og en oppskrift på ca. 1,2 s, mot 6 og 3–4,6 s før. Det som står igjen er mest databasen i en annen region. To tiltak, i denne rekkefølgen hvis det føles tregt igjen:
  1. **Varm instans:** `min-instances=1` på Cloud Run, eventuelt databasen opp fra db-f1-micro til db-g1-small. Fjerner kaldstart etter at appen har stått ubrukt. Ca. 10–15 USD/mnd (begge: 20–35). En konfigurasjonsendring.
  2. **Samme region for app og database:** Cloud Run står i europe-west1 (Belgia), Cloud SQL i europe-north2 (Stockholm), så hver spørring krysser landegrensen. Å flytte appen krever trolig lastbalanserer (domenekoblingen støttes ikke i europe-north2, ca. 18 USD/mnd); å flytte databasen (replika som forfremmes) gir litt nedetid. Må undersøkes før valg.
- **Norsk** for vanlige brukere: oversatt tekstlag per oppskrift (avsnitt 3, Språk), norske navn i pantryet til handlelista, og grensesnittet (Flask-Babel).
- Erstatninger (`RECIPE_VISUALIZATIONS.md` 9.5), økter og forkant ved lang ventetid (9.11), tilsyn i passiv tid, historikk for revisjoner og underoppskrifter.

## 13. Utseende: struktur tidlig, stil sent

Endringer i hvordan appen ser ut koster ulikt, og det bestemmer rekkefølgen (vedtatt 19.10.2026):

1. **Mobil og stor skjerm er struktur** (steg 7a): hvilke visninger som finnes, hva som får plass, og hvordan man navigerer. Det er dyrt å endre når visningene er bygget, og avgjøres derfor i prototypen før bygget. Avgjort: telefonen er for å lage maten (oversikt, gjør klart, lag mat), stor skjerm for å forstå og planlegge (i tillegg tidslinjen, metrokartet og tabellmetoden). Se `RECIPE_VISUALIZATIONS.md` 9.15.
2. **Design-tokens fra første linje** (steg 7b): farger, fonter og avstander samles på ett sted i stedet for å spres i koden. Da blir stil billig å endre senere.
3. **Helhetlig uttrykk** (steg 7d) gjøres med ekte innhold foran seg og må være på plass før bildene av retter og komponenter (steg 9), fordi stilen på dem skal passe paletten. Ingredienssymbolene kan lages på nytt for rundt 30 USD hvis uttrykket krever det.
4. **Finjustering** av farger, luft og tetthet gjøres fortløpende fra visningene viser ekte oppskrifter, i 7c og 8. Det er bortkastet å pusse før tokens finnes.
