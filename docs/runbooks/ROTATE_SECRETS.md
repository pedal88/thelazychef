# Runbook: bytte hemmeligheter og flytte dem til Secret Manager

Bakgrunn: `GOOGLE_API_KEY`, databasepassordet og `SECRET_KEY` har ligget i klartekst i en Claude-samtale og som miljøvariabler på Cloud Run. Deploy-workflowen satte dem som vanlige miljøvariabler fra GitHub-secrets ved hver deploy. Etter denne runbooken er alle tre nye, ligger i Secret Manager, og Cloud Run leser dem derfra.

Kjøres fra Mac minien. Verdiene skrives aldri på kommandolinjen eller i terminalen, så de havner ikke i shell-historikken eller i en samtale.

| | |
|---|---|
| Prosjekt | `thelazychefai-prod` |
| Tjeneste | `lazy-chef-app` (europe-west1) |
| Migreringsjobb | `lazy-chef-db-migration` (europe-west1) |
| Cloud SQL-instans | `lazy-chef-db-eu` |
| Databasebruker | `postgres` |
| Secrets | `GOOGLE_API_KEY`, `DB_PASS`, `SECRET_KEY` |
| Gemini-nøkkel | Prosjektet `ai-chef-2026` (`gen-lang-client-0770637546`, kontoen pedal88, etterskuddsfakturering) |

Gemini-nøkkelen ligger ikke i `thelazychefai-prod`. Der er Gemini-faktureringen forhåndsbetalt, og når kreditten er tom gir API-et `402 RESOURCE_EXHAUSTED` (appen viser «AI generation is temporarily unavailable (billing)»).

Merk:
- Steg 4 gir noen sekunders databasefeil mellom tjenesteoppdateringen og passordbyttet.
- Ny `SECRET_KEY` logger ut alle innloggede brukere.
- Alt som logger inn i databasen som `postgres` (lokale skript, Cloud SQL Studio o.l.) må bruke det nye passordet etterpå.
- Ikke merge noe til `main` mens steg 2–4 pågår.

## 0. Forberedelser

```bash
brew install --cask gcloud-cli
gcloud auth login --no-launch-browser   # lim lenken inn i Chrome-profilen som eier prosjektet
gcloud config set project thelazychefai-prod
gh auth status
```

Se hva som finnes. Kommandoene viser bare navn, aldri verdier. Ikke kjør `services describe` uten `--format`, for da skrives verdiene ut.

```bash
gcloud run services describe lazy-chef-app --region europe-west1 --format='value(spec.template.spec.containers[0].env[].name)'
gcloud run jobs describe lazy-chef-db-migration --region europe-west1 --format='value(spec.template.spec.template.spec.containers[0].env[].name)'
gcloud secrets list --format='value(name)'
gcloud sql users list --instance=lazy-chef-db-eu
```

## 1. Lag en ny Gemini-nøkkel

Lag den med gcloud i samme prosjekt som den gamle, så kvoter og fakturering ikke endres. Ikke bruk AI Studio: der vises nøkkelen i klartekst, og den nye `AQ.`-nøkkeltypen derfra ble avvist med `API_KEY_INVALID` i oktober 2026. gcloud lager en vanlig nøkkel og skriver den aldri ut.

Logg inn med kontoen som eier prosjektet, og bytt tilbake til app-kontoen etterpå:

```bash
gcloud auth login --no-launch-browser   # i pedal88-profilen
gcloud config set account thelazychefai@gmail.com
```

Finn den gamle nøkkelen (bare navn og ID-er vises):

```bash
gcloud services api-keys list --account=pedal88@gmail.com --project=gen-lang-client-0770637546 --format='table(displayName,uid,createTime,restrictions.apiTargets[].service)'
```

Lag en ny, begrenset til Gemini. `--async` gjør at nøkkelen ikke skrives ut:

```bash
gcloud services api-keys create --account=pedal88@gmail.com --project=gen-lang-client-0770637546 --display-name=lazychef-prod-ÅÅÅÅ-MM --api-target=service=generativelanguage.googleapis.com --async
```

Kjør list-kommandoen igjen for å finne UID-en. Ikke slett den gamle ennå.

## 2. Legg nye verdier i Secret Manager

Gemini-nøkkelen går rett fra API Keys til Secret Manager uten å vises (bytt ut `NY_UID` med UID-en fra steg 1):

```bash
gcloud services api-keys get-key-string NY_UID --account=pedal88@gmail.com --project=gen-lang-client-0770637546 --format='value(keyString)' | tr -d '\n' | gcloud secrets versions add GOOGLE_API_KEY --data-file=-
```

Test at den kan generere tekst, ikke bare liste modeller (det siste virker også når faktureringen ikke gjør det). Skal gi `200`. `403` betyr vent ett minutt, `400` ugyldig nøkkel og `402` tom kreditt:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -H "x-goog-api-key: $(gcloud secrets versions access latest --secret=GOOGLE_API_KEY)" -H 'Content-Type: application/json' -d '{"contents":[{"parts":[{"text":"hi"}]}]}' https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent
```

Nytt databasepassord og ny `SECRET_KEY`, generert. Lag secreten først hvis den mangler (`gcloud secrets create NAVN --replication-policy=automatic`):

```bash
python3 -c "import secrets;print(secrets.token_urlsafe(32),end='')" | gcloud secrets versions add DB_PASS --data-file=-
python3 -c "import secrets;print(secrets.token_urlsafe(48),end='')" | gcloud secrets versions add SECRET_KEY --data-file=-
```

## 3. Gi tjenestekontoen lesetilgang

Finn kontoen tjenesten og jobben kjører som. Tomt svar betyr standardkontoen `PROSJEKTNUMMER-compute@developer.gserviceaccount.com`:

```bash
gcloud run services describe lazy-chef-app --region europe-west1 --format='value(spec.template.spec.serviceAccountName)'
gcloud run jobs describe lazy-chef-db-migration --region europe-west1 --format='value(spec.template.spec.template.spec.serviceAccountName)'
```

Gi tilgang (bytt ut `SA`), og sjekk:

```bash
for S in GOOGLE_API_KEY DB_PASS SECRET_KEY; do gcloud secrets add-iam-policy-binding $S --member=serviceAccount:SA --role=roles/secretmanager.secretAccessor --format='value(etag)'; done
for S in GOOGLE_API_KEY DB_PASS SECRET_KEY; do echo "== $S"; gcloud secrets get-iam-policy $S --format='value(bindings.role,bindings.members)'; done
```

## 4. Koble Cloud Run til Secret Manager og bytt databasepassordet

Rekkefølgen er valgt slik at en feil tidlig ikke tar ned appen. Appen kobler seg ikke til databasen ved oppstart, så en ny revisjon starter selv om passordet ikke er byttet ennå. Kjør én og én, og stopp ved feil.

A. Migreringsjobben (merkes ikke, den kjører bare ved deploy):

```bash
gcloud run jobs update lazy-chef-db-migration --region europe-west1 --remove-env-vars=GOOGLE_API_KEY,DB_PASS --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest,DB_PASS=DB_PASS:latest
```

B. Tjenesten. Feiler denne, er ingenting ødelagt:

```bash
gcloud run services update lazy-chef-app --region europe-west1 --remove-env-vars=GOOGLE_API_KEY,DB_PASS,SECRET_KEY --update-secrets=GOOGLE_API_KEY=GOOGLE_API_KEY:latest,DB_PASS=DB_PASS:latest,SECRET_KEY=SECRET_KEY:latest
```

C. Rett etter B, bytt passordet:

```bash
gcloud sql users set-password postgres --instance=lazy-chef-db-eu --password="$(gcloud secrets versions access latest --secret=DB_PASS)"
```

D. Kontroll. Skal liste de tre secretene:

```bash
gcloud run services describe lazy-chef-app --region europe-west1 --format='value(spec.template.spec.containers[0].env[].valueFrom.secretKeyRef.name)'
```

## 5. Sjekk at appen virker

Logg inn på https://thelazychef.app og generer en oppskrift (tester både database og Gemini). Se etter feil i loggene:

```bash
gcloud run services logs read lazy-chef-app --region europe-west1 --limit 50
```

## 6. Få deploy-workflowen til å bruke Secret Manager

`.github/workflows/deploy.yaml` gir tjenesten og migreringsjobben hemmelighetene fra Secret Manager i stedet for som miljøvariabler. Endringen merges først når steg 2–5 er gjort. Ellers feiler neste deploy fordi secreten mangler eller kontoen ikke har tilgang.

Testene i CI bruker en dummy-nøkkel, for de kaller ikke Gemini. Etter merge og en vellykket deploy brukes ikke disse GitHub-secretene lenger:

```bash
gh secret delete GOOGLE_API_KEY --repo pedal88/thelazychef
gh secret delete DB_PASS --repo pedal88/thelazychef
gh secret delete SECRET_KEY --repo pedal88/thelazychef
```

## 7. Rydd opp

- Slett den gamle Gemini-nøkkelen (UID fra steg 1):

  ```bash
  gcloud services api-keys delete GAMMEL_UID --account=pedal88@gmail.com --project=gen-lang-client-0770637546
  ```

- Deaktiver de gamle versjonene i Secret Manager (`gcloud secrets versions list NAVN` viser numrene):

  ```bash
  gcloud secrets versions disable GAMMELT_NUMMER --secret=GOOGLE_API_KEY
  gcloud secrets versions disable GAMMELT_NUMMER --secret=DB_PASS
  ```

- Gamle Cloud Run-revisjoner har fortsatt de gamle verdiene i klartekst i konfigurasjonen. Det er ufarlig når nøkkelen er slettet og passordet byttet, men ikke rull tilbake til en av dem.
- Slett `.env` i pilot-worktreen på laptopen (`~/code/thelazychef/.claude/worktrees/pilot-recipe-v2-940716/.env`).

## Senere bytter

Når alt ligger i Secret Manager, er et bytte enklere: legg til en ny versjon (steg 2), og test den med `generateContent`, og lag en ny revisjon så alle instanser leser `latest` (`gcloud run services update lazy-chef-app --region europe-west1 --update-labels=rotated=ÅÅÅÅ-MM-DD`). For databasepassordet kjøres steg 4 B og C.

## Nøkkelen til innholds-API-et (`CONTENT_API_KEY`)

Claude Code på MacBooken sender guider og forsiden som utkast med denne nøkkelen (`docs/CONTENT.md`, «The content API»). Den ligger i Secret Manager og i Keychain på MacBooken, og vises aldri i terminalen. Uten den svarer API-et 401, og ingenting annet i appen påvirkes.

Alt gjøres på MacBooken (gcloud er logget inn som `thelazychefai@gmail.com` mot `thelazychefai-prod`). Nøkkelen går rett fra Secret Manager til Keychain, uten utklippstavle. Hemmeligheten og tilgangen må finnes før deployen, ellers feiler «Deploy to Prod» med `Permission denied on secret`.

Første gang (eller hvis deployen feilet av den grunnen):

```bash
P=thelazychefai-prod
SA=$(gcloud run services describe lazy-chef-app --region europe-west1 --project $P --format='value(spec.template.spec.serviceAccountName)')
SA=${SA:-$(gcloud projects describe $P --format='value(projectNumber)')-compute@developer.gserviceaccount.com}
openssl rand -hex 32 | tr -d '\n' | gcloud secrets create CONTENT_API_KEY --data-file=- --project=$P
gcloud secrets add-iam-policy-binding CONTENT_API_KEY --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor --format='value(etag)' --project=$P
security add-generic-password -U -a "$USER" -s thelazychef-content-api -w "$(gcloud secrets versions access latest --secret=CONTENT_API_KEY --project=$P)"
security find-generic-password -s thelazychef-content-api -w | wc -c   # 65: 64 tegn og linjeskiftet
```

Feilet deployen, kjør den feilede jobben på nytt: `gh run rerun <run-id> --failed` (id-en fra `gh run list --branch main --limit 1`). Etterpå skal `python -m scripts.content pages` liste sidene.

Bytte senere: samme blokk, men `gcloud secrets versions add` i stedet for `create` og uten `add-iam-policy-binding`. Lag så en ny revisjon som under «Senere bytter», så appen leser den nye versjonen.
