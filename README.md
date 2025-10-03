# BitShred Final Project - Fixed Build

This project is a Flask application that integrates ingestion, otolith and eDNA services with MongoDB and provides visualization using Chart.js and Plotly.

## Deployment (Render)
- Add environment variables in Render: MONGO_URI, MONGO_DB
- Deploy using Dockerfile (Render Docker service) or use Procfile for non-Docker

## Local dev
- Create a .env with MONGO_URI and MONGO_DB or export env vars
- docker compose up --build
