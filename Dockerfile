FROM python:3.7-slim-buster
COPY requirements.txt /requirements.txt
pip install -r /requirements.txt
COPY issuebot.py /issuebot.py
ENTRYPOINT ["python", "/issuebot.py"]
