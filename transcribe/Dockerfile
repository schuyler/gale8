FROM public.ecr.aws/lambda/python:3.9
WORKDIR /root
RUN yum -y install tar xz unzip
RUN curl https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | \
      tar -J --no-anchored -x -f- ffmpeg && \
      mkdir -p /opt/bin && \
      mv ffmpeg-*-amd64-static/ffmpeg /opt/bin
RUN curl https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip > model.zip && \
      unzip model.zip && \
      mv vosk-model-* /opt/model

FROM public.ecr.aws/lambda/python:3.9
COPY --from=0 /opt/model /opt/model
COPY --from=0 /opt/bin /opt/bin
COPY requirements.txt  .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
COPY transcribe_forecast.py ${LAMBDA_TASK_ROOT}

CMD ["transcribe_forecast.handle_event"]
