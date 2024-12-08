REGION := eu-west-2
ACCOUNT := $(AWS_ACCOUNT)
IAM_ROLE := arn:aws:iam::$(ACCOUNT):role/gale8-lambda

all: update-function-catalog_forecast clean

clean:
	rm -rf __pycache__ build *.zip support-*.txt

check-account:
	@[ -n "$(ACCOUNT)" ] || (echo "Try again by passing ACCOUNT to make" && false)

check-syntax-%: %.py
	python3 -m py_compile $*.py

create-function-%: check-account %.zip
	aws lambda create-function \
		--function-name `echo $* | tr _ -` \
		--handler $*.handle_event \
		--runtime python3.9 \
		--role $(IAM_ROLE) \
		--timeout 30 \
		--zip-file fileb://$*.zip

update-function-%: %.zip
	aws lambda update-function-code \
		--function-name `echo $* | tr _ -` \
		--zip-file fileb://$*.zip

delete-function-%:
	aws lambda delete-function --function-name `echo $* | tr _ -`

%.zip: %.py check-syntax-%
	mkdir build
	cp $*.py build
	(cd build && zip -9qr - .) > $*.zip
	rm -r build
