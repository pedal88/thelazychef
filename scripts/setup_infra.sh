#!/bin/bash

# ==============================================================================
# LAZY CHEF INFRASTRUCTURE SETUP
# This script aligns your GCP Project with the 'thelazychef' repo requirements.
# ==============================================================================

# 1. Configuration - CHANGE THESE IF NEEDED
REGION="europe-north2"
REPO_NAME="app-repo"
GITHUB_REPO="pedal88/thelazychef" # The NEW fork
# We assume you are using the same pool/provider name as the old project, 
# or creating standard ones.
POOL_NAME="github-pool"
PROVIDER_NAME="github-provider"

# 2. Safety Checks
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    echo "❌ ERROR: No Google Cloud Project selected."
    echo "   Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

PROJECT_ID=$GOOGLE_CLOUD_PROJECT
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
SERVICE_ACCOUNT="github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==================================================="
echo "Configuring Project: $PROJECT_ID"
echo "Region:              $REGION"
echo "GitHub Repo:         $GITHUB_REPO"
echo "Service Account:     $SERVICE_ACCOUNT"
echo "==================================================="

# 3. Enable Required APIs
echo "🔄 Enabling required APIs..."
gcloud services enable \
    artifactregistry.googleapis.com \
    iamcredentials.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    compute.googleapis.com

# 4. Create Artifact Registry
echo "🔄 Checking Artifact Registry..."
if ! gcloud artifacts repositories describe $REPO_NAME --location=$REGION &>/dev/null; then
    echo "   Creating '$REPO_NAME' in $REGION..."
    gcloud artifacts repositories create $REPO_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Lazy Chef Docker Repository"
else
    echo "   ✅ Registry '$REPO_NAME' already exists."
fi

# 5. Create Service Account (if missing)
echo "🔄 Checking Service Account..."
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT &>/dev/null; then
    echo "   Creating service account 'github-deployer'..."
    gcloud iam service-accounts create github-deployer \
        --display-name="GitHub Actions Deployer"
else
    echo "   ✅ Service Account '$SERVICE_ACCOUNT' already exists."
fi

# 6. Grant Permissions (Idempotent)
echo "🔄 Granting IAM roles..."
ROLES=(
    "roles/run.admin"
    "roles/storage.admin"
    "roles/artifactregistry.writer"
    "roles/iam.serviceAccountUser"
    "roles/cloudsql.client"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="$role" \
        --condition=None &>/dev/null
done

# 7. Workload Identity Federation (The Tricky Part)
echo "🔄 Configuring Workload Identity Federation..."

# Create Pool if missing
if ! gcloud iam workload-identity-pools describe $POOL_NAME --location="global" &>/dev/null; then
    gcloud iam workload-identity-pools create $POOL_NAME \
        --location="global" \
        --display-name="GitHub Actions Pool"
fi

# Create Provider if missing
if ! gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
    --location="global" \
    --workload-identity-pool=$POOL_NAME &>/dev/null; then
    
    gcloud iam workload-identity-pools providers create $PROVIDER_NAME \
        --location="global" \
        --workload-identity-pool=$POOL_NAME \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --issuer-uri="https://token.actions.githubusercontent.com"
fi

# 8. Bind the NEW Repo to the Service Account
echo "🔄 Binding GitHub Repo '$GITHUB_REPO' to Service Account..."
# This command allows the specific GitHub repo to impersonate the service account
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT" \
    --project="$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

echo ""
echo "✅ SUCCESS! Infrastructure is ready."
echo ""
echo "👇 YOU MUST NOW MANUALLY ADD THESE SECRETS TO GITHUB ($GITHUB_REPO):"
echo "---------------------------------------------------"
echo "PROJECT_ID:            $PROJECT_ID"
echo "WIF_PROVIDER:          projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/providers/$PROVIDER_NAME"
echo "WIF_SERVICE_ACCOUNT:   $SERVICE_ACCOUNT"
echo "---------------------------------------------------"