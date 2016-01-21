FROM python:2.7
MAINTAINER ITOH Akihiko

ADD ./GitAutoDeploy.conf.json /root/GitAutoDeploy.conf.json
ADD ./GitAutoDeploy.py /root/GitAutoDeploy.py

EXPOSE 8001

WORKDIR /root
ENTRYPOINT ["python"]
CMD ["GitAutoDeploy.py --daemon-mode"]

