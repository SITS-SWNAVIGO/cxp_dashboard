FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies for MySQL and health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy all your files into the container
COPY . .

# Install Python libraries from your requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Expose the port Streamlit uses
EXPOSE 8501

# Start the application
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
