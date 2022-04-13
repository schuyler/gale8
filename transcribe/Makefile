IMAGE=transcribe-forecast

build:
	cp ../transcribe_forecast.py .
	docker build . -t $(IMAGE)
	rm transcribe_forecast.py

run: build
	docker run -p 9000:8080 --env-file .env --rm $(IMAGE)

test:
	curl -XPOST http://`minikube ip`:9000/2015-03-31/functions/function/invocations" \
		-d '{"files": ["archive/20180102Z0520.mp3"]}'

login:
	aws ecr get-login-password --region ${AWS_REGION} | \
		docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_ACCOUNT}.amazonaws.com

create-repo:
	aws ecr create-repository --repository-name gale8
		--image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE

upload: build login
	docker tag $(IMAGE):latest ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}amazonaws.com/$(IMAGE):latest
	docker push ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/$(IMAGE):latest

clean:
	docker image rm $(IMAGE)
