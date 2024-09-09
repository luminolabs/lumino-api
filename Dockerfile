FROM python:3.12-bullseye

# Install essentials
RUN apt update \
	&& apt install -y \
		build-essential \
		ca-certificates \
		curl \
		git \
		libssl-dev \
		software-properties-common

# Work in this folder
WORKDIR /project

# Upgrade pip
RUN python -m pip install --upgrade pip

# Install npm, nodejs, and dependencies for serving the api-specs
RUN apt install -y npm nodejs
RUN npm init -y
RUN npm install express swagger-ui-express yamljs

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy api-specs and service
COPY api-specs api-specs
COPY api-specs.js .

# Copy app configs
COPY app-configs app-configs

# Copy html templates
COPY html html

# Copy src files
COPY src .

# Set Python path
ENV PYTHONPATH=/project