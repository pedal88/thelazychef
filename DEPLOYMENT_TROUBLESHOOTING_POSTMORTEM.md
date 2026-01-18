# Deployment Troubleshooting Journey - January 16, 2026

## Executive Summary

After 2+ hours of troubleshooting, we successfully deployed the Build Your Meal application to Google Cloud Run. The deployment ultimately succeeded using **Google Cloud Shell** instead of the local `gcloud` CLI, which had persistent issues due to OneDrive integration and process deadlocks.

**Final Deployment URL:** https://bym-app-287448924512.us-central1.run.app

---

## Initial Context

### Starting Point
- **Project Location:** `/Users/pad/Library/CloudStorage/OneDrive-TV2AS/p_ai/bym2026`
- **Deployment Script:** `scripts/deploy.sh` (bash-based)
- **Target:** Google Cloud Run with Cloud SQL connection
- **Project Size:** ~507MB (including `.git`, `venv`, `google-cloud-sdk`)

### First Deployment Attempt
**Command:** `./scripts/deploy.sh bym-app-287448924512`

**Result:** Hung indefinitely at "Building Container Image..." step

**Duration:** 30+ minutes with no progress

---

## Troubleshooting Timeline

### Phase 1: Size Optimization (6:46 AM - 7:12 AM)

#### Problem Identified
- Project directory was 507MB
- Suspected large files causing slow upload

#### Actions Taken
1. **Analyzed directory size:**
   ```bash
   du -sh .  # Result: 507M
   ```

2. **Identified culprits:**
   - `.git` folder: 422MB
   - `google-cloud-cli-darwin-arm.tar.gz`: 55MB
   - `venv/`: 32MB
   - `google-cloud-sdk/`: 50MB

3. **Updated `.gcloudignore`:**
   ```
   *.tar.gz
   *.zip
   .DS_Store
   ```

#### Result
- Improvements made but deployment still hung
- **Root cause was deeper than file size**

---

### Phase 2: Smart Deployment Script (7:12 AM - 7:37 AM)

#### Solution Attempt
Created `scripts/smart_deploy.py` with features:
- Pre-flight size checks
- Async build submission
- Live status polling
- Real-time progress dashboard

#### Implementation
```python
# Key features:
- check_project_size()  # Warns if >200MB
- monitor_build()       # Polls build status every 3s
- Live timer display
```

#### Result
- Script created successfully
- **Still hung at "Submitting Build (Async)..." step**
- No progress after 5+ minutes

---

### Phase 3: OneDrive Investigation (7:23 AM - 7:51 AM)

#### Discovery
- User's internet speed: 23.3 Mbps upload (should be fast enough)
- Expected upload time for 60MB: ~20 seconds
- Actual time: **Indefinite hang**

#### Hypothesis
OneDrive was intercepting file operations, causing:
1. File sync checks on every read
2. Throttling of rapid file access
3. Potential deadlocks between `gcloud` and OneDrive

#### Actions Taken
1. **Attempted project migration:**
   ```bash
   cp -r /Users/pad/Library/CloudStorage/OneDrive-TV2AS/p_ai/bym2026 ~/Projects/
   ```
   - **Result:** Copy itself was slow (OneDrive downloading files)

2. **Used `rsync` with exclusions:**
   ```bash
   rsync -av --exclude ".git" --exclude "venv" \
     --exclude "google-cloud-sdk" \
     /Users/pad/Library/CloudStorage/OneDrive-TV2AS/p_ai/bym2026/ \
     ~/Projects/bym2026/
   ```
   - **Result:** Stuck copying `static/pantry/` (1426 image files)

---

### Phase 4: Gcloud CLI Deadlock (7:51 AM - 8:28 AM)

#### Critical Discovery
Multiple `gcloud` commands were hanging system-wide:

```bash
ps -ef | grep gcloud
# Found 5 zombie processes:
- PID 10870: gcloud builds submit (1+ hour old)
- PID 93668: gcloud builds list (1+ hour old)
- PID 99635: gcloud builds list
- PID 99845: gcloud builds list
- PID 10066: gcloud version (hung on simple command!)
```

#### Diagnosis
- Even `gcloud version` (millisecond command) hung indefinitely
- Indicated **fundamental CLI corruption/deadlock**
- Likely caused by:
  1. OneDrive file locking
  2. Corrupted gcloud config cache
  3. Multiple concurrent operations creating race conditions

#### Attempted Fixes
1. **Killed zombie processes:**
   ```bash
   kill -9 10870 93668 99635 99845 10066
   ```

2. **Modified deployment script** to stream output:
   - Changed from async to synchronous build
   - Added `capture_output=False` to show native progress

3. **Result:** Still hung - CLI was fundamentally broken

---

### Phase 5: Cloud Shell Solution (8:28 AM - 9:07 AM)

#### Strategy Shift
Abandoned local `gcloud` CLI entirely in favor of browser-based Cloud Shell.

#### Implementation Steps

**1. Create Deployment Package**
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
- **Result:** 17MB package (down from 507MB)

**2. Upload to Cloud Shell**
- Opened https://console.cloud.google.com
- Clicked Cloud Shell icon (terminal button)
- Used Upload menu → Selected `bym2026-deploy.tar.gz`
- **Upload completed in seconds**

**3. Extract and Deploy**
```bash
mkdir bym2026 && cd bym2026
tar -xzf ../bym2026-deploy.tar.gz

gcloud config set project gen-lang-client-0770637546

gcloud run deploy bym-app \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances gen-lang-client-0770637546:us-central1:buildyourmeal \
  --set-env-vars "DB_BACKEND=cloudsql,STORAGE_BACKEND=gcs,GCS_BUCKET_NAME=buildyourmeal-assets,INSTANCE_CONNECTION_NAME=gen-lang-client-0770637546:us-central1:buildyourmeal,DB_USER=postgres,DB_NAME=postgres,FLASK_DEBUG=0,DB_PASS=***,GOOGLE_API_KEY=***"
```

**4. Success!**
```
Building Container... done
Creating Revision... done
Routing traffic... done
Service URL: https://bym-app-287448924512.us-central1.run.app
```

**Total deployment time:** ~10 minutes (expected duration)

---

## Root Causes Identified

### Primary Issue: OneDrive + Gcloud Incompatibility
1. **File Locking:** OneDrive intercepts file reads to check sync status
2. **Throttling:** Rapid file access (like `gcloud` archiving) triggers rate limiting
3. **Deadlocks:** Concurrent operations between OneDrive and gcloud create race conditions

### Secondary Issue: Gcloud CLI Corruption
1. **Zombie Processes:** Multiple hung gcloud commands held locks
2. **Config Cache:** Potentially corrupted state files
3. **No Recovery:** Even after killing processes, CLI remained broken

### Environmental Factors
- **Project Location:** OneDrive-synced directory
- **File Count:** 1400+ images in `static/pantry/`
- **Network:** Despite good bandwidth, local CLI couldn't complete uploads

---

## Solutions That Worked

### Immediate Solution: Cloud Shell
✅ **Bypasses all local issues**
- No OneDrive interference
- Pre-authenticated Google environment
- Fast, reliable Google network
- Built-in gcloud (always up-to-date)

### Long-Term Recommendations

1. **Move Project Out of OneDrive**
   ```bash
   # Recommended location:
   ~/Projects/bym2026  # or ~/Development/bym2026
   ```

2. **Exclude Large Directories from Sync**
   - Add `.git/`, `venv/`, `node_modules/` to OneDrive exclusions

3. **Use Cloud Shell for Deployments**
   - More reliable than local CLI
   - No dependency on local environment
   - Faster uploads from Google's network

4. **Automated Deployment Package Creation**
   ```bash
   # Create deployment-ready archive:
   tar -czf deploy.tar.gz \
     --exclude='.git' \
     --exclude='venv' \
     --exclude='static/pantry' \
     --exclude='static/recipes' \
     .
   ```

---

## Solutions That Didn't Work

### ❌ Updating `.gcloudignore`
- **Why it failed:** Files were already being scanned before exclusion rules applied
- **Lesson:** Ignore files help with upload size, not with local file access issues

### ❌ Smart Deployment Script with Monitoring
- **Why it failed:** Script couldn't fix underlying CLI deadlock
- **Lesson:** Better UX doesn't solve infrastructure problems

### ❌ Killing Zombie Processes
- **Why it failed:** CLI state was corrupted beyond simple process cleanup
- **Lesson:** Sometimes a full environment reset (Cloud Shell) is faster than debugging

### ❌ Moving Project to Local Directory
- **Why it failed:** OneDrive still had to download files before they could be copied
- **Lesson:** OneDrive sync is bidirectional and unavoidable for synced folders

### ❌ Rsync with Exclusions
- **Why it failed:** Still had to traverse OneDrive-synced directories
- **Lesson:** Any local operation on OneDrive files will be slow

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **Total Troubleshooting Time** | 2 hours 21 minutes |
| **Deployment Attempts** | 8+ |
| **Final Package Size** | 17MB (from 507MB) |
| **Actual Deployment Time** | ~10 minutes |
| **Upload Speed (Cloud Shell)** | Seconds |
| **Upload Speed (Local CLI)** | Infinite (hung) |

---

## Lessons Learned

### Technical Insights

1. **OneDrive is incompatible with development workflows**
   - File locking interferes with build tools
   - Sync overhead makes operations unpredictable
   - Better suited for documents, not code repositories

2. **Cloud Shell is more reliable than local CLI**
   - No local environment issues
   - Pre-configured and authenticated
   - Faster network to Google services

3. **Zombie processes indicate deeper issues**
   - Don't just kill processes - investigate why they hung
   - Multiple hung instances suggest systemic problem

### Process Improvements

1. **Start with Cloud Shell for production deployments**
   - Saves time debugging local issues
   - Consistent environment across team members

2. **Keep deployment packages small**
   - Exclude development artifacts (`.git`, `venv`)
   - Exclude static assets served from cloud storage

3. **Document working solutions immediately**
   - Create `DEPLOY_VIA_CLOUD_SHELL.md` for future reference
   - Capture exact commands that worked

---

## Future Deployment Workflow

### Recommended Process

1. **Develop Locally** (outside OneDrive)
   ```bash
   cd ~/Projects/bym2026
   # Make changes, test locally
   ```

2. **Create Deployment Package**
   ```bash
   tar -czf bym2026-deploy.tar.gz \
     --exclude='.git' \
     --exclude='venv' \
     --exclude='google-cloud-sdk' \
     --exclude='*.tar.gz' \
     --exclude='__pycache__' \
     --exclude='static/pantry' \
     --exclude='static/recipes' \
     .
   ```

3. **Deploy via Cloud Shell**
   - Open https://console.cloud.google.com
   - Activate Cloud Shell
   - Upload `bym2026-deploy.tar.gz`
   - Extract and run deployment command

4. **Verify Deployment**
   - Check service URL
   - Test critical functionality
   - Monitor logs for errors

### Alternative: CI/CD Pipeline
Consider setting up GitHub Actions or Cloud Build triggers for automated deployments:
- Push to `main` branch → automatic deployment
- No manual intervention required
- Consistent, repeatable process

---

## Conclusion

After extensive troubleshooting, the deployment succeeded by **changing the deployment environment** rather than fixing the local environment. This highlights an important principle: **sometimes the fastest solution is to change the approach entirely** rather than debugging a broken tool.

The Cloud Shell solution is now documented and can be used for all future deployments, providing a reliable, fast, and consistent deployment process.

**Deployment Status:** ✅ **SUCCESSFUL**  
**Service URL:** https://bym-app-287448924512.us-central1.run.app  
**Revision:** bym-app-00016-h5f
