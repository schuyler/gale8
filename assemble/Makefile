AWS_REGION=eu-west-2
IMAGE=assemble-stream
FUNCTION=assemble-stream

IAM_ROLE := arn:aws:iam::$(AWS_ACCOUNT):role/gale8-lambda
ECR=$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com
IMAGE_URI=$(ECR)/$(IMAGE)

all: update-function

build-latest:
	docker build . -t $(IMAGE)

run: build-latest
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

upload-%: build-%
	docker tag $(IMAGE):$* $(IMAGE_URI):$*
	docker push $(IMAGE_URI):$*

create-function: upload-latest
	aws lambda create-function \
		--function-name $(FUNCTION) \
		--package-type Image  \
		--code ImageUri=$(IMAGE_URI):latest \
		--role $(IAM_ROLE) \
		--memory-size 512 \
		--timeout 300

create-rule:
	../download/gen-rule.sh $(AWS_REGION) $(AWS_ACCOUNT) $(FUNCTION) 01 30 2

delete-rule:
	../download/del-rule.sh $(FUNCTION) 01 30

update-function: upload-latest
	aws lambda update-function-code \
		--function-name $(FUNCTION) \
		--image-uri $(IMAGE_URI):latest

delete-function:
	aws lambda delete-function --function-name $(FUNCTION)
	
clean:
	docker image rm $(IMAGE)
