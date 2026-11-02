#!/usr/bin/env bash
# Create the S3 bucket Terraform cannot create, write terraform.tfvars, upload
# the experiment files. Does not deploy the stack.
#
#   experiments/bootstrap_aws.sh
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

export AWS_REGION=${AWS_REGION:-us-west-2}
export AWS_DEFAULT_REGION=$AWS_REGION

aws sts get-caller-identity >/dev/null

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET=${BUCKET:-file-transfer-${ACCOUNT}-kn}
PREFIX=${PREFIX:-tmp/}

echo "account  $ACCOUNT"
echo "region   $AWS_REGION"
echo "bucket   $BUCKET"

if aws s3api head-bucket --bucket "$BUCKET" 2>/dev/null; then
  echo "bucket already exists"
else
  echo "creating bucket"
  aws s3 mb "s3://$BUCKET" --region "$AWS_REGION"
fi

cat > terraform/terraform.tfvars <<EOF
files_bucket = "$BUCKET"
files_prefix = "$PREFIX"
# Slightly more sensitive than the defaults so a short Locust run can
# actually move the scalers. Gateway still uses ALB requests/target;
# backend still uses CPU (an NLB has no request-count metric).
gateway_requests_per_target = 40
backend_cpu_target          = 40
EOF

python3 experiments/make_files.py --out experiments/corpus
for name in f4kib.bin f64kib.bin f256kib.bin f1mib.bin f4mib.bin; do
  aws s3 cp "experiments/corpus/$name" "s3://$BUCKET/${PREFIX}$name"
done

echo
echo "wrote terraform/terraform.tfvars"
echo "uploaded files under s3://$BUCKET/$PREFIX"
echo "next: scripts/deploy.sh --yes"
