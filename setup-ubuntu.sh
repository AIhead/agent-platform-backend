#!/bin/bash
# Agent Platform — Ubuntu 24.04 LTS Setup Script
set -e

echo "=== Installing system dependencies ==="
sudo apt update
sudo apt install -y python3-pip python3-venv postgresql postgresql-16-pgvector build-essential python3-dev

echo ""
echo "=== Setting up PostgreSQL ==="
sudo -u postgres psql -c "CREATE USER agent WITH PASSWORD 'agent123';" 2>/dev/null || true
sudo -u postgres psql -c "CREATE DATABASE agent_platform OWNER agent;" 2>/dev/null || true
sudo -u postgres psql -d agent_platform -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
echo "Database ready."

echo ""
echo "=== Setting up Python ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Initializing data ==="
cp .env.example .env 2>/dev/null || true
echo "Edit .env with your DEEPSEEK_API_KEY before running!"
python3 seed_data.py

echo ""
echo "=== Done! ==="
echo "Start: source venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "Docs: http://localhost:8000/docs"
