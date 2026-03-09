FROM continuumio/miniconda3

WORKDIR /app

# Copy environment file
COPY environment.yml .

# Create conda environment
RUN conda env create -f environment.yml

# Activate environment automatically
SHELL ["conda", "run", "-n", "glance-app-flask-endpoint", "/bin/bash", "-c"]

# Copy app source
COPY . .

EXPOSE 5000

CMD ["conda", "run", "--no-capture-output", "-n", "glance-app-flask-endpoint", "python", "flask_api.py"]