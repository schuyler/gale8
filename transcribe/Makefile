AWS_REGION=eu-west-2
IMAGE=transcribe-forecast
FUNCTION=transcribe-forecast
IAM_ROLE := arn:aws:iam::$(AWS_ACCOUNT):role/gale8-lambda
ECR=$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com
IMAGE_URI=$(ECR)/$(IMAGE):latest

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
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR)

create-repo:
	aws ecr create-repository --repository-name $(IMAGE) \
		--image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE

upload: build login
	docker tag $(IMAGE):latest $(IMAGE_URI)
	docker push $(IMAGE_URI)

create-function: upload
	aws lambda create-function \
		--function-name $(FUNCTION) \
		--package-type Image  \
		--code ImageUri=$(IMAGE_URI) \
		--role $(IAM_ROLE) \
		--memory-size 2048 \
		--timeout 900

update-function: upload
	aws lambda update-function-code \
		--function-name $(FUNCTION)
		--image-uri $(IMAGE_URI)

clean:
	docker image rm $(IMAGE)
