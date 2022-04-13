#!/bin/bash
FUNCTION=$1
HOUR=$2
MIN=$3

RULE="forecast-${HOUR}${MIN}"

aws events remove-targets --rule $RULE --ids 1
aws events delete-rule --name $RULE
aws lambda remove-permission --function-name ${FUNCTION} --statement-id ${RULE}-event
