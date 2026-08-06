# 3.13 to match the local venv. audioop-lts (in requirements.txt) declares
# Requires-Python >=3.13, so this build fails outright on 3.11.
FROM python:3.13-bookworm

RUN apt-get -y update \
 && apt-get -y install --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first so editing bot.py doesn't reinstall the whole dep tree.
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip \
 && python3 -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD python -u ./bot.py
