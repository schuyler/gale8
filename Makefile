REGION := eu-west-2
IAM_ROLE := arn:aws:iam::$(ACCOUNT):role/gale8-lambda
LAMBDA_ARN := "arn:aws:lambda:$(REGION):$(ACCOUNT):function:download-forecast"
BUCKET = gale8-uk
DISTRIBUTION = EXV28HJUVSJZY
FUNCTION=download-forecast

all: update check-launch index clean

index:
	aws s3 sync --acl public-read docs/ s3://$(BUCKET)/
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION) --paths /index.html

build:
	mkdir build
	cp download_forecast.py build
	pip3 install -t build pytz
	(cd build && zip -9qr - .) > $(FUNCTION).zip
	rm -r build

update: build
	aws lambda update-function-code \
		--function-name $(FUNCTION) \
		--zip-file fileb://$(FUNCTION).zip

check-launch:
	python3 download_forecast.py -s

clean:
	rm -rf __pycache__ build $(FUNCTION).zip

check-account:
	@[ -n "$(ACCOUNT)" ] || (echo "Try again by passing ACCOUNT to make" && false)

check-stream:
	@[ -n "$(STREAM)" ] || (echo "Try again by passing STREAM to make" && false)

create-function: check-account check-stream build
	aws lambda create-function \
		--function-name $(FUNCTION) \
		--handler download_forecast.handle_lambda_event \
		--runtime python3.9 \
		--role $(IAM_ROLE) \
		--environment "Variables={FORECAST_STREAM=$(STREAM)}" \
		--timeout 900 \
		--zip-file fileb://download-forecast.zip

delete-function:
	aws lambda delete-function --function-name $(FUNCTION)

create-rule-0048: check-account
	tools/gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 00 48 12

delete-rule-0048: check-account
	tools/del-rule.sh $(FUNCTION) 00 48

create-rule-0520: check-account
	tools/gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 05 20 12

delete-rule-0520: check-account
	tools/del-rule.sh $(FUNCTION) 05 20

create-rule-1201: check-account
	tools/gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 12 01 7

delete-rule-1201: check-account
	tools/del-rule.sh $(FUNCTION) 12 01

create-rule-1754: check-account
	tools/gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 17 54 7

delete-rule-1754: check-account
	tools/del-rule.sh $(FUNCTION) 17 54

create: create-function \
	create-rule-0048 create-rule-0520 create-rule-1201 create-rule-1754 \
	check-launch clean

destroy: delete-function \
	delete-rule-0048 delete-rule-0520 delete-rule-1201 delete-rule-1754 \
	clean
