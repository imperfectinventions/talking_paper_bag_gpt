FROM python:3.9.18-bullseye
LABEL Maintainer="imperfect.inventions"

RUN apt-get update -qq && apt-get install ffmpeg -y
RUN apt install python3-libgpiod -y

RUN mkdir -p /home/paper_bag_gpt
COPY ./ /home/paper_bag_gpt

ENV PYTHONPATH $PYTHONPATH:/usr/lib/python3/dist-packages

WORKDIR /home/paper_bag_gpt
RUN python --version
RUN python -m pip install --upgrade pip
RUN python -m pip install -r ./requirements.txt
CMD ["python", "./main.py"]
