BUCKET = gale8-uk
DISTRIBUTION = EXV28HJUVSJZY

all: index download-forecast

index: 
	aws s3 sync --acl public-read docs/ s3://$(BUCKET)/
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION) --paths /index.html

download-forecast:
	make -C download
