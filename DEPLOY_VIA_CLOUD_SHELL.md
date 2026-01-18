# Deploy via Google Cloud Shell (CLI Alternative)

## Why This Method?
Your local `gcloud` CLI has a persistent issue. Cloud Shell is a browser-based terminal provided by Google that has `gcloud` pre-installed and always works.

## Steps

### 1. Create Deployment Package
Run this from your local machine:
```bash
cd ~/Projects/bym2026
tar -czf bym2026-deploy.tar.gz \
  --exclude='.git' \
  --exclude='venv' \
  --exclude='google-cloud-sdk' \
  --exclude='*.tar.gz' \
  --exclude='__pycache__' \
  --exclude='static/pantry' \
  --exclude='static/recipes' \
  --exclude='instance' \
  .
```

This creates a ~5MB archive.

### 2. Open Cloud Shell
1. Go to https://console.cloud.google.com
2. Click the **Cloud Shell** icon (terminal icon) in the top-right corner
3. Wait for the shell to activate

### 3. Upload Your Code
In Cloud Shell, click the **⋮** (three dots) menu → **Upload** → Select `bym2026-deploy.tar.gz`

### 4. Extract and Deploy
In Cloud Shell terminal:
```bash
# Extract
mkdir bym2026 && cd bym2026
tar -xzf ../bym2026-deploy.tar.gz

# Set your project
gcloud config set project bym-app-287448924512

# Build and deploy in one command
gcloud run deploy bym-app \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances gen-lang-client-0770637546:us-central1:buildyourmeal \
  --set-env-vars "DB_BACKEND=cloudsql,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=buildyourmeal-assets,INSTANCE_CONNECTION_NAME=gen-lang-client-0770637546:us-central1:buildyourmeal,DB_USER=postgres,DB_NAME=postgres,FLASK_DEBUG=0" \
  --set-secrets "DB_PASS=DB_PASSWORD:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest"
```

**Note:** You'll need to create secrets in Secret Manager first:
```bash
# Create secrets (one-time setup)
echo -n "YOUR_DB_PASSWORD" | gcloud secrets create DB_PASSWORD --data-file=-
echo -n "YOUR_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
```

### 5. Monitor Progress
Cloud Shell will show you real-time progress:
- ✓ Uploading code
- ✓ Building container
- ✓ Deploying to Cloud Run
- ✓ Service URL

## Advantages
- ✅ No local CLI issues
- ✅ Fast, reliable Google network
- ✅ Built-in authentication
- ✅ Works from any browser
