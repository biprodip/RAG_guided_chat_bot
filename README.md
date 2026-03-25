# RAG Guided Medical Chatbot

A  **Retrieval-Augmented Generation (RAG)** based chatbot specialised for medical question-answering. The system retrieves semantically relevant passages from domain-specific documents and synthesises concise, grounded answers using OpenAI's GPT-4o-mini. The updated version with hybrid retrival, reranking and other improvement will be published soon. 

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Local)](#quick-start-local)
- [Indexing New Documents](#indexing-new-documents)
- [Configuration Reference](#configuration-reference)
- [API Reference](#api-reference)
- [Deployment (AWS EC2 + ECR + GitHub Actions)](#deployment-aws-ec2--ecr--github-actions)
- [CI/CD Pipeline](#cicd-pipeline)
- [Tech Stack](#tech-stack)

---

## Overview

The chatbot answers medical questions by:

1. **Retrieving** the top-k most relevant text chunks from a Pinecone vector index built from PDF documents.
2. **Generating** a concise two-sentence answer conditioned on the retrieved context using GPT-4o-mini.

This RAG approach keeps responses grounded in the source material and reduces hallucination compared to prompting a bare LLM.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         User Browser                         │
│              GET /  →  chat.html (Bootstrap UI)              │
│              POST /get  →  { msg: "..." }                    │
└────────────────────────────┬─────────────────────────────────┘
                             │ AJAX
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                      Flask Application                        │
│                          app.py                              │
│                                                              │
│  ┌──────────────────────┐    ┌───────────────────────────┐  │
│  │  PineconeVectorStore  │    │    ChatOpenAI (gpt-4o-mini)│  │
│  │  (Retriever, k=2)    │    │    + ChatPromptTemplate    │  │
│  └──────────┬───────────┘    └────────────┬──────────────┘  │
│             │  top-k docs                 │                  │
│             └──────────────┬──────────────┘                  │
│                            ▼                                 │
│              create_stuff_documents_chain                    │
│              create_retrieval_chain                          │
│                            │                                 │
│                            ▼  answer string                  │
└──────────────────────────────────────────────────────────────┘

Offline indexing (store_index.py):
  PDF files → PyPDFLoader → text chunks (500 chars, 20 overlap)
            → HuggingFace all-MiniLM-L6-v2 (384-dim embeddings)
            → Pinecone serverless index (cosine similarity, AWS us-east-1)
```

---

## Project Structure

```
RAG_guided_chat_bot/
├── .github/
│   └── workflows/
│       └── cicd.yaml          # GitHub Actions CI/CD pipeline
├── src/
│   ├── __init__.py
│   ├── helper.py              # PDF loading, chunking, embedding helpers
│   └── prompt.py              # System prompt for the medical assistant
├── data/
│   └── microbiome_in_cancer.pdf   # Sample source document
├── static/
│   └── style.css              # Chat UI styles
├── templates/
│   └── chat.html              # Jinja2 chat interface
├── app.py                     # Flask application entry point
├── store_index.py             # One-time vector store initialisation script
├── requirements.txt           # Python dependencies
├── setup.py                   # Package metadata
├── Dockerfile                 # Container image definition
└── .gitignore
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| Docker | 20.10+ (for containerised deployment) |
| Pinecone account | Free tier supported |
| OpenAI API key | GPT-4o-mini access required |

---

## Quick Start (Local)

### 1. Clone the repository

```bash
git clone <repo-url>
cd RAG_guided_chat_bot
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```dotenv
PINECONE_API_KEY=your_pinecone_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 5. Index your documents (first-time setup)

Place PDF files inside the `data/` directory, then run:

```bash
python store_index.py
```

This creates (or reuses) a Pinecone index named `rag-guided-chatbot` and uploads all document embeddings.

### 6. Start the application

```bash
python app.py
```

Open your browser at **http://localhost:8080**.

---

## Indexing New Documents

To add or replace source documents:

1. Copy your PDF files into `data/`.
2. Re-run `python store_index.py`.
   The script checks whether the index already exists; if it does it will upsert the new vectors alongside the existing ones.

> **Note:** If you want a clean re-index, delete the Pinecone index from the console before running `store_index.py`.

---

## Configuration Reference

| Variable | Source | Description |
|---|---|---|
| `PINECONE_API_KEY` | `.env` / GitHub Secret | Pinecone authentication key |
| `OPENAI_API_KEY` | `.env` / GitHub Secret | OpenAI authentication key |
| `AWS_ACCESS_KEY_ID` | GitHub Secret | AWS credentials for ECR/EC2 |
| `AWS_SECRET_ACCESS_KEY` | GitHub Secret | AWS credentials for ECR/EC2 |
| `AWS_DEFAULT_REGION` | GitHub Secret | AWS region (e.g. `us-east-1`) |
| `ECR_REPO` | GitHub Secret | Full ECR repository URI |

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, CPU)
**LLM:** `gpt-4o-mini`
**Pinecone index:** `rag-guided-chatbot` · cosine similarity · serverless (AWS `us-east-1`)
**Retriever:** similarity search, `k=2`
**Chunk size:** 500 characters · overlap 20 characters

---

## API Reference

### `GET /`

Returns the chat web interface (`chat.html`).

---

### `POST /get`

Processes a user message and returns the chatbot's answer.

**Request (form-encoded)**

| Field | Type | Description |
|---|---|---|
| `msg` | `string` | The user's question |

**Response**

| Type | Description |
|---|---|
| `text/plain` | Concise answer string (≤ 2 sentences) |

**Example**

```bash
curl -X POST http://localhost:8080/get \
  -d "msg=What+is+the+role+of+microbiome+in+cancer?"
```

```
The gut microbiome influences cancer development by modulating immune responses
and producing metabolites that can either promote or inhibit tumour growth.
Dysbiosis has been associated with several cancers including colorectal cancer.
```

---

## Deployment (AWS EC2 + ECR + GitHub Actions)

### Step 1 — Create an IAM User

Create an IAM user and attach the following policies:

- `AmazonEC2ContainerRegistryFullAccess`
- `AmazonEC2FullAccess`

> For production, apply least-privilege policies. The above is sufficient for a basic working setup.

Generate access keys under **IAM → Security credentials → Create access key (CLI use case)** and save `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

### Step 2 — Create an ECR Repository

1. Open the AWS Console → search **ECR**.
2. Create a new private repository (e.g., `rag-guided-chatbot`).
3. Copy the repository URI (e.g., `123456789.dkr.ecr.us-east-1.amazonaws.com/rag-guided-chatbot`).

### Step 3 — Launch an EC2 Instance

| Setting | Recommended value |
|---|---|
| OS | Ubuntu 22.04 LTS |
| Instance type | t3.large (8 GB RAM) or larger |
| Storage | 20 GB |

Connect to the instance via SSH using its public IP.

### Step 4 — Install Docker on EC2

```bash
sudo apt-get update -y && sudo apt-get upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker
docker --version   # verify
```

### Step 5 — Install the GitHub Self-Hosted Runner

In your GitHub repository go to **Settings → Actions → Runners → New self-hosted runner → Linux** and follow the provided commands on the EC2 instance. Install the runner as a service for automatic restart:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

### Step 6 — Add GitHub Secrets

**Settings → Secrets and variables → Actions → New repository secret**

Add all keys listed in the [Configuration Reference](#configuration-reference).

### Step 7 — Open Inbound Port

EC2 → **Security Groups → Edit inbound rules** → add Custom TCP rule for port **8080** from `0.0.0.0/0`.

---

## CI/CD Pipeline

The pipeline defined in [.github/workflows/cicd.yaml](.github/workflows/cicd.yaml) runs on every push to `main`.

```
Push to main
    │
    ▼
[Job 1: Continuous-Integration]  (ubuntu-latest)
    ├── Checkout code
    ├── Configure AWS credentials
    ├── Login to Amazon ECR
    ├── Build Docker image (tagged :latest)
    └── Push image to ECR
    │
    ▼
[Job 2: Continuous-Deployment]  (self-hosted EC2 runner)
    ├── Checkout code
    ├── Configure AWS credentials
    ├── Login to ECR
    ├── Pull latest image from ECR
    └── Run container on port 8080 with API keys injected
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Flask 3.1 |
| LLM | OpenAI GPT-4o-mini via LangChain |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace) |
| Vector database | Pinecone (serverless) |
| RAG orchestration | LangChain 0.3 |
| Document parsing | PyPDF |
| Containerisation | Docker (python:3.10-slim-buster) |
| CI/CD | GitHub Actions + AWS ECR + EC2 self-hosted runner |
| Frontend | Bootstrap 4, jQuery AJAX |
