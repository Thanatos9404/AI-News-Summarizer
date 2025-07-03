# Use an official Python runtime as a parent image
# Using python:3.12-slim-buster for Python 3.12
FROM python:3.12-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for pyttsx3 (might need more for your specific setup)
# These are common dependencies for pyttsx3, espeak, and potential audio/media handling.
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    espeak \
    ffmpeg \
    # Clean up APT cache to reduce image size
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the working directory
# Make sure your requirements.txt is in the same directory as this Dockerfile
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# --no-cache-dir reduces the size of the Docker image by not storing pip's cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy your Streamlit application and any necessary files
# Assuming ai_news.py is in the root of your project directory
COPY ai_news.py .
# Important: Do NOT copy .env or client_secrets.json directly.
# You will manage environment variables directly on Vercel.

# Expose the port that Streamlit runs on
EXPOSE 8501

# Define the command to run your Streamlit app
# --server.port 8501: Ensures Streamlit runs on this port inside the container.
# --server.enableCORS false --server.enableXsrfProtection false: Sometimes needed for Dockerized Streamlit behind proxies like Vercel.
# Be aware of the security implications if this app is publicly accessible and handles sensitive user input.
CMD ["streamlit", "run", "ai_news.py", "--server.port", "8501", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"]