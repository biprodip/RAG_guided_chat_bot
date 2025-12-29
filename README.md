# RAG Guided Chatbot — AWS EC2 + ECR + GitHub Actions (Self-Hosted Runner)

This guide explains how to deploy the **RAG Guided Chatbot** using:

- **EC2** (a virtual machine) to run the application container  
- **ECR** (Elastic Container Registry) to store the Docker image  
- **GitHub Actions** with a **self-hosted runner** installed on the EC2 instance for CI/CD

---

## 1 Create an IAM User (for GitHub Actions)

Create an IAM user and attach permissions so GitHub Actions can push images to ECR and manage EC2-related operations.

### Attach these policies (as used here)
1. `AmazonEC2ContainerRegistryFullAccess`  
2. `AmazonEC2FullAccess`

> **Note:** For production, prefer **least-privilege** policies. The above is fine for a simple working setup.

### Create Access Keys
Go to: **IAM User → Security credentials → Create access key**  
- Use case: **Command Line Interface (CLI)**  
Save:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

---

## 2 Create an ECR Repository

1. Open AWS Console → search **ECR**
2. Create a new repository for your app
3. Copy and save the repository URI

Example:
```
287223951947.dkr.ecr.ap-southeast-2.amazonaws.com/rag-guided-chatbot

```

---

## 3 Launch an EC2 Instance (to run the Docker container)

1. Open AWS Console → search **EC2**
2. Launch Instance:
   - OS: **Ubuntu**
   - Instance type: choose a suitable size (e.g., **8 GB RAM**)
   - Storage: **20 GB**
   - Key pair: create/select one
3. Launch the instance
4. Connect using the **public IP** (SSH)

---

## 4 Install Docker on the EC2 Instance

On the EC2 machine:

### Optional updates
```bash
sudo apt-get update -y
sudo apt-get upgrade -y
````

## Install Docker (required)

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
newgrp docker
```

Verify:

```bash
docker --version
```

---

## 5 Add a GitHub Self-Hosted Runner on EC2

In your GitHub repo:

**Settings → Actions → Runners → New self-hosted runner → Linux**

GitHub will provide commands like:

1. Download runner
2. Configure runner (`./config.sh ...`)
3. Start runner (`./run.sh`)

Run those commands **on your EC2 instance** to connect the runner to GitHub.

> **Tip:** Prefer installing the runner as a **service** so it starts automatically after reboot.

---

## 6 Add GitHub Secrets

In GitHub repo:

**Settings → Secrets and variables → Actions → New repository secret**

Add:

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`
* `AWS_DEFAULT_REGION`
* `ECR_REPO`
* `PINECONE_API_KEY`
* `OPENAI_API_KEY`

---

## 7 CI/CD Workflow

1. Add workflow file:

   * `.github/workflows/cicd.yaml`
2. Push changes to GitHub
3. Check GitHub Actions → confirm workflow runs successfully

---

## 8 Open Required Ports on EC2 (Inbound Rules)

To access your running web app:

EC2 → **Security Groups** → **Edit inbound rules** → Add rule(s):

* Type: **Custom TCP**
* Port: (your app port, e.g., `8000` / `8501` / `80`)
* Source: `0.0.0.0/0` (public) or restrict to your IP for better security

---

# Deployment Summary (What Happens)

1. **Build** the Docker image from your source code
2. **Push** the Docker image to **ECR**
3. **Launch** the EC2 instance
4. **Pull** the Docker image from ECR into EC2
5. **Run** the Docker container in EC2