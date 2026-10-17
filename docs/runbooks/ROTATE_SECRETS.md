# Runbook: bytte hemmeligheter og flytte dem til Secret Manager

Bakgrunn: `GOOGLE_API_KEY`, databasepassordet og `SECRET_KEY` har ligget i klartekst i en Claude-samtale og som miljøvariabler på Cloud Run. Deploy-workflowen satte `GOOGLE_API_KEY` og `DB_PASS` som vanlige miljøvariabler fra GitHub-secrets. Etter denne runbooken er alle tre nye, ligger i Secret Manager, og Cloud Run leser dem derfra.

Kjøres fra Mac minien. Verdiene skrives aldri på kommandolinjen, så de havner ikke i shell-historikken.

| | |
|---|---|
| Prosjekt | `thelazychefai-prod` |
| Tjeneste | `lazy-chef-app` (europe-west1) |
| Migreringsjobb | `lazy-chef-db-migration` (europe-west1) |
| Cloud SQL-instans | `lazy-chef-db-eu` |
| Secrets | `GOOGLE_API_KEY`, `DB_PASSWORD`, `SECRET_KEY` (den siste lages hvis den mangler) |

Merk:
- Steg 4 gir noen sekunders databasefeil mellom passordbyttet og den nye revisjonen.
- Ny `SECRET_KEY` logger ut alle innloggede brukere.

## 0. Forberedelser

```bash
gcloud auth login
gcloud config set project thelazychefai-prod
gh auth status
```

Finn databasebrukeren (samme som GitHub-secret `DB_USER`):

```bash
gcloud sql users list --instance=lazy-chef-db-eu
```

## 1. Lag en ny Gemini-nøkkel

Lag den samme sted som den gamle: Google AI Studio (API keys) eller Cloud Console under *APIs & Services → Credentials* i `thelazychefai-prod`. Begrens nøkkelen til *Generative Language API*. Ikke slett den gamle ennå.

## 2. Legg nye verdier i Secret Manager

Gemini-nøkkelen (limes inn ved spørsmålet, vises ikke):

```bash
read -s -p "Ny Gemini-nøkkel: " K && printf %s "$K" | gcloud secrets versions add GOOGLE_API_KEY --data-file=- ; unset K; echo
```

Nytt databasepassord, generert:

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32),end='')" | gcloud secrets versions add DB_PASSWORD --data-file=-
```

Ny `SECRET_KEY`. Lag secreten først hvis den ikke finnes (`gcloud secrets describe SECRET_KEY` gir feil):

```bash
gcloud secrets create SECRET_KEY --replication-policy=automatic
```

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(48),end='')" | gcloud secrets versions add SECRET_KEY --data-file=-
```

## 3. Gi tjenestekontoen lesetilgang

Finn kontoen som tjenesten og jobben kjører som:

```bash
gcloud run services describe lazy-chef-app --region europe-west1 --format='value(spec.template.spec.serviceAccountName)'
```

Er svaret tomt, er det standardkontoen `PROSJEKTNUMMER-compute@developer.gserviceaccount.com`. Gi tilgang til alle tre (bytt ut `SA`):

```bash
for S in GOOGLE_API_KEY DB_PASSWORD SECRET_KEY; do gcloud secrets add-iam-policy-binding $S --member=serviceAccount:SA --role=roles/secretmanager.secretAccessor; done
```

Gjør det samme for migreringsjobben hvis den bruker en annen konto (`gcloud run jobs describe lazy-chef-db-migration --region europe-west1`).

## 4. Bytt databasepassordet og koble Cloud Run til Secret Manager

Kjør de tre kommandoene rett etter hverandre (bytt ut `DBBRUKER`):

```bash
gcloud sql users set-password DBBRUKER --instance=lazy-chef-db-eu --password="$(gcloud secrets versions access latest --secret=DB_PASSWORD)"
```

```bash
gcloud run services update lazy-chef-app --region europe-west1 --remove-env-vars=GOOGLE_API_KEY,DB_PASS,SECRET_KEY --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest,DB_PASS=DB_PASSWORD:latest,SECRET_KEY=SECRET_KEY:latest
```

```bash
gcloud run jobs update lazy-chef-db-migration --region europe-west1 --remove-env-vars=GOOGLE_API_KEY,DB_PASS --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest,DB_PASS=DB_PASSWORD:latest
```

Avviser gcloud at samme navn fjernes og settes i én kommando, kjør `--remove-env-vars` og `--update-secrets` som to kommandoer rett etter hverandre.

## 5. Sjekk at appen virker

Åpne appen, logg inn, og generer eller åpne en oppskrift. Se etter feil i loggene:

```bash
gcloud run services logs read lazy-chef-app --region europe-west1 --limit 50
```

## 6. Få deploy-workflowen til å bruke Secret Manager

Grenen `chore/secrets-to-secret-manager` endrer `.github/workflows/deploy.yaml`, slik at tjenesten og migreringsjobben leser hemmelighetene fra Secret Manager i stedet for å få dem som miljøvariabler. Merge den først når steg 2–5 er gjort. Ellers feiler neste deploy fordi `SECRET_KEY` mangler eller kontoen ikke har tilgang.

Oppdater også GitHub-secreten som testene bruker, med den nye Gemini-nøkkelen (verdien spørres om, vises ikke):

```bash
gh secret set GOOGLE_API_KEY --repo pedal88/thelazychef
```

Etter merge og en vellykket deploy brukes ikke GitHub-secreten `DB_PASS` lenger:

```bash
gh secret delete DB_PASS --repo pedal88/thelazychef
```

## 7. Rydd opp

- Slett den gamle Gemini-nøkkelen der den ble laget.
- Deaktiver de gamle versjonene i Secret Manager (`gcloud secrets versions list GOOGLE_API_KEY` viser numrene):

  ```bash
  gcloud secrets versions disable GAMMELT_NUMMER --secret=GOOGLE_API_KEY
  ```

  Gjør det samme for `DB_PASSWORD`.
- Slett `.env` i pilot-worktreen på laptopen (`~/code/thelazychef/.claude/worktrees/pilot-recipe-v2-940716/.env`).
