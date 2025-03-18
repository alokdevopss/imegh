FROM python:3.9
WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY webhook.py /app/webhook.py
RUN pip install -r requirements.txt
RUN curl -sSL -o /usr/local/bin/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64 && \
    chmod +x /usr/local/bin/argocd
CMD ["python", "webhook.py"]
