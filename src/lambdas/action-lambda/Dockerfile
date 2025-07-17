FROM public.ecr.aws/lambda/python:3.11@sha256:58834a0d4d7f86326b6c91d516c66fbe8e91ccd3646ceba4025a66a7a8906e81
RUN yum update --security -y && \
    yum install -y gcc gcc-c++ && \
    yum clean all

# Set up Lambda environment
ENV LAMBDA_TASK_ROOT=/var/task
ENV LAMBDA_RUNTIME_DIR=/var/runtime
ENV PATH=/var/lang/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Set Python 3.11 as the default
RUN ln -sf /usr/local/bin/python3.11 /usr/bin/python3 && \
    ln -sf /usr/local/bin/python3.11 /usr/bin/python

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --upgrade pip setuptools wheel --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir
COPY . ${LAMBDA_TASK_ROOT}
CMD ["index.get_response"]
USER 1001
HEALTHCHECK --interval=600s --timeout=2s --retries=12 \
    CMD ["python3", "-c", "import sys; sys.exit(0 if __import__('index').get_response else 1)"]