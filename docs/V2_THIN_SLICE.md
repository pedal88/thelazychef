# Plan: tynn skive av v2-bygget (steg 7b)

Dato: 19.10.2026. Status: forslag til godkjenning.
Bakgrunn: `docs/RECIPE_MODEL_V2.md` (modellen og planen), `docs/pilot/RECIPE_V2_PILOT_0B.md` (modellvalg), `docs/RECIPE_VISUALIZATIONS.md` 9.15 (telefonflyten).

## Målet

**Én oppskrift hele veien i produksjon:** admin skriver en idé eller limer inn en oppskrift, appen lager den med Claude i bakgrunnen, lagrer den i de nye tabellene og viser den på oppskriftssiden på telefonen. Skiven skal finne integrasjonsproblemene mens de er billige: bakgrunnsjobben, Claude i produksjon, planleggeren i Python og databasemodellen.

**Ferdig når:**

1. Admin lager en oppskrift fra en idé på thelazychef.app, ser en statusside mens den lages, og havner på oppskriftssiden når den er klar (under ett minutt).
2. Oppskriften ligger i de nye tabellene med `schema_version = 2`, er gyldig etter validatoren og har `source_text` fra runde 1.
3. Oppskriftssiden viser den på telefon: oversikt med handleliste og symboler, og stegene i planlagt rekkefølge med symbol i mengdepillen og klargjøringen i cook-steg.
4. Mislykket generering blir et utkast med feilene synlige for admin, ikke en feilside.
5. Gamle oppskrifter og dagens generering virker som før.

## Hva som er med, og hva som venter

| Med i skiven | Venter til 7c |
|---|---|
| Idé og innlimt tekst som kilde | Nettside og video (adapterne fra piloten flyttes da) |
| Runde 1 og 2 med Opus 5.5 `low`, validator med nye forsøk | Redigering og ny strukturering |
| De nye tabellene for komponenter, linjer og steg | Former, enhetstabell, tetthet, allergener, grunnvare |
| Planleggeren («Rolig») i Python | «Prep først» og «Akkurat i tide» |
| Oversikt og stegliste på oppskriftssiden | Gjør klart, kortmodus med pågår, stor skjerm |
| Design-tokens med dagens uttrykk | Helhetlig uttrykk (7d) |
| Promptendringene fra pilotrapporten | Næring |

## Rekkefølge: fem PR-er

Hver PR kan deployes alene og endrer ikke det som finnes.

**PR 1: Datamodell.** Nye tabeller for komponent, ingredienslinje og steg, med koblingstabeller for `uses` og `after` og `ON DELETE CASCADE`. Nye felt på `recipe`: `schema_version`, `revision`, `revised_at`, `source_text`, `validation_errors`, `chef_note` og `yield_text`. Bare nye tabeller og nullbare felt, ingen dataendring. Migreringen testes mot tom database i CI og mot en kopi av produksjon lokalt.

**PR 2: Generering uten infrastruktur.** `services/recipe_v2/` med promptene, runde 1, runde 2 med strukturert output og validatoren i løkke, pantry-treff og lagring. Modellens `pantry_id` kontrolleres av matcheren. Ingredienser som ikke finnes i pantryet, lagres uten kobling, og oppskriften flagges. Et skript lager en oppskrift lokalt mot lokal database. Testene bruker lagrede svar fra piloten, så CI kaller ikke Claude. Her kommer også promptendringene fra pilotrapporten (komponentregelen, manglende mengder og porsjoner, rettede kildefeil i `chef_note`, `prep_style` i rendringen) og advarselen for «hver» ved totalmengde.

**PR 3: Planleggeren og lesemodellen.** `schedule()` fra prototypen i Python, «Rolig» først, og utledning av handleliste og mise-elementer. Testene sjekker at de fem fasitrettene gir samme rekkefølge og totaltid som i prototypen.

**PR 4: Visningen.** Oppskriftssiden velger ny mal når `schema_version = 2`: oversikt (tid, mengde, handleliste med symboler, utstyr) og steglisten fra telefonprototypen. Bygget på design-tokens i én CSS-fil med dagens farger og fonter. Prøves lokalt med en oppskrift fra PR 2.

**PR 5: Bakgrunnsjobben.** Cloud Tasks-kø, internt endepunkt som kjører rundene, statusside, og et nytt input-felt i New Recipe for admin. `ANTHROPIC_API_KEY` og tidsavbrudd i deploy-oppsettet. Når denne er ute, er skiven ferdig.

PR 2 og PR 3 kan lages parallelt. PR 5 krever infrastruktur, se under.

## Beslutninger som trenger ditt ja

**1. Claude i produksjon: nøkkel i Secret Manager (anbefalt) eller identitetsføderasjon.** En nøkkel virker som de andre hemmelighetene og er klar på minutter. Føderasjon fjerner den faste nøkkelen, men krever oppsett mellom Google Cloud og Anthropic som ikke er prøvd her. Anbefaling: nøkkel nå, føderasjon vurderes i 7c. Det bør være en egen produksjonsnøkkel med 90 dagers utløp og rotasjon etter `docs/runbooks/ROTATE_SECRETS.md`, ikke pilotnøkkelen.

**2. Betaling.** Kredittene fra Max-planen dekker utvikling. Sjekk vilkårene for om de kan brukes for et offentlig produkt. Er svaret nei, får produksjonsnøkkelen vanlig fakturering med månedsgrense. Kostnaden er lav: ca. 0,15 USD per ny oppskrift fra idé.

**3. Cloud Tasks-oppsettet.** Krever, i prosjekt `thelazychefai-prod`:
- Cloud Tasks API slås på, og en kø `recipe-generation` i europe-west1 med maks 2 samtidige og 3 nye forsøk.
- En tjenestekonto som køen bruker til å kalle appen (OIDC), med rollen Cloud Run Invoker.
- Rollen Cloud Tasks Enqueuer for appens tjenestekonto.

Dette er endringer i produksjon. Jeg skriver kommandoene i PR 5, og du kjører dem eller gir meg ja til å kjøre dem.

**4. Språk.** Notatet sier engelsk som førstespråk, men piloten skrev runde 1 på norsk. Anbefaling: runde 1 skriver på engelsk i produksjon, mens innlimte oppskrifter beholder kildens språk. Prototypene er på norsk og påvirkes ikke.

**5. Ingredienser som mangler i pantryet.** Anbefaling for skiven: linjen lagres uten kobling til pantryet, med navnet fra modellen, og oppskriften flagges for gjennomgang. Løsningen der admin godkjenner nye ingredienser, kommer i 7c sammen med resten av pantry-arbeidet.

## Risiko

- **Tidsavbrudd:** Opus `low` brukte 22–66 sekunder i piloten. Cloud Tasks venter opptil 10 minutter, og det interne endepunktet får 300 sekunders tidsavbrudd. Dagens generering kjører rett i forespørselen og blir stående som den er til steg 8.
- **Cloud Run strupes etter svar:** løses av Cloud Tasks, fordi jobben er selve forespørselen.
- **Migrering i produksjon:** bare nye tabeller og nullbare felt. Ingen eksisterende rader endres.
- **Kostnad:** hver generering koster ca. 0,15 USD. Køen begrenser antall samtidige, og månedsgrensen hos Anthropic stopper resten.
