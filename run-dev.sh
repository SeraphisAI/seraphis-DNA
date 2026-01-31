#!/usr/bin/env bash
set -euo pipefail
cd infra
docker compose up -d --build
