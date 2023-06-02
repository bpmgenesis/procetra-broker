FROM tiangolo/uvicorn-gunicorn:python3.9-slim
WORKDIR /server
RUN apt-get update
RUN apt-get install graphviz -y
COPY deps.txt .
RUN pip install -r deps.txt
RUN pip install certifi
COPY src/ .
CMD ["python", "./main.py"]