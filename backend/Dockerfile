# backend/Dockerfile
# 1. Start from an official slim Python image
FROM python:3.11-slim

# 2. Set a working directory inside the container
WORKDIR /app

# 3. Copy ONLY the requirements file first (layer caching trick)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the application code
COPY . .

# 5. Tell Docker which port the app will listen on
EXPOSE 8000

# 6. The command that runs when the container starts
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
