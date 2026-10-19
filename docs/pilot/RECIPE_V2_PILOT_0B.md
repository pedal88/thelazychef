# Pilot: oppskriftsmodell v2, fase 0b (Claude mot Gemini)

Dato: 19.10.2026
Beslutning som testes: `docs/RECIPE_MODEL_V2.md`, avsnitt 2 og steg 5 i planen: hvilken modell skal skrive oppskriftsteksten (runde 1) og strukturere den (runde 2)?
Kode: `scripts/pilot_v2b.py`. Promptene er `data/prompts/recipe_v2/` med reglene fra fase 0-rapporten.
Resultater: `data/pilot_v2/results_0b/` for fasit og database. Nettsider og video ligger utenfor repoet (`~/promptlab-runs/pilot-0b`), fordi kildetekstene tilhører andre.

## Konklusjon

**Claude Opus 5.5 med effort `low` anbefales for begge rundene.** Den er like pålitelig som den dyreste konfigurasjonen, tre ganger raskere enn Gemini, fyller alltid inn pantry-ID og retter åpenbare feil i kilden i stedet for å kopiere dem. Kostnaden er rundt 0,07 USD for strukturering og 0,15 USD for en ny oppskrift fra idé, altså om lag 4 USD for de 56 godkjente oppskriftene i steg 8.

| | Anbefaling | Begrunnelse |
|---|---|---|
| Runde 1, tekst | Opus 5.5, `low` | Rikest og mest presise tekst. Kostnaden er liten (ca. 0,04 USD) |
| Runde 2, strukturering | Opus 5.5, `low` | 23 av 24 gyldige i første forsøk, 29 sekunder i snitt, 100 % pantry-ID |
| Video til tekst | Gemini (som vedtatt) | Fungerte. Claude tar ikke video |
| Ikke valgt | Opus `medium` | Ikke bedre resultat, dobbel kostnad, og én gang tom for tokens |
| Ikke valgt | Sonnet 5.5 | Flere nye forsøk, ID-rot, mangler pantry-ID, og kopierer feil i kilden |
| Ikke valgt | Gemini | Pålitelig og billig, men 92 sekunder i snitt. Beholdes som reserve |

Alle 120 kjøringer endte gyldige. Forskjellene ligger i første forsøk, tid, pantry-treff og hvordan modellene håndterer svake kilder.

## Oppsett

| | |
|---|---|
| Konfigurasjoner | `gemini` (`gemini-flash-latest`, koden fra fase 0 med ny prompt), `sonnet-low`, `sonnet-high`, `opus-low`, `opus-medium` |
| Claude | Strukturert output mot `RecipeV2Schema` (`output_config.format`), adaptiv tenking, regler, kataloger og eksempler som bufret systemprompt |
| Prompt | Fase 0-promptet med reglene fra rapporten: `setup` er all klargjøring av utstyr, `{iN}` er alltid totalen, serveringssteg når kilden mangler det, og skarpere komponentdefinisjon |
| Validering | Regel 1–8, maks to nye forsøk, som i fase 0. Ny advarsel `no_preheat` |
| Testsett | Fasit (5 retter fra én setning), database (15 godkjente oppskrifter, samme som fase 0), og nytt: 4 kilder fra nettet |

Nettkildene, hentet gjennom adapterne slik de skal virke i appen:

| Kilde | Adapter | Hva den tester |
|---|---|---|
| Gladkokken, Marry Me Chicken (norsk) | Nettside, schema.org-oppskrift | Norsk kilde, antall porsjoner bare som «3porsjoner» |
| RecipeTin Eats, Chicken Chasseur (engelsk) | Nettside, schema.org-oppskrift | Lang blogg der oppskriften ligger nederst |
| TikTok, Korean Beef Rice Bowls | Video til tekst med Gemini | Mengdene står bare i videoen, ikke i bildeteksten |
| TikTok, Karamellisert og sticky svinenakke | Video til tekst med Gemini | Norsk, hele oppskriften i bildeteksten. Samme rett som db-257 |

Half Baked Harvest var førstevalget, men siden er beskyttet av Cloudflare og avviser alle skript (403).

## Resultater

| Konfigurasjon | Bestått | Første forsøk | USD per oppskrift | Snitt s | Maks s | Pantry-ID utfylt |
|---|---|---|---|---|---|---|
| gemini | 24/24 | 22/24 | 0,045 | 92 | 151 | 100 % |
| sonnet-low | 24/24 | 17/24 | 0,055 | 27 | 62 | 73 % |
| sonnet-high | 24/24 | 17/24 | 0,083 | 49 | 95 | 87 % |
| **opus-low** | **24/24** | **23/24** | **0,091** | **29** | **66** | **100 %** |
| opus-medium | 24/24 | 23/24 | 0,150 | 53 | 227 | 100 % |

Kostnaden er for hele kjeden. For fasit og nett inkluderer den runde 1. Bare strukturering (databasesettet): gemini 0,044, sonnet-low 0,047, sonnet-high 0,069, opus-low 0,070 og opus-medium 0,149 USD. Hele piloten kostet 10,17 USD for 120 kjøringer.

**Regler som feilet i første forsøk:**

| Konfigurasjon | Regler (antall) |
|---|---|
| gemini | 3 (1), 7 (1) |
| sonnet-low | 1 (4), 4 (2), 5 (2), 8 (2), 3 (1), 6 (1) |
| sonnet-high | 1 (5), 4 (3), 5 (3), 2 (2) |
| opus-low | 8 (1) |
| opus-medium | ugyldig JSON (1): traff tokengrensen på 32 000 i én oppskrift og brukte 227 sekunder |

Sonnet feiler oftest på regel 1 (ID-er), og i nye forsøk dukker det opp ID-er som `i_dummy_removed_placeholder_never_used_x`. Strukturen blir riktig til slutt, men det koster tid og gir en grunn til å ikke stole på den.

### Funnene fra fase 0

Kontrollene som telte funnene i fase 0, kjørt på alle resultatene:

| | Fase 0 (Gemini, gammelt prompt) | gemini | sonnet-low | sonnet-high | opus-low | opus-medium |
|---|---|---|---|---|---|---|
| Ugyldige komponenter («Assembly», «Garnish») | 13 av 15 db | 0 | 5 | 1 | 2 | 1 |
| «hver» ved siden av totalmengde | 5 | 2 | 5 | 3 | 5 | 3 |
| Ovn uten forvarming | 1 | 0 | 0 | 0 | 0 | 0 |
| Sluttsteg som ikke er servering | – | 0 | 0 | 0 | 0 | 0 |

Promptreglene virker: komponentnavnene er nesten borte, og forvarmingen er på plass overalt. «Hver»-regelen virker dårligere. Telleren er grov og fanger også riktige formuleringer, men noen er reelle («1 skive ost på hver burger» med totalen). Validatoren bør få en advarsel for det, så det kan rettes i nytt forsøk.

### Trofasthet mot kilden (databasesettet)

Med treff på pantry-ID og navn er alle konfigurasjonene trofaste mot kilden. Ingen ingredienser mangler og ingen mengder er endret. To forskjeller viser seg likevel:

- **Feil i kilden:** gyros (db-190) har «4 g pita» i databasen. Gemini og begge Opus-konfigurasjonene skrev 4 stk. Sonnet kopierte 4 g.
- **Lagt til:** sonnet-low la til «1 klype salt» som ikke finnes i kilden. opus-low la til «salt» uten mengde.

### Komponenter

Den skarpere regelen om at sauser og fyll er egne komponenter, gjør at Claude deler mer enn fasiten: «Eggekrem» i carbonara (sonnet-low), «Eggesaus» (opus-medium), «Marinert kylling» (sonnet-low), «Dressing» som egen komponent ved siden av salaten (opus-low). Dressing og burgersaus er greit, siden de kan pekes på. Eggeblandingen og marinaden er ikke det. Gemini holdt seg nærmest fasiten. Regelen må presiseres (se under).

### Runde 1: teksten

Alle skriver godt norsk. Opus skriver de mest gjennomarbeidede oppskriftene: tikka masala med grønn chili og kasuri methi, lime til servering, og tydelige delgrupper. Gemini og Sonnet er solide, men enklere. Runde 1 tar 18–37 sekunder og koster 0,007–0,06 USD, så den bør velges etter kvalitet og ikke etter pris.

### Nettsider og video

- **schema.org-oppskriften virker.** Begge nettsidene ga ren oppskriftstekst. Appens skraper kutter i dag ved 20 000 tegn. RecipeTin Eats, Pinch of Yum og Serious Eats traff alle grensen i en test, med oppskriftskortet nær eller etter kuttet. Adapteren i piloten bør erstatte den i v2-bygget.
- **Bot-beskyttelse:** Half Baked Harvest (Cloudflare) og Budget Bytes avviser skript. Appen trenger «lim inn teksten» som reserve når en lenke ikke kan leses.
- **Videoadapteren virker.** Gemini fant mengdene for Korean Beef Rice Bowls i selve videoen. Det den ikke fant, ble merket «(amount not given)».
- **Manglende mengder gir regel 8-feil.** Vårløk og avokado uten mengde ble linjer uten mengde og uten «etter smak», og Sonnet og opus-low trengte nytt forsøk. Promptet må si hva som gjøres med «(amount not given)».
- **Manglende porsjoner gir ulike svar.** Videoen sier ikke antall porsjoner, og modellene valgte 1, 2 eller 4. Promptet må ha en regel for anslag.

## Anbefalte endringer

Til v2-bygget (steg 7):

1. **Modellvalg:** Opus 5.5 med effort `low` for runde 1 og 2, Gemini for video til tekst. Modellnavnene ligger i `services/ai_models.py`.
2. **Komponentregelen presiseres:** en komponent er noe du kan peke på i den ferdige retten, eller en saus eller et fyll som lages for seg og legges inn (lasagne). Marinade, eggeblanding og krydderblanding er ikke komponenter. De hører til komponenten de går inn i.
3. **Ny promptregel for manglende mengder:** linjer merket «(amount not given)» får `prep_style` «etter smak» (eller «to taste») hvis de er pynt eller krydder, ellers et anslag med «ca.».
4. **Ny promptregel for porsjoner:** mangler kilden antall porsjoner, anslås det ut fra hovedingrediensen, og det står i `chef_note`.
5. **Rettede kildefeil logges:** modellen får lov å rette åpenbare enhetsfeil («4 g pita»), men skal nevne rettelsen i `chef_note`, så de kan sjekkes.
6. **Ny advarsel i validatoren:** `{iN}` ved siden av «hver», «per» eller «each», så det rettes i nytt forsøk.
7. **Webadapteren fra piloten** (schema.org først, deretter sidetekst) erstatter dagens skraper, og «lim inn tekst» blir reserve når en lenke avvises.
8. **Pantry-treff kontrolleres i koden:** modellens `pantry_id` er et forslag. Matcheren i appen bekrefter eller retter det.
9. **`max_tokens`:** 32 000 holdt ikke for én oppskrift med `medium`. Med `low` var det ingen problem, men grensen bør settes høyere eller strømmingen håndtere stopp.

## Begrensninger

- **Én kjøring per oppskrift og konfigurasjon.** Variasjon mellom kjøringer er ikke målt.
- **Kvaliteten på grafene er målt med regler og stikkprøver**, ikke med en blind gjennomgang. Den beste testen er å lage noen av oppskriftene med telefonprototypen.
- **De to Gemini-videokjøringene** (`web-68720e7b`, `web-a711fb72`) kan ha lest et eldre strukturprompt i runde 2, fordi arbeidskopien byttet gren i noen sekunder under kjøringen. De kjøres på nytt, og tallene for Gemini på nett oppdateres.
- **Prisene** er listepriser fra oktober 2026 og regnet fra token-tallene i svaret.
- **Faste ingredienser mangler i pantryet:** ni av ingrediensene i de fem rettene finnes ikke (blant annet fersk ingefær, garam masala, tomatpuré og oksebuljong). Det påvirker ikke strukturen, men pantryet må fylles før nygenereringen.

## Hvordan kjøre på nytt

Kjør fra roten av repoet:

```
python scripts/pilot_v2b.py --fetch URL [URL ...]          # henter nettsider og video til web-settet
python scripts/pilot_v2b.py --config all --set all          # alle konfigurasjoner (ANTHROPIC_API_KEY og GOOGLE_API_KEY)
python scripts/pilot_v2b.py --summary                       # tabellen fra lagrede resultater
```

Kjøringer som finnes fra før, hoppes over. Bruk `--force` for å kjøre på nytt.
