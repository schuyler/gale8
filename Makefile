BUCKET = gale8-uk
DISTRIBUTION = EXV28HJUVSJZY

all: index catalog-forecast transcribe-forecast download-forecast

index: 
	aws s3 sync --acl public-read docs/ s3://$(BUCKET)/
	aws cloudfront create-invalidation --distribution-id $(DISTRIBUTION) --paths /index.html

download-forecast:
	make -C download

transcribe-forecast:
	make -C transcribe

catalog-forecast:
	make -C catalog

assemble-stream:
	make -C assemble
