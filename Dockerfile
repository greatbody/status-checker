# Use the official Python image from the Docker Hub
FROM python:3.13.2-slim

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY ./app /app

# Expose the port the app runs on
EXPOSE 8243

# Command to run the application
CMD ["python", "app.py"]
