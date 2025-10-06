FROM python:3.11-slim

# Cài lib hệ thống cần cho pyodbc, cffi, cryptography
RUN apt-get update && apt-get install -y \
    gcc g++ make \
    unixodbc unixodbc-dev \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirement trước để cache
COPY requirements.txt .

# Cài dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install -r requirements.txt

# Copy code
COPY . .

# Expose cổng Flask
EXPOSE 5000

# Run app
CMD ["python","-u","webapp.py"]

ENV PYTHONUNBUFFERED=1