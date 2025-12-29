# RAG_guided_chat_bot

#Create IAM user with direct permission policy

#Policy:

1. AmazonEC2ContainerRegistryFullAccess

2. AmazonEC2FullAccess

Here,

EC2 access : It is virtual machine  

ECR: Elastic container registry to save docker image in aws


Then for the created user, in the security credentials, create access key with  

Use case : Command Line Interface (CLI)


## Then Go to ECR(Search) and Create a repository:


After creation of ECR repo(to save the docker image), copy and save the URI

URI: 287223951947.dkr.ecr.ap-southeast-2.amazonaws.com/rag-guided-chatbot



## Then search find and create EC2 instance (To load and run the docker image)

Launch instance -> provide name -> Ubuntu_OS -> Instance type: 8 GB memory
-> Key pair name -> Configure storage 20GB -> Launch instance

Connect EC2 using a public IP


## Open EC2 and Install docker in EC2 Machine:

#optinal

sudo apt-get update -y

sudo apt-get upgrade

#required

curl -fsSL https://get.docker.com -o get-docker.sh

sudo sh get-docker.sh

sudo usermod -aG docker ubuntu

newgrp docker



## Github Action
Github Project Repo -> Settings -> Actions -> Runner -> New Self Hosted Runner -> Linux

Then Run the given commands to connect Github with EC2 instance

## Save Keys in Github Secrets
Secrets and variables -> actions -> New repository secrets -> Add Keys

1. AWS_ACCESS_KEY_ID
2. AWS_SECRET_ACCESS_KEY
3. AWS_DEFAULT_REGION
4. ECR_REPO
5. PINECONE_API_KEY
6. OPENAI_API_KEY


#Summary: About the deployment

1. Build docker image of the source code

2. Push your docker image to ECR

3. Launch Your EC2 

4. Pull Your image from ECR in EC2

5. Lauch your docker image in EC2