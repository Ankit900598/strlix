#!/usr/bin/env bash
# Create ONE Strlix AWS GPU worker (g4dn.xlarge preferred).
# Does NOT create unless CONFIRM_AWS_GPU_CREATE=yes
set -euo pipefail

AWS="${AWS_CLI:-$HOME/.local/bin/aws}"
REGION="${REGION:-us-east-1}"
INSTANCE_TYPE="${INSTANCE_TYPE:-g4dn.xlarge}"
FALLBACK_TYPE="${FALLBACK_TYPE:-g5.xlarge}"
NAME="${NAME:-strlix-gpu-worker-1}"
# Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04) — refreshed via SSM param
AMI_PARAM="${AMI_PARAM:-/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-22.04/latest/ami-id}"
IAM_PROFILE="${IAM_PROFILE:-strlix-gpu-worker-ssm}"
SG_NAME="${SG_NAME:-strlix-gpu-worker-sg}"
VOLUME_GB="${VOLUME_GB:-100}"

echo "== Preflight =="
$AWS sts get-caller-identity --output json
echo "REGION=$REGION TYPE=$INSTANCE_TYPE NAME=$NAME"

QUOTA=$($AWS service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA --region "$REGION" --query 'Quota.Value' --output text)
echo "G/VT On-Demand quota (vCPU)=$QUOTA"
if [[ "$(python3 -c "print(1 if float('$QUOTA') < 4 else 0)")" == "1" ]]; then
  echo "REFUSING: G/VT quota=$QUOTA (<4 needed for g4dn.xlarge). See REQUEST-quota.md" >&2
  exit 3
fi

EXISTING=$($AWS ec2 describe-instances --region "$REGION" \
  --filters "Name=tag:Name,Values=$NAME" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
  --query 'Reservations[*].Instances[*].InstanceId' --output text)
if [[ -n "${EXISTING// /}" ]]; then
  echo "REFUSING: instance(s) already tagged Name=$NAME: $EXISTING" >&2
  exit 4
fi

AMI_ID=$($AWS ssm get-parameter --region "$REGION" --name "$AMI_PARAM" --query 'Parameter.Value' --output text)
echo "AMI=$AMI_ID ($AMI_PARAM)"

VPC_ID=$($AWS ec2 describe-vpcs --region "$REGION" --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
echo "VPC=$VPC_ID (default)"

# Security group: no public inbound SSH; egress default allows SSM HTTPS
SG_ID=$($AWS ec2 describe-security-groups --region "$REGION" \
  --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
  --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [[ -z "$SG_ID" || "$SG_ID" == "None" ]]; then
  echo "Creating SG $SG_NAME (no public inbound; open 22/443 later only if needed)"
  SG_ID=$($AWS ec2 create-security-group --region "$REGION" \
    --group-name "$SG_NAME" \
    --description "Strlix GPU worker - SSM preferred; no public SSH by default" \
    --vpc-id "$VPC_ID" \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=$SG_NAME},{Key=Project,Value=strlix},{Key=Owner,Value=ay186mnc},{Key=rg-note,Value=mirror-of-zevi-cloudphone}]" \
    --query 'GroupId' --output text)
  # Explicitly ensure no inbound from 0.0.0.0/0. Default SG create has none.
  echo "SG created: $SG_ID (inbound empty — use SSM Session Manager)"
else
  echo "Reusing SG $SG_ID"
fi

# Prefer AZ with g4dn.xlarge; pick first default subnet that offers it
pick_subnet() {
  local itype="$1"
  local azs
  azs=$($AWS ec2 describe-instance-type-offerings --region "$REGION" --location-type availability-zone \
    --filters "Name=instance-type,Values=$itype" --query 'InstanceTypeOfferings[].Location' --output text)
  for az in $azs; do
    local sid
    sid=$($AWS ec2 describe-subnets --region "$REGION" \
      --filters "Name=vpc-id,Values=$VPC_ID" "Name=availability-zone,Values=$az" "Name=default-for-az,Values=true" \
      --query 'Subnets[0].SubnetId' --output text)
    if [[ -n "$sid" && "$sid" != "None" ]]; then
      echo "$sid $az"
      return 0
    fi
  done
  return 1
}

SUBNET_INFO=$(pick_subnet "$INSTANCE_TYPE" || true)
if [[ -z "$SUBNET_INFO" ]]; then
  echo "WARN: no subnet for $INSTANCE_TYPE; trying fallback $FALLBACK_TYPE"
  INSTANCE_TYPE="$FALLBACK_TYPE"
  SUBNET_INFO=$(pick_subnet "$INSTANCE_TYPE" || true)
fi
if [[ -z "$SUBNET_INFO" ]]; then
  echo "REFUSING: no suitable subnet/AZ for GPU types" >&2
  exit 5
fi
SUBNET_ID=$(echo "$SUBNET_INFO" | awk '{print $1}')
AZ=$(echo "$SUBNET_INFO" | awk '{print $2}')
echo "Subnet=$SUBNET_ID AZ=$AZ TYPE=$INSTANCE_TYPE"
echo "Est. On-Demand: g4dn.xlarge ≈ \$0.526/hr · g5.xlarge ≈ \$1.006/hr (us-east-1 Linux)"

if [[ "${CONFIRM_AWS_GPU_CREATE:-}" != "yes" ]]; then
  echo "Dry-run only. Re-run with CONFIRM_AWS_GPU_CREATE=yes to create."
  cat <<CMDS
# Exact create:
$AWS ec2 run-instances --region $REGION \\
  --image-id $AMI_ID \\
  --instance-type $INSTANCE_TYPE \\
  --subnet-id $SUBNET_ID \\
  --security-group-ids $SG_ID \\
  --iam-instance-profile Name=$IAM_PROFILE \\
  --associate-public-ip-address \\
  --metadata-options HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled \\
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":$VOLUME_GB,"VolumeType":"gp3","DeleteOnTermination":true}}]' \\
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=Project,Value=strlix},{Key=Owner,Value=ay186mnc},{Key=rg-note,Value=mirror-of-zevi-cloudphone},{Key=role,Value=gpu-worker}]' \\
  --count 1
CMDS
  exit 0
fi

echo "CONFIRM_AWS_GPU_CREATE=yes — creating ONE instance..."
# Try primary type; on InsufficientInstanceCapacity try one alternate AZ then fallback type once
run_once() {
  local itype="$1" subnet="$2"
  $AWS ec2 run-instances --region "$REGION" \
    --image-id "$AMI_ID" \
    --instance-type "$itype" \
    --subnet-id "$subnet" \
    --security-group-ids "$SG_ID" \
    --iam-instance-profile "Name=$IAM_PROFILE" \
    --associate-public-ip-address \
    --metadata-options "HttpTokens=required,HttpPutResponseHopLimit=2,HttpEndpoint=enabled" \
    --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":$VOLUME_GB,\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME},{Key=Project,Value=strlix},{Key=Owner,Value=ay186mnc},{Key=rg-note,Value=mirror-of-zevi-cloudphone},{Key=role,Value=gpu-worker}]" \
    --count 1 \
    --query 'Instances[0].[InstanceId,InstanceType,Placement.AvailabilityZone]' --output text
}

set +e
OUT=$(run_once "$INSTANCE_TYPE" "$SUBNET_ID" 2>/tmp/strlix-gpu-create.err)
RC=$?
set -e
if [[ $RC -ne 0 ]]; then
  ERR=$(cat /tmp/strlix-gpu-create.err)
  echo "First attempt failed: $ERR"
  if echo "$ERR" | grep -qiE 'InsufficientInstanceCapacity|Unsupported|Not available'; then
    # One alternate: try another AZ for same type, else fallback type once
    ALT=""
    for cand in $($AWS ec2 describe-instance-type-offerings --region "$REGION" --location-type availability-zone \
      --filters "Name=instance-type,Values=$INSTANCE_TYPE" --query 'InstanceTypeOfferings[].Location' --output text); do
      [[ "$cand" == "$AZ" ]] && continue
      sid=$($AWS ec2 describe-subnets --region "$REGION" \
        --filters "Name=vpc-id,Values=$VPC_ID" "Name=availability-zone,Values=$cand" "Name=default-for-az,Values=true" \
        --query 'Subnets[0].SubnetId' --output text)
      if [[ -n "$sid" && "$sid" != "None" ]]; then
        echo "Retry same type in AZ $cand..."
        set +e
        OUT=$(run_once "$INSTANCE_TYPE" "$sid" 2>/tmp/strlix-gpu-create.err)
        RC=$?
        set -e
        if [[ $RC -eq 0 ]]; then ALT=1; break; fi
        echo "Alt AZ failed: $(cat /tmp/strlix-gpu-create.err)"
        break  # only one alternate AZ attempt
      fi
    done
    if [[ -z "$ALT" && "$INSTANCE_TYPE" != "$FALLBACK_TYPE" ]]; then
      echo "Trying fallback type $FALLBACK_TYPE once..."
      FB=$(pick_subnet "$FALLBACK_TYPE" || true)
      if [[ -n "$FB" ]]; then
        INSTANCE_TYPE="$FALLBACK_TYPE"
        SUBNET_ID=$(echo "$FB" | awk '{print $1}')
        set +e
        OUT=$(run_once "$INSTANCE_TYPE" "$SUBNET_ID" 2>/tmp/strlix-gpu-create.err)
        RC=$?
        set -e
      fi
    fi
  fi
fi

if [[ $RC -ne 0 || -z "$OUT" ]]; then
  echo "CREATE FAILED. Exact error:" >&2
  cat /tmp/strlix-gpu-create.err >&2
  exit 6
fi

IID=$(echo "$OUT" | awk '{print $1}')
echo "Created InstanceId=$IID ($OUT)"
echo "Waiting until running..."
$AWS ec2 wait instance-running --region "$REGION" --instance-ids "$IID"
$AWS ec2 describe-instances --region "$REGION" --instance-ids "$IID" \
  --query 'Reservations[0].Instances[0].{Id:InstanceId,Type:InstanceType,State:State.Name,AZ:Placement.AvailabilityZone,PublicIp:PublicIpAddress,PrivateIp:PrivateIpAddress,Subnet:SubnetId}' \
  --output json
echo "Idle hygiene: aws ec2 stop-instances --instance-ids $IID --region $REGION"
echo "Terminate:     aws ec2 terminate-instances --instance-ids $IID --region $REGION"
