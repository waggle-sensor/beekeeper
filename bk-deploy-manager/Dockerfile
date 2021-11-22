
# docker build -t waggle/beekeeper-deploy-manager .
# docker run -ti --rm --env BEEKEEPER_URL=http://host.docker.internal:5000 waggle/beekeeper-deploy-manager
FROM python:3.10-alpine

COPY *.py .
COPY requirements.txt .

RUN pip3 install -r requirements.txt

CMD [ "./deploy_manager.py" ]