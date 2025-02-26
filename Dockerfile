FROM python:3.12-slim

WORKDIR /app

COPY . ./

# install python dependencies
RUN pip3 install -r requirements.txt

CMD ["python", "main.py"]
