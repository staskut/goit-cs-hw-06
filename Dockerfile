FROM python:3.8
WORKDIR /app
COPY ./app /app
RUN pip install pymongo
EXPOSE 3000 5050
CMD ["python", "app/main.py"]
