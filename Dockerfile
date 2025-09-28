# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
# PYTHONDONTWRITEBYTECODE: prevents python from writing .pyc files
# PYTHONUNBUFFERED: allows logs to be sent straight to the terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies that might be required by some Python packages
# For example, build-essential for C extensions.
# This is a good practice, though may not be strictly necessary for all our current dependencies.
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# We copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Define the command to run the application
# We use Gunicorn as the production server, with Uvicorn workers for ASGI.
# The number of workers (-w 4) is a common starting point, but should be
# adjusted based on the server's CPU cores.
# We bind to 0.0.0.0 to make it accessible from outside the container.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "4", "-b", "0.0.0.0:8000", "eia.main:app"]