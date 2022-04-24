FROM public.ecr.aws/lambda/python:3.9
WORKDIR /root
RUN yum -y install tar xz
RUN curl https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | \
      tar -J --no-anchored -x -f- ffmpeg && \
      mkdir -p /opt/bin && \
      mv ffmpeg-*-amd64-static/ffmpeg /opt/bin

FROM public.ecr.aws/lambda/python:3.9
COPY --from=0 /opt/bin /opt/bin
COPY requirements.txt  .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY assemble_stream.py ${LAMBDA_TASK_ROOT}

CMD ["assemble_stream.handle_event"]
