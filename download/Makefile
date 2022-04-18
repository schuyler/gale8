REGION := eu-west-2
ACCOUNT := $(AWS_ACCOUNT)
IAM_ROLE := arn:aws:iam::$(ACCOUNT):role/gale8-lambda
FUNCTION = download-forecast
LAMBDA_ARN := "arn:aws:lambda:$(REGION):$(ACCOUNT):function:$(FUNCTION)"

all: update-function-download_forecast check-launch clean

clean:
	rm -rf __pycache__ build *.zip support-*.txt

check-account:
	@[ -n "$(ACCOUNT)" ] || (echo "Try again by passing ACCOUNT to make" && false)

check-stream:
	@[ -n "$(STREAM)" ] || (echo "Try again by passing STREAM to make" && false)

create-function-%: check-account check-stream %.zip
	aws lambda create-function \
		--function-name `echo $* | tr _ -` \
		--handler $*.handle_event \
		--runtime python3.9 \
		--role $(IAM_ROLE) \
		--environment "Variables={FORECAST_STREAM=$(STREAM)}" \
		--timeout 900 \
		--zip-file fileb://$*.zip

update-function-%: %.zip
	aws lambda update-function-code \
		--function-name `echo $* | tr _ -` \
		--zip-file fileb://$*.zip

delete-function-%:
	aws lambda delete-function --function-name `echo $* | tr _ -`

%.zip: %.py
	mkdir build
	cp $*.py build
	pip3 install -t build pytz
	(cd build && zip -9qr - .) > $*.zip
	rm -r build

check-launch:
	python3 download_forecast.py -s

create-rule-0048: check-account
	./gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 00 48 12

delete-rule-0048: check-account
	./del-rule.sh $(FUNCTION) 00 48

create-rule-0520: check-account
	./gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 05 20 12

delete-rule-0520: check-account
	./del-rule.sh $(FUNCTION) 05 20

create-rule-1201: check-account
	./gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 12 01 5

delete-rule-1201: check-account
	./del-rule.sh $(FUNCTION) 12 01

create-rule-1754: check-account
	./gen-rule.sh $(REGION) $(ACCOUNT) $(FUNCTION) 17 54 5

delete-rule-1754: check-account
	./del-rule.sh $(FUNCTION) 17 54

create: create-function-download_forecast \
	create-rule-0048 create-rule-0520 create-rule-1201 create-rule-1754 \
	build support clean

destroy: delete-function-download_forecast \
	delete-rule-0048 delete-rule-0520 delete-rule-1201 delete-rule-1754 \
	clean
