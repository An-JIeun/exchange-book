#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-asia-northeast3}"
DB_INSTANCE="${DB_INSTANCE:-meet-zool-mysql}"
DB_NAME="${DB_NAME:-meet_zool}"
DB_USER="${DB_USER:-meetzool}"
DB_PASS="${DB_PASS:-}"
SERVICE_NAME="${SERVICE_NAME:-meet-zool-api}"

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID is required."
  echo "Example: PROJECT_ID=my-project-id DB_PASS=your-password ./deploy_backend_cloudsql.sh"
  exit 1
fi

if [[ -z "$DB_PASS" ]]; then
  echo "DB_PASS is required."
  echo "Example: PROJECT_ID=my-project-id DB_PASS=your-password ./deploy_backend_cloudsql.sh"
  exit 1
fi

command -v gcloud >/dev/null 2>&1 || { echo "gcloud is required."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required."; exit 1; }

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [[ ! -d "$BACKEND_DIR" ]]; then
  echo "backend directory not found: $BACKEND_DIR"
  exit 1
fi

echo "[1/8] gcloud auth check"
gcloud auth login

echo "[2/8] set project"
gcloud config set project "$PROJECT_ID"

echo "[3/8] enable required services"
gcloud services enable \
  sqladmin.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

echo "[4/8] create Cloud SQL instance if missing"
if gcloud sql instances describe "$DB_INSTANCE" >/dev/null 2>&1; then
  echo "Cloud SQL instance already exists: $DB_INSTANCE"
else
  gcloud sql instances create "$DB_INSTANCE" \
    --database-version=MYSQL_8_0 \
    --cpu=1 \
    --memory=3840MiB \
    --region="$REGION"
fi

echo "[5/8] create database/user if missing"
if gcloud sql databases describe "$DB_NAME" --instance="$DB_INSTANCE" >/dev/null 2>&1; then
  echo "Database already exists: $DB_NAME"
else
  gcloud sql databases create "$DB_NAME" --instance="$DB_INSTANCE"
fi

if gcloud sql users list --instance="$DB_INSTANCE" --format="value(name)" | grep -Fxq "$DB_USER"; then
  echo "User already exists: $DB_USER (password will be updated)"
  gcloud sql users set-password "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASS"
else
  gcloud sql users create "$DB_USER" --instance="$DB_INSTANCE" --password="$DB_PASS"
fi

echo "[6/8] build backend image"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$SERVICE_NAME" "$BACKEND_DIR"

echo "[7/8] deploy Cloud Run"
INSTANCE_CONN="$(gcloud sql instances describe "$DB_INSTANCE" --format='value(connectionName)')"
DATABASE_URL="mysql+pymysql://$DB_USER:$DB_PASS@/$DB_NAME?unix_socket=/cloudsql/$INSTANCE_CONN"

gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/$PROJECT_ID/$SERVICE_NAME" \
  --region "$REGION" \
  --platform managed \
  --allow-unauthenticated \
  --add-cloudsql-instances "$INSTANCE_CONN" \
  --set-env-vars "APP_NAME=$SERVICE_NAME,APP_ENV=prod,DATABASE_URL=$DATABASE_URL"

echo "[8/8] health check"
SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)')"
echo "Service URL: $SERVICE_URL"
HEALTH_URL="$SERVICE_URL/api/health"
echo "Health URL: $HEALTH_URL"
curl -fsSL "$HEALTH_URL" && echo

echo "Done."
