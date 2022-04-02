REGION := eu-west-2
IAM_ROLE := arn:aws:iam::$(ACCOUNT):role/gale8-lambda
LAMBDA_ARN := "arn:aws:lambda:$(REGION):$(ACCOUNT):function:download-forecast"
BUCKET = gale8-uk
DISTRIBUTION = EXV28HJUVSJZY

all: update check-launch index clean

index:
	aws s3 cp --acl public-read index.html s3://$(BUCKET)/
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION) --paths /index.html

build:
	mkdir build
	cp download_forecast.py build
	pip3 install -t build pytz
	(cd build && zip -9r - .) > download-forecast.zip
	rm -r build

update: build
	aws lambda update-function-code \
		--function-name download-forecast \
		--zip-file fileb://download-forecast.zip

check-launch:
	python3 download_forecast.py -s

clean:
	rm -rf __pycache__ build download-forecast.zip

check-account:
	@[ -n "$(ACCOUNT)" ] || (echo "Try again by passing ACCOUNT to make" && false)

check-stream:
	@[ -n "$(STREAM)" ] || (echo "Try again by passing STREAM to make" && false)

create-function: check-account check-stream build
	aws lambda create-function \
		--function-name download-forecast \
		--handler download_forecast.handle_lambda_event \
		--runtime python3.9 \
		--role $(IAM_ROLE) \
		--environment "Variables={FORECAST_STREAM=$(STREAM)}" \
		--timeout 900 \
		--zip-file fileb://download-forecast.zip

create-rule-0048: check-account
	aws events put-rule \
		--name forecast-0048 \
		--schedule-expression 'cron(47 00 ? * * *)'
	./gen-target.sh $(LAMBDA_ARN) 00:48 > tmp.json
	aws events put-targets \
		--rule forecast-0048 \
		--targets file://tmp.json
	rm -f tmp.json
	aws lambda add-permission \
		--function-name download-forecast \
		--action 'lambda:InvokeFunction' \
		--principal events.amazonaws.com \
		--source-arn arn:aws:events:$(REGION):$(ACCOUNT):rule/forecast-0048 \
		--statement-id forecast-0048-event

create-rule-0520: check-account
	aws events put-rule \
		--name forecast-0520 \
		--schedule-expression 'cron(19 05 ? * * *)'
	./gen-target.sh $(LAMBDA_ARN) 05:20 > tmp.json
	aws events put-targets \
		--rule forecast-0520 \
		--targets file://tmp.json
	rm -f tmp.json
	aws lambda add-permission \
		--function-name download-forecast \
		--action 'lambda:InvokeFunction' \
		--principal events.amazonaws.com \
		--source-arn arn:aws:events:$(REGION):$(ACCOUNT):rule/forecast-0520 \
		--statement-id forecast-0520-event

create: create-function create-rule-0048 create-rule-0520 check-launch clean

destroy:
	aws lambda delete-function --function-name download-forecast
	aws events remove-targets --rule forecast-0048 --ids 1
	aws events delete-rule --name forecast-0048
	aws events remove-targets --rule forecast-0520 --ids 1
	aws events delete-rule --name forecast-0520
