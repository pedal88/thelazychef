# Beslutningsnotat: oppskriftsmodell versjon 2

Dato: 14.10.2026
Status: vedtatt
Bakgrunn og begrunnelser: `docs/RECIPE_VISUALIZATIONS.md`, særlig kapittel 9.
Prototyper: `docs/prototypes/fem-retter.html` (fem retter, seks visninger) og `docs/prototypes/grill-kreta.html`.

## 1. Beslutning

Vi migrerer fra dagens listemodell (ingredienser og steg som fritekst) til en grafmodell der stegene peker på ingrediensene de bruker og på stegene de bygger på. Migreringen gjøres gradvis:

- Nye tabeller og kolonner kommer **i tillegg til** de gamle. De gamle feltene regnes ut fra den nye modellen, så dagens grensesnitt virker hele veien.
- Før noe bygges, testes det om AI-en klarer å lage modellen (fase 0).
- Oppskrifter som ikke klarer migreringen, blir på versjon 1 og vises med den enkle visningen.

Å beholde den gamle modellen med tilpasninger er vurdert og forkastet. Verdien ligger i koblingen mellom steg og ingredienser, og så fort den legges til, er det den nye modellen.

## 2. Hva som er vedtatt

| | Vedtak |
|---|---|
| Forenkling 1 | `waits` lagres ikke. Ventetid på varmt utstyr utledes: et steg venter automatisk på oppvarmingssteget (`setup`) for det samme kokekaret. Sjeldne tilfeller som «varm pitaen etter kjøttet» modelleres ikke |
| Forenkling 2 | Maltekst bare for ingredienser (`{i3}`). Ingen referanser til mellomprodukter (`{s2}`) og ingen `output_label`. Stegteksten sier «sausen» i vanlig tekst |
| Forbedring 1 | Generering i to runder: først naturlig tekst, så strukturering til graf med validator i løkke (avsnitt 6) |
| Forbedring 2 | Ingrediensformer og enheter (avsnitt 4) |
| Versjon | `schema_version` og `revision` på oppskriften. Ingen historikk foreløpig |
| Ikke vedtatt | Standardverdier for `holds` per handling (forenkling 3) og tilsyn i passiv tid (forbedring 3) |

## 3. Avklaringer

1. **`schema_version`** (heltall): 1 = dagens lister, 2 = graf. Visningene velger ut fra den.
2. **`revision`** (heltall) og **`revised_at`** (tidspunkt): øker når innholdet endres (ingredienser, steg, komponenter, mise-elementer, mengder, tekst). Status, bilder og evaluering øker den ikke. Tidligere utgaver lagres ikke. `user_recipe_interaction` får `revision`, satt når brukeren markerer retten som laget.
3. **`phase` lagres.** Validatoren sjekker at steg med varme (`method` er en varmemetode) er `cook`. Regel: varme er cook, siste hånd før spising er serve, alt annet er prep.
4. **Steggranularitet:** ett steg er én handling på ett sted, med ett «ferdig når». Nytt steg ved ny beholder eller ventetid. Regelen står med eksempler i promptet.
5. **Komponenter, ikke underoppskrifter**, i versjon 2. `sub_recipe_id` på komponenten kan komme senere.
6. **`holds_minutes` er valgfri.** Mangler den, er det ingen grense. AI-en skal sette den for ting som forringes: kuttet frukt, salat med dressing, stekt mat, kokt stivelse.
7. **Validatoren avviser og prøver på nytt, maks to ganger.** Deretter lagres oppskriften som utkast med `is_flagged_for_review` og feilene i `validation_errors`. Ingen ugyldig oppskrift publiseres.
8. **Rekkefølge:** enhetstabell og tetthet i fase 1, ingrediensformer i fase 3 sammen med mise-elementer.
9. **Originalteksten lagres** (`source_text`), slik at oppskriften kan struktureres på nytt når skjemaet endres.
10. **Redigering for hånd:** teksten redigeres og strukturering kjøres på nytt. Enkle felter (mengde, tid) kan redigeres direkte, og validatoren kjører ved lagring.
11. **Migrering:** godkjente oppskrifter migreres med strukturerings-runden. Utkast genereres heller på nytt.
12. **Planstrategi er en brukerinnstilling**, med «rolig» som standard (`RECIPE_VISUALIZATIONS.md` 9.12).

## 4. Modellen

### Oppskrift (`recipe`)

| Felt | Nytt | Merknad |
|---|---|---|
| `schema_version` | ja | 1 eller 2 |
| `revision`, `revised_at` | ja | Se avsnitt 3 |
| `source_text` | ja | Teksten fra første runde |
| `validation_errors` | ja | JSON, tom når oppskriften er gyldig |
| `chef_note` | ja | Genereres i dag og kastes |
| `prep_time_mins` | – | Blir utledet (aktiv prep-tid i «rolig»-planen) |
| `component_images` | – | Erstattes av `image_filename` på komponenten |

### Komponent (`component`, ny)

`id`, `recipe_id`, `local_id` (`c1`), `name`, `sort_order`, `image_filename`.

### Ingredienslinje (`recipe_ingredient`)

| Felt | Nytt | Merknad |
|---|---|---|
| `local_id` | ja | `i3`, brukes i malteksten |
| `component_id` | ja | Erstatter fritekst-`component`, som beholdes utledet |
| `mise_element_id` | fase 3 | Hver linje har et mise-element |
| `ingredient_form_id` | fase 3 | Hel hvitløk eller fedd, egg eller eggeplomme |
| `unit` | – | Må finnes i enhetstabellen |
| `amount`, `prep_style`, `gram_weight` | – | Som i dag. `amount` er null bare for «etter smak» |

**Delte linjer:** en ingrediens som brukes på to tidspunkter, står som to linjer (pecorino 60 g og 20 g). Ingredienslisten summerer dem. Det finnes ingen andel per bruk.

### Steg (`instruction`)

| Felt | Nytt | Merknad |
|---|---|---|
| `local_id` | ja | `s3` |
| `component_id` | ja | Erstatter fritekst-`component`, som beholdes utledet |
| `phase` | – | Lagres, valideres mot `method` |
| `short` | ja | Kort navn, maks ca. 4 ord. Brukes i metrokart, tabell og kort |
| `text` | endret | Maltekst med `{iN}`. Ingen tidsord som «mens». Teknikk inne i steget («mens du visper») er greit |
| `uses` | ja | Koblingstabell `instruction_ingredient(instruction_id, recipe_ingredient_id)` |
| `after` | ja | Koblingstabell `instruction_dependency(instruction_id, depends_on_id)`. Bare der maten går videre |
| `active_minutes`, `passive_minutes` | ja | Erstatter `estimated_minutes`, som beholdes som summen |
| `holds_minutes` | ja | Valgfri. Null betyr ingen grense |
| `method` | ja | Fast liste. Varmemetoder gir cook |
| `equipment` | ja | Liste av ID-er fra katalogen. Første element er kokekaret |
| `temp_c`, `mode` | ja | Gjelder kokekaret |
| `setup` | ja | Oppvarming av utstyr (forvarm ovn, tenn grill, kok opp vann). Andre steg på samme kokekar venter automatisk på det |
| `done_when` | ja | Sansebasert sjekkpunkt |
| `step_number`, `global_order_index` | – | Beholdes, men blir utledet fra «rolig»-planen |

### Mise-element (`mise_element`, ny i fase 3)

`id`, `recipe_id`, `local_id`, `name`, `used_in_step_id`. Definisjon: det som står klart når prep er ferdig, og helles i på samme tidspunkt. Alle ingredienslinjer har et mise-element.

### Pantry og kataloger

| | Fase | Innhold |
|---|---|---|
| `ingredient.is_staple` | 1 | Salt, pepper og oljer |
| `ingredient.density_g_per_ml` | 1 | For omregning fra volum til gram |
| `unit` (ny tabell) | 1 | Navn i entall og flertall, type (volum, vekt, antall, omtrentlig), ml per enhet |
| `data/constraints/equipment.json` | 1 | ID, navn, rolle (koke, forberede, avlastning) |
| `data/constraints/methods.json` | 1 | ID, navn, om det er en varmemetode |
| `ingredient_form` (ny tabell) | 3 | Ingrediens, navn i entall og flertall, gram per stykk, forhold til kjøpevaren (1 egg = 1 plomme + 1 hvite), bilde |

### Utledes, lagres ikke

Plan og rekkefølge per strategi, økter og «mens …»-formuleringer, aktiv og total tid, ingrediensliste for hele retten, inndelingen av mise-elementer i skål, ta frem og på benken, komponenten til et mise-element, kolonnene i tabellmetoden og ventetid på varmt utstyr.

## 5. Validering

Kjøres før lagring, i strukturerings-runden og ved redigering:

1. Alle `local_id` er unike innenfor sin type.
2. Alle referanser finnes (`uses`, `after`, `component_id`, `{iN}` i teksten).
3. Hver `{iN}` i teksten står i stegets `uses`.
4. Hver ingredienslinje brukes av nøyaktig ett steg.
5. Ingen sykler. Nøyaktig ett sluttsteg.
6. Steg med varmemetode har `phase = cook`.
7. `equipment`, `method` og `unit` finnes i katalogene.
8. `amount` er større enn 0, eller null med «etter smak».
9. Fase 3: hver linje har et mise-element, hvert mise-element brukes av et steg som finnes, og linjene når det steget gjennom prep-stegene.

Advarsler (lagres, men flagges): `holds_minutes` overskrides i «rolig»-planen, eller stegteksten inneholder tidsord som «mens» og «i mellomtiden».

## 6. Generering i to runder

1. **Runde 1, tekst:** AI-en skriver oppskriften som naturlig tekst med ingredienser og fremgangsmåte, slik den gjør godt i dag. Lagres i `source_text`.
2. **Runde 2, strukturering:** et eget kall gjør teksten om til modellen over, med pantry-treff for ingrediensene.
3. **Validering:** feiler den, sendes feilmeldingene tilbake sammen med forrige svar. Maks to nye forsøk.
4. **Lagring:** gyldig gir `schema_version = 2`. Ugyldig etter tre forsøk gir utkast med flagg og `validation_errors`.

Runde 2 brukes også til å migrere eksisterende oppskrifter. Da er input dagens ingredienslinjer og steg.

## 7. Faser

**Fase 0, test (før noe bygges i databasen).** Strukturerings-runden kjøres som et frittstående skript på de fem rettene fra prototypen og 15 godkjente oppskrifter fra databasen.
- Krav: minst 80 prosent består validatoren etter nye forsøk.
- Mål også kostnad og ventetid per oppskrift, og hvilke regler som feiler oftest.
- Klares ikke kravet, forenkles modellen før fase 2.

**Fase 1, felter uten graf.**
- `schema_version`, `revision`, `revised_at`, `source_text`, `validation_errors`, `chef_note`.
- På steget: `short`, aktiv og passiv tid, `holds_minutes`, `method`, `equipment`, `temp_c`, `mode`, `setup`, `done_when`.
- Enhetstabell, tetthet, `is_staple`, utstyrs- og metodekatalog.
- Gir kortmodus med «ferdig når», riktig utstyr og bedre tidsangivelser med en gang.

**Fase 2, grafen.**
- `local_id`, komponenttabell, `uses`, `after`, maltekst.
- Validator og generering i to runder.
- Planlegger med tre strategier og brukerinnstilling, «rolig» som standard.
- Migrering av godkjente oppskrifter.
- Gir tidslinje, metrokart, tabellmetoden og ingredienser i steget.

**Fase 3, mise en place og former.**
- Mise-elementer, ingrediensformer, brettet med skål, ta frem og på benken.

I hver fase regnes de gamle feltene ut fra de nye, så eksisterende visninger fungerer.

## 8. Utenfor scope

Nevnt så de ikke glemmes, men ikke del av denne migreringen:

- Erstatninger (`RECIPE_VISUALIZATIONS.md` 9.5)
- Økter og forkant ved lang ventetid (9.11)
- Tilsyn i passiv tid («snu halvveis»)
- Bildeflyt for retter og komponenter (9.7) og ingrediensbilder (9.13)
- Historikk for revisjoner
- Underoppskrifter
- Visningene selv, utover at de skal kunne tegnes fra modellen
