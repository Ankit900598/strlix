#!/usr/bin/env bash
# Draft only — does NOT create unless CONFIRM_GPU_CREATE=yes
# Prefers cheapest useful CUDA GPU: Standard_NC4as_T4_v3 in eastus2
set -euo pipefail

RG="${RG:-rg-zevi-cloudphone}"
LOC="${LOC:-eastus2}"
NAME="${NAME:-vm-zevi-gpu-t4}"
SIZE="${SIZE:-Standard_NC4as_T4_v3}"
PRIORITY="${PRIORITY:-Regular}"   # Regular | Spot
MAX_PRICE="${MAX_PRICE:--1}"      # Spot max price; -1 = pay up to OD
USERNAME="${USERNAME:-azureuser}"

echo "== Preflight =="
az account show --query "{name:name,id:id,user:user.name}" -o json
echo "Target RG=$RG LOC=$LOC SIZE=$SIZE PRIORITY=$PRIORITY"

if [[ "$RG" != "rg-zevi-cloudphone" ]]; then
  echo "REFUSING: only rg-zevi-cloudphone allowed" >&2
  exit 2
fi

LIMIT=$(az vm list-usage -l "$LOC" -o json | python3 -c '
import json,sys
d=json.load(sys.stdin)
lim=0
for u in d:
    loc=u.get("localName") or ""
    name=str(u.get("name") or "")
    if "NCASv3_T4" in loc or "NCasT4" in name or "NCASv3_T4" in name:
        lim=int(u.get("limit") or 0)
        break
print(lim)
')
echo "NCasT4 family limit=$LIMIT"
if [[ "${LIMIT:-0}" -lt 4 ]]; then
  echo "REFUSING: GPU quota limit=$LIMIT (<4). See REQUEST-quota.md" >&2
  # Still print commands for documentation when dry-run
  if [[ "${CONFIRM_GPU_CREATE:-}" == "yes" ]]; then
    exit 3
  fi
fi

echo "Est. 48h OD cost NC4as_T4_v3 eastus2 ≈ \$25 (\$0.526/hr). Spot ≈ \$12 if quota allows."

if [[ "${CONFIRM_GPU_CREATE:-}" != "yes" ]]; then
  echo "Dry-run only. Re-run with CONFIRM_GPU_CREATE=yes to create."
  cat <<CMDS
# Exact create (on-demand):
az vm create \\
  --resource-group $RG \\
  --name $NAME \\
  --location $LOC \\
  --size $SIZE \\
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest \\
  --admin-username $USERNAME \\
  --generate-ssh-keys \\
  --public-ip-sku Standard \\
  --nsg-rule SSH \\
  --os-disk-size-gb 64 \\
  --storage-sku Premium_LRS \\
  --tags project=strlix role=gpu-worker sprint=3day \\
  --output json

# Optional Spot (after LP quota ≥4):
#   --priority Spot --eviction-policy Deallocate --max-price $MAX_PRICE

# Idle hygiene:
# az vm deallocate -g $RG -n $NAME
CMDS
  exit 0
fi

echo "CONFIRM_GPU_CREATE=yes — creating..."
CREATE_ARGS=(
  --resource-group "$RG"
  --name "$NAME"
  --location "$LOC"
  --size "$SIZE"
  --image Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest
  --admin-username "$USERNAME"
  --generate-ssh-keys
  --public-ip-sku Standard
  --nsg-rule SSH
  --os-disk-size-gb 64
  --storage-sku Premium_LRS
  --tags project=strlix role=gpu-worker sprint=3day
)
if [[ "$PRIORITY" == "Spot" ]]; then
  CREATE_ARGS+=(--priority Spot --eviction-policy Deallocate --max-price "$MAX_PRICE")
fi
az vm create "${CREATE_ARGS[@]}" -o json
echo "Created. Remember: az vm deallocate -g $RG -n $NAME when idle."
