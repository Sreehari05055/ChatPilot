# Dockerfile for Code Sandbox
FROM python:3.11-slim

# Create a non-root user
RUN useradd -m sandboxuser

# Install common data analysis libraries
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    scipy \
    scikit-learn \
    statsmodels \
    openpyxl

# Set working directory
WORKDIR /home/sandboxuser
USER sandboxuser

# Default command
CMD ["python3"]
