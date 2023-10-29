FROM python:3.9.18

RUN apt-get -y update
RUN apt-get -y install ffmpeg

WORKDIR /app

COPY . .

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt
CMD python -u ./bot.py