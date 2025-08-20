FROM public.ecr.aws/lambda/python:3.12
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ../../optimizer/src /opt/optimizer/src
ENV PYTHONPATH="/opt/optimizer/src:{$PYTHONPATH}"
COPY app.py ${LAMBDA_TASK_ROOT}
CMD ["app/lambda_handler"]