# Base image with CUDA 12.1 and Python 3.9
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Avoid buffering
ENV PYTHONUNBUFFERED=1

# Install system packages and Python 3.9
RUN apt-get update && apt-get install -y \
    python3.9 python3.9-distutils python3-pip ffmpeg curl git gcc \
    && ln -sf python3.9 /usr/bin/python3 \
    && ln -sf pip3 /usr/bin/pip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install PyTorch with CUDA support (from PyTorch stable index)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5045

# Start the app with longer timeout for processing
CMD ["gunicorn", "--bind", "0.0.0.0:5045", "--timeout", "300", "app:app"]
