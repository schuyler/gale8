AWS_REGION=eu-west-2
FUNCTION=download-forecast
IMAGE=download-forecast

IAM_ROLE := arn:aws:iam::$(AWS_ACCOUNT):role/gale8-lambda
ECR=$(AWS_ACCOUNT).dkr.ecr.$(AWS_REGION).amazonaws.com
IMAGE_URI=$(ECR)/$(IMAGE)

all: update-function check-launch

build-latest:
	docker build . -t $(IMAGE)

run: build-latest
	docker run -p 9000:8080 --env-file .env --rm $(IMAGE)

login:
	aws ecr get-login-password --region $(AWS_REGION) | \
		docker login --username AWS --password-stdin $(ECR)

create-repo:
	aws ecr create-repository --repository-name $(IMAGE) \
		--image-scanning-configuration scanOnPush=true --image-tag-mutability MUTABLE

upload-%: build-% login
	docker tag $(IMAGE):$* $(IMAGE_URI):$*
	docker push $(IMAGE_URI):$*

check-stream:
	@[ -n "$(FORECAST_STREAM)" ] || (echo "Try again by passing FORECAST_STREAM to make" && false)
	@[ -n "$(ERROR_TOPIC_ARN)" ] || (echo "Try again by passing ERROR_TOPIC_ARN to make" && false)

check-account:
	@[ -n "$(AWS_ACCOUNT)" ] || (echo "Try again by passing AWS_ACCOUNT to make" && false)

create-function: check-stream upload-latest
	aws lambda create-function \
		--function-name $(FUNCTION) \
		--package-type Image  \
		--code ImageUri=$(IMAGE_URI):latest \
		--role $(IAM_ROLE) \
		--memory-size 512 \
		--environment "Variables={FORECAST_STREAM=$(FORECAST_STREAM),ERROR_TOPIC_ARN=$(ERROR_TOPIC_ARN)}" \
		--timeout 900

update-function: upload-latest
	aws lambda update-function-code \
		--function-name $(FUNCTION) \
		--image-uri $(IMAGE_URI):latest

update-function-environment: check-stream
	aws lambda update-function-configuration \
		--function-name $(FUNCTION) \
		--environment "Variables={FORECAST_STREAM=$(FORECAST_STREAM),ERROR_TOPIC_ARN=$(ERROR_TOPIC_ARN)}" \

delete-function:
	aws lambda delete-function --function-name $(FUNCTION)

check-launch:
	python3 download_forecast.py -s

create-rule-0048: check-account
	./gen-rule.sh $(AWS_REGION) $(AWS_ACCOUNT) $(FUNCTION) 00 48 12 '*'

delete-rule-0048: check-account
	./del-rule.sh $(FUNCTION) 00 48

create-rule-0520: check-account
	./gen-rule.sh $(AWS_REGION) $(AWS_ACCOUNT) $(FUNCTION) 05 20 12 '*'

delete-rule-0520: check-account
	./del-rule.sh $(FUNCTION) 05 20

create-rule-1754: check-account
	./gen-rule.sh $(AWS_REGION) $(AWS_ACCOUNT) $(FUNCTION) 17 54 6 1,7

delete-rule-1754: check-account
	./del-rule.sh $(FUNCTION) 17 54

create: upload-latest create-function \
	create-rule-0048 create-rule-0520 create-rule-1754 \
	clean

destroy: delete-function \
	delete-rule-0048 delete-rule-0520 delete-rule-1754 \
	clean

clean:
	docker image rm $(IMAGE)
