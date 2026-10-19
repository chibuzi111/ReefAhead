FROM python:3.14-slim
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY . .
ENV CLIMATE_DATA_DIR=/app/data OMP_NUM_THREADS=4
EXPOSE 8765
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8765"]
