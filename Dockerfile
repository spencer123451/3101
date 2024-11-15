FROM python:3.12-slim
RUN apt-get update && apt-get install -y git
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
WORKDIR /app/streamlit
CMD ["python", "app.py"]
