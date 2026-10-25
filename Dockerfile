# Two stages. The Python packages are built in the first, which changes only with requirements.txt (or a new
# base image); the second refreshes the OS packages daily and copies the packages in. The daily refresh used to
# rebuild the packages too, which made the first deploy of the day two to three minutes slower.

# --- The Python packages ---
FROM python:3.13-slim AS packages

# gcc and python3-dev for any package that has to be compiled; not in the image that runs
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/packages -r requirements.txt

# --- The image that runs ---
# Use the official Python executable using the slim version for a smaller image size
FROM python:3.13-slim

# Prevent Python from buffering stdout and stderr (for logging)
ENV PYTHONUNBUFFERED=1

# APT_REFRESH (the date, from CI) makes the cached layer refresh daily, so OS security fixes arrive within a day
ARG APT_REFRESH=none
RUN echo "OS packages as of ${APT_REFRESH}" && apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# The packages from the first stage; pip and setuptools are left out, they are not used and Trivy flags them
COPY --from=packages /packages /usr/local
RUN rm -rf /usr/local/lib/python3.13/site-packages/pip \
           /usr/local/lib/python3.13/site-packages/pip-*.dist-info \
           /usr/local/lib/python3.13/site-packages/setuptools \
           /usr/local/lib/python3.13/site-packages/setuptools-*.dist-info \
           /usr/local/lib/python3.13/site-packages/pkg_resources \
           /usr/local/lib/python3.13/ensurepip

# Create a non-root user for security, and the app's folder, owned by it as before
RUN groupadd -r appuser && useradd -r -g appuser appuser && mkdir /app && chown appuser:appuser /app

# Set the working directory
WORKDIR /app

# The application code, owned by the non-root user (in the copy, not a chown of every file afterwards)
COPY --chown=appuser:appuser . .

# Switch to the non-root user
USER appuser

# Expose the port (Cloud Run sets the PORT env var, defaulting to 8080)
# Note: This is documentation only, the app must bind to the environment variable
EXPOSE 8080

# Run gunicorn
# 1 worker, 8 threads is a good starting point for I/O bound Flask apps on Cloud Run
# 0 timeout is required by Cloud Run to avoid killing long connections prematurely
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
