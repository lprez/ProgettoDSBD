FROM python:3.8
WORKDIR /app

RUN curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 && \
    chmod 700 get_helm.sh && \
    ./get_helm.sh

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ .

ENV HOME /app
ENV FLASK_APP=run.py
RUN chmod 777 /app
CMD ["python", "-m", "flask", "run", "--host", "0.0.0.0"]
