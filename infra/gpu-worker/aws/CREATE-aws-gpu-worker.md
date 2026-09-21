# Create AWS GPU worker (Strlix soft-launch)

**Account:** `787235610343` · **Region:** `us-east-1`  
**Do not** create Azure GPU (`CONFIRM_GPU_CREATE` / NC4as) — Azure NCasT4 / NVadsA10 remain **limit 0**.  
**Stripe live:** stays **OFF** (first month free).

## Live instance (created 2026-09-21 ~23:46 IST)

| Field | Value |
|-------|--------|
| Instance id | `i-0531c567f620877c3` |
| Name tag | `strlix-gpu-worker-1` |
| Type | `g4dn.xlarge` (1× NVIDIA T4, 4 vCPU) |
| State | `running` (at create) |
| AZ | `us-east-1b` |
| Subnet | `subnet-0e1a710803da5929d` (default VPC) |
| Public IP | `44.201.216.57` |
| Private IP | `172.31.82.79` |
| AMI | Deep Learning Base OSS Nvidia Driver GPU (Ubuntu 22.04) via SSM param `/aws/service/deeplearning/ami/x86_64/base-oss-nvidia-driver-gpu-ubuntu-22.04/latest/ami-id` (`ami-0defd610006e0417c` at create) |
| SG | `sg-07cc11f2d8fdc0058` (`strlix-gpu-worker-sg`) — **no public inbound**; egress all (SSM HTTPS) |
| IAM | instance profile `strlix-gpu-worker-ssm` + role `strlix-gpu-worker-ssm-role` (`AmazonSSMManagedInstanceCore`) |
| Tags | `Name=strlix-gpu-worker-1`, `Project=strlix`, `rg-note=mirror-of-zevi-cloudphone`, `Owner=ay186mnc`, `role=gpu-worker` |
| Hourly estimate | **≈ $0.526 / hr** On-Demand Linux us-east-1 (≈ $12.6 / day if left running) |

Quota: Service Quotas **L-DB2E81BA** = **4** vCPU (case **179000526000600** / `ab584e62…` **CASE_CLOSED**). First `RunInstances` hit transient `VcpuLimitExceeded` (EC2 still showing 0); DryRun then real create succeeded ~20 min after case close. Do **not** launch a second worker without product ask (quota headroom is only one g4dn.xlarge).

## Access (SSM preferred — no public SSH)

```bash
# Wait until SSM lists the instance (often 2–5 min after boot)
aws ssm describe-instance-information --region us-east-1 \
  --filters Key=InstanceIds,Values=i-0531c567f620877c3

aws ssm start-session --region us-east-1 --target i-0531c567f620877c3
```

Public IP exists for later ADB/API tunnel docs, but **SG inbound is empty**. To open minimally later:

```bash
# Example only — lock CIDR to operator IP, never 0.0.0.0/0 long-term
aws ec2 authorize-security-group-ingress --region us-east-1 \
  --group-id sg-07cc11f2d8fdc0058 \
  --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges='[{CidrIp=YOUR.IP/32,Description=operator-ssh}]'
# Optionally 443 for reverse tunnel / API as needed
```

If you must use an SSH key: generate under this directory, keep `*.pem` out of git (already in root `.gitignore`).

```bash
ssh-keygen -t ed25519 -f /workspace/zevi-cloudphone/infra/gpu-worker/aws/strlix-gpu-worker.pem -N ''
# then create-key-pair / import and recreate or replace-instance — prefer SSM instead
```

## Create / recreate (guarded)

```bash
# Dry-run (prints plan; no create)
./infra/gpu-worker/aws/CREATE-aws-gpu-worker.sh

# Create ONE instance (refuses if Name=strlix-gpu-worker-1 already exists)
CONFIRM_AWS_GPU_CREATE=yes ./infra/gpu-worker/aws/CREATE-aws-gpu-worker.sh
```

Defaults: `g4dn.xlarge`; fallback `g5.xlarge` only if primary type/AZ fails capacity. Script retries **at most one** alternate AZ then one fallback type — does not spam instances.

## Stop / terminate (idle hygiene)

```bash
# Stop (keeps EBS; stops ~$0.526/hr compute; gp3 disk still bills)
aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3

# Start again
aws ec2 start-instances --region us-east-1 --instance-ids i-0531c567f620877c3

# Terminate (destroys instance + DeleteOnTermination root volume)
aws ec2 terminate-instances --region us-east-1 --instance-ids i-0531c567f620877c3
```

## NVIDIA check (after SSM online)

```bash
nvidia-smi
```

DL Base OSS Nvidia Driver GPU AMI boots with drivers for G4dn/G5; no extra driver install for soft-launch smoke.

## Related

- Azure path (do not run with confirm): `../CREATE-gpu-worker.sh` / `../REQUEST-quota.md`
- Tickets: `../../../demo/credit-burn/QUOTA-TICKETS.md`
- Soft-launch: `../../../demo/launch/SOFT-LAUNCH-STATUS.md`
