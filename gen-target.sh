#!/bin/bash
LAMBDA_ARN=$1
EXEC_TIME=$2
cat <<EOF
[
    {
        "Id": "1",
        "Arn": "${LAMBDA_ARN}",
        "Input": "{\"time\": \"${EXEC_TIME}\", \"duration\": 720}",
        "RetryPolicy": {
            "MaximumEventAgeInSeconds": 60
        }
    }
]
EOF
