FROM ubuntu:20.04
 
# Save ourselves being prompted by tzdata
ARG DEBIAN_FRONTEND=noninteractive
 
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3.8-venv python3.8-distutils git
RUN apt-get install -y python3-pip
 
RUN ln -s /usr/bin/python3.8 /usr/bin/python
 
RUN git clone https://github.com/Chia-Network/chia-blockchain.git /opt/chia-blockchain
COPY . /opt/chia-blockchain
WORKDIR /opt/chia-blockchain
RUN python3.8 -m pip install wheel requests prometheus-client
RUN python3.8 -m pip install --extra-index-url https://pypi.chia.net/simple/ miniupnpc==2.1
RUN python3.8 -m pip install -e .

CMD ["python3","exporter.py"]