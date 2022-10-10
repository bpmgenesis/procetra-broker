FROM tiangolo/uvicorn-gunicorn:python3.8-slim
WORKDIR /server
RUN apt-get update
RUN apt-get install graphviz -y
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install certifi
COPY src/ .
CMD ["python", "./main.py"]