FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data
ENV SQLALCHEMY_DATABASE_URI=sqlite:////app/data/nav.db

EXPOSE 5000

CMD ["python", "app.py"]
