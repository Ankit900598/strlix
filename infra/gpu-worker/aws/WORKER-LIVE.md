# AWS GPU worker LIVE — Strlix soft-launch capacity

**As of:** 2026-09-22 ~09:40 IST  
**Purpose:** Wire `strlix-gpu-worker-1` as **GPU capacity** for the phone pool while Azure NCasT4 / NVadsA10 remain **limit 0**.  
**Do not:** terminate this instance · create Azure GPU · enable Stripe live.

## Live identity

| Field | Value |
|-------|--------|
| Instance id | `i-0531c567f620877c3` |
| Name | `strlix-gpu-worker-1` |
| Type | `g4dn.xlarge` (1× Tesla T4, 4 vCPU, 16 GiB) |
| Region / AZ | `us-east-1` / `us-east-1b` |
| State | **RUNNING** (started 2026-09-22 ~09:27 IST from stopped) |
| Public IP | `44.204.83.61` (changes on stop/start) |
| Private IP | `172.31.82.79` (stable in subnet) |
| SSM | Profile `strlix-gpu-worker-ssm` · agent **Online** |
| SG | `sg-07cc11f2d8fdc0058` — **no public inbound**; egress all (SSM) |
| AMI | Deep Learning Base OSS Nvidia Driver GPU (Ubuntu 22.04) |
| Hourly cost | **≈ $0.526 / hr** On-Demand Linux us-east-1 (≈ **$12.6 / day** if left running) |

## Health (verified this pass)

| Check | Result |
|-------|--------|
| EC2 state | `running` |
| SSM PingStatus | `Online` (Ubuntu 22.04, agent 3.3.x) |
| `nvidia-smi` | **GREEN** — Tesla T4 · Driver **595.91.07** · CUDA **13.2** · 15360 MiB |
| Docker | **29.8.1** · runtime `nvidia` · `docker run --gpus all … nvidia-smi` **GREEN** |
| `/dev/kvm` | **Absent** — classic AVD hardware accel not available |
| binderfs | Mounted at `/dev/binderfs` (`binder`/`hwbinder`/`vndbinder`) |
| Redroid | **UP** — container `strlix-redroid-1` · image `redroid/redroid:12.0.0_64only-latest` · ADB `127.0.0.1:5556` · `boot_completed=1` · Android **12** · `product:redroid_x86_64_only` |
| GPU mode | `androidboot.redroid_gpu_mode=guest` (host mode left ADB offline on this AMI; guest boots clean) |
| Disk / RAM | ~97G root · ~15 GiB RAM |

**Port note:** host `127.0.0.1:5555` is taken by NVIDIA `nv-hostengine` — use **5556** for Redroid ADB.

Access only via SSM (no public SSH):

```bash
aws ssm start-session --region us-east-1 --target i-0531c567f620877c3
# or:
aws ssm send-command --region us-east-1 --instance-ids i-0531c567f620877c3 \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["nvidia-smi","docker ps --filter name=strlix-redroid-1","adb devices -l"]'
```

## Installed / changed on host this pass

- Verified existing DL AMI NVIDIA stack (no driver reinstall).
- Mounted binderfs; `modprobe binder_linux`.
- Pulled `redroid/redroid:12.0.0_64only-latest`.
- Started Docker container `strlix-redroid-1` (`--restart unless-stopped`, data `/opt/strlix/redroid-data`, publish `127.0.0.1:5556->5555`).
- Installed `adb` via apt.
- Left Azure GPU create untouched; did not open SG inbound; did not enable Stripe live.

## Phone-pool wiring

### Current Redroid (already running)

```bash
# On worker (SSM):
adb connect 127.0.0.1:5556
adb -s 127.0.0.1:5556 shell getprop sys.boot_completed   # expect 1
adb -s 127.0.0.1:5556 shell getprop ro.build.version.release  # 12
docker ps --filter name=strlix-redroid-1
nvidia-smi
```

### Recreate if needed

```bash
sudo mkdir -p /dev/binderfs /opt/strlix/redroid-data
sudo mountpoint -q /dev/binderfs || sudo mount -t binder binder /dev/binderfs
sudo docker pull redroid/redroid:12.0.0_64only-latest
sudo docker rm -f strlix-redroid-1 2>/dev/null || true
# Use 5556 — 5555 is nv-hostengine on this AMI
sudo docker run -d --name strlix-redroid-1 --restart unless-stopped \
  --privileged --gpus all \
  -v /opt/strlix/redroid-data:/data \
  -p 127.0.0.1:5556:5555 \
  redroid/redroid:12.0.0_64only-latest \
  androidboot.redroid_gpu_mode=guest \
  androidboot.redroid_width=720 androidboot.redroid_height=1280 androidboot.redroid_dpi=320
```

Optional later: retry `androidboot.redroid_gpu_mode=host` after confirming ADB stays online (host mode was flaky this pass).

### Broker / pool

1. SSM port-forward ADB to a trusted broker host — **do not** open SG `0.0.0.0/0`:

```bash
aws ssm start-session --region us-east-1 --target i-0531c567f620877c3 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5556"],"localPortNumber":["5556"]}'
```

2. Register pool device when multi-device lands (today phase-1 seed is still Azure pilot — see `infra/ops/CAPACITY-PHONE-POOL.md`):
   - id example: `aws-gpu-redroid-1`
   - serial: `127.0.0.1:5556` after forward
   - labels: `kind=redroid`, `host=strlix-gpu-worker-1`
3. Keep `vm-zevi-cloudphone` pilot emulator as fallback until broker multi-device is wired.

### Why not AVD on this box

No `/dev/kvm`. Software AVD is possible but slow; Redroid is the intended density path on the T4.

## Idle hygiene

```bash
# Stop compute when idle (keeps EBS; stops ~$0.526/hr). Do NOT terminate.
aws ec2 stop-instances --region us-east-1 --instance-ids i-0531c567f620877c3

# Start again (public IP will change; Redroid restarts via --restart unless-stopped after Docker is up)
aws ec2 start-instances --region us-east-1 --instance-ids i-0531c567f620877c3
# wait SSM Online → nvidia-smi → adb connect 127.0.0.1:5556
```

## Related

- Create/recreate: `CREATE-aws-gpu-worker.md` / `CREATE-aws-gpu-worker.sh`
- Tickets: `../../../demo/credit-burn/QUOTA-TICKETS.md`
- Soft-launch: `../../../demo/launch/SOFT-LAUNCH-STATUS.md`
- Phone pool: `../../ops/CAPACITY-PHONE-POOL.md`
