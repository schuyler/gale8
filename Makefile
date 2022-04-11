REGION := eu-west-2
IAM_ROLE := arn:aws:iam::$(ACCOUNT):role/gale8-lambda
BUCKET = gale8-uk
DISTRIBUTION = EXV28HJUVSJZY
FUNCTION = download-forecast
LAMBDA_ARN := "arn:aws:lambda:$(REGION):$(ACCOUNT):function:$(FUNCTION)"

all: update check-launch index clean

clean:
	rm -rf __pycache__ build *.zip support-*.txt

index:
	aws s3 sync --acl public-read docs/ s3://$(BUCKET)/
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION) --paths /index.html

check-account:
	@[ -n "$(ACCOUNT)" ] || (echo "Try again by passing ACCOUNT to make" && false)

check-stream:
	@[ -n "$(STREAM)" ] || (echo "Try again by passing STREAM to make" && false)

create-function-%: check-account check-stream %.zip support-arn.txt
	aws lambda create-function \
		--function-name `echo $* | tr _ -` \
		--handler $*.handle_event \
		--runtime python3.9 \
		--role $(IAM_ROLE) \
		--environment "Variables={FORECAST_STREAM=$(STREAM)}" \
		--timeout 900 \
		--layers `cat support-arn.txt` \
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
	#pip3 install -t build pytz
	(cd build && zip -9qr - .) > $*.zip
	rm -r build

check-launch:
	python3 download_forecast.py -s

support: build-support install-support support-arn.txt clean

install-support:
	aws s3 cp $(FUNCTION)-support.zip s3://$(BUCKET)/layers/$(FUNCTION)-support.zip
	aws lambda publish-layer-version \
		--layer-name $(FUNCTION)-support \
		--content S3Bucket=$(BUCKET),S3Key=layers/$(FUNCTION)-support.zip

configure-support: support-arn.txt
	aws lambda update-function-configuration \
		--function-name $(FUNCTION) \
		--layers `cat support-arn.txt`

support-arn.txt:
	aws lambda list-layer-versions --layer-name download-forecast-support \
		--query 'LayerVersions[0].LayerVersionArn' \
		--output text \
		> support-arn.txt

clean-support:
	aws lambda list-layer-versions --layer-name download-forecast-support \
		--query 'LayerVersions[1].Version' \
		--output text \
		> support-version.txt
	aws lambda delete-layer-version --layer-name $(FUNCTION)-support \
		--version-number `cat support-version.txt` \
		2>/dev/null || true
	rm -f support-version.txt

build-support: install-ffmpeg install-vosk install-pytz
	(cd build && zip -9r - .) > $(FUNCTION)-support.zip
	rm -r build

install-ffmpeg:
	mkdir -p build/bin
	wget -O- https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz | \
		tar -xf -
	cp ffmpeg-*-amd64-static/ffmpeg build/bin
	rm -rf ffmpeg-*-amd64-static

install-vosk:
	mkdir -p build/python
	pip install --target build/python \
		--platform manylinux2014_x86_64 \
		--implementation cp \
		--python 3.9 \
		--only-binary=:all: \
		vosk
	wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
	unzip -d build vosk-model-small-en-us-*.zip
	mv build/vosk-model* build/model
	rm -rf vosk-model-small-en-us-*.zip

install-pytz:
	mkdir -p build/python
	pip install --target build/python pytz

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
	build support clean

destroy: delete-function \
	delete-rule-0048 delete-rule-0520 delete-rule-1201 delete-rule-1754 \
	clean
