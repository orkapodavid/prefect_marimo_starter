# Deployment Guide

This document describes how to deploy the Prefect + Marimo workflows to a Windows Server 2019 environment.

## Target Environment
- Windows Server 2019
- Python 3.11/3.12
- Air-gapped (No internet access)

## Deployment Steps

### 1. Prepare Packages (Internet-connected machine)
Run the following script to download all dependencies:
```powershell
.\scripts\windows\download-packages.ps1
```
This generates an `offline-packages/` folder.

### 2. Transfer Code and Packages
Copy the entire repository (including `offline-packages/`) to the target server via USB or internal network.

### 3. Server Setup
On the target server, run the setup script:
```powershell
.\scripts\windows\setup-server.ps1
```
This will:
- Create a virtual environment.
- Install packages from the `offline-packages` folder.
- Initialize basic directories.

### 4. Configure Environment
Create a `.env` file in the root directory based on `.env.example`.
Update `PREFECT_API_URL` and `DATABASE_URL`.

### 5. Install Services
Install the Prefect server and worker as Windows services:
```powershell
.\scripts\windows\install-server-service.ps1
.\scripts\windows\install-worker-service.ps1 -Environment prod
```

### 6. Deploy Workflows
Run the deployment script:
```powershell
.\scripts\windows\deploy.ps1 -Environment prod
```
