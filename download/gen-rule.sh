#!/bin/bash
REGION=$1
ACCOUNT=$2
FUNCTION=$3
HOUR=$4
MIN=$5
DURATION=$6

RULE="forecast-${HOUR}${MIN}"

aws events put-rule \
  --name $RULE \
  --schedule-expression "cron($(($MIN - 1)) $HOUR ? * * *)"

cat >tmp.json <<EOF
[
    {
        "Id": "1",
        "Arn": "arn:aws:lambda:${REGION}:${ACCOUNT}:function:${FUNCTION}",
        "Input": "{\"time\": \"${HOUR}:${MIN}\", \"duration\": $((${DURATION} * 60))}",
        "RetryPolicy": {
            "MaximumEventAgeInSeconds": 60
        }
    }
]
EOF

aws events put-targets \
  --rule $RULE \
  --targets file://tmp.json

rm -f tmp.json

aws lambda add-permission \
  --function-name ${FUNCTION} \
  --action 'lambda:InvokeFunction' \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:${REGION}:${ACCOUNT}:rule/${RULE} \
  --statement-id ${RULE}-event
