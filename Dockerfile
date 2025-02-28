# Use official Python image as base
FROM python:3.9-slim

# Set a non-root user for security
RUN useradd -m trailmark
USER trailmark

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY --chown=trailmark:trailmark requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the script into the container
COPY --chown=trailmark:trailmark trailmark.py /app/trailmark.py

# Define the command-line interface
ENTRYPOINT ["python", "/app/trailmark.py"]