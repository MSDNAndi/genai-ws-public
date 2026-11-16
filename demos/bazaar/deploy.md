# Deploying the A2A Bazaar to Azure Container Apps

**Status: written, NOT run.** Nothing in this file has been executed. Every command creates or changes Azure
resources in `genaiclass-rg`, so run them only after you have decided to deploy.

What you get: one Container App (`bazaar`) with external HTTPS ingress, 0.5 vCPU / 1 GiB, one replica. The
gateway key is a Container Apps **secret**. It is never in the image, the Dockerfile or the repo.

## 0. Prerequisites (2 min)

```bash
az login
az account show --query "{sub:name, id:id}" -o table          # check you are on the class subscription
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

## 1. Variables

```bash
RG=genaiclass-rg
LOC=$(az group show -n $RG --query location -o tsv)           # same region as the rest of the class
ACR=genaiclassbazaar$RANDOM                                    # must be globally unique, lowercase
ENVNAME=bazaar-env
APP=bazaar
GENAI_BASE_URL=https://genaiclass-apim-7slyc.azure-api.net/openai/v1
ROOM_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(6))")   # write it on the slide
read -rs -p "Bazaar gateway key (not echoed): " BAZAAR_KEY; echo
```

Which key? Best: a **new APIM subscription just for the Bazaar** (its own counters and limits, and you can suspend
it without affecting the room). Create it in the portal: APIM > Subscriptions > Add, scope = the GenAI API, name
`bazaar`. Never use the `shared` row or an attendee's key.

## 2. Build the image in the cloud (no local Docker needed, ~3 min)

```bash
az acr create -g $RG -n $ACR --sku Basic -l $LOC
az acr build -r $ACR -t bazaar:1 demos/bazaar        # run from the repo root; uses demos/bazaar/Dockerfile
```

## 3. Environment + app (~3 min)

```bash
az containerapp env create -g $RG -n $ENVNAME -l $LOC --logs-destination none   # no Log Analytics bill

az containerapp create -g $RG -n $APP --environment $ENVNAME \
  --image $ACR.azurecr.io/bazaar:1 --registry-server $ACR.azurecr.io --registry-identity system \
  --ingress external --target-port 8000 \
  --cpu 0.5 --memory 1.0Gi --min-replicas 1 --max-replicas 1 \
  --secrets genai-key="$BAZAAR_KEY" \
  --env-vars GENAI_BASE_URL=$GENAI_BASE_URL GENAI_API_KEY=secretref:genai-key \
             BAZAAR_ROOM_TOKEN=$ROOM_TOKEN BAZAAR_RATE_PER_MIN=12 BAZAAR_GLOBAL_PER_MIN=120
unset BAZAAR_KEY

FQDN=$(az containerapp show -g $RG -n $APP --query properties.configuration.ingress.fqdn -o tsv)
echo "https://$FQDN"
```

`--registry-identity system` makes the CLI create a managed identity and grant it AcrPull, which needs
role-assignment rights on the registry. If that step fails, use the admin user instead:
`az acr update -n $ACR --admin-enabled true` and replace `--registry-identity system` with
`--registry-username $ACR --registry-password "$(az acr credential show -n $ACR --query 'passwords[0].value' -o tsv)"`.

Why `--max-replicas 1`: the rate limiter, the task store and the shady "loot" list are in memory. One replica
handles a classroom (the model calls are the bottleneck, and `BAZAAR_MAX_CONCURRENT=8` caps them).

Replica options:

| Setting | Behaviour | When |
|---|---|---|
| `--min-replicas 1` | always warm, no cold start, billed at the idle rate when quiet | during the workshop |
| `--min-replicas 0` | scales to zero after ~5 min idle; first call after idle waits ~5-15 s | before/after the session |

```bash
az containerapp update -g $RG -n $APP --min-replicas 0     # scale to zero
az containerapp update -g $RG -n $APP --min-replicas 1     # warm it up 10 min before the segment
```

## 4. Smoke test (1 min)

```bash
B=https://$FQDN
curl -s $B/registry | python3 -m json.tool
curl -s $B/fx/.well-known/agent-card.json | python3 -m json.tool      # card URL must show https://$FQDN/fx/
python3 demos/bazaar/client.py fx "Convert 100 USD to EUR" --base $B --token $ROOM_TOKEN
python3 demos/bazaar/client.py poet "hi" --base $B                     # expect HTTP 401 (no room token)
```

If the card shows `http://` instead of `https://`, pin it:
`az containerapp update -g $RG -n $APP --set-env-vars BAZAAR_PUBLIC_URL=https://$FQDN`.

## 5. The poisoned-card segment

```bash
az containerapp update -g $RG -n $APP --set-env-vars BAZAAR_SHADY=1     # new revision, ~30 s
# ... demo ...
az containerapp update -g $RG -n $APP --set-env-vars BAZAAR_SHADY=0
```

## 6. Kill switches and teardown

```bash
az containerapp ingress disable -g $RG -n $APP            # instant: Bazaar unreachable
az containerapp update -g $RG -n $APP --set-env-vars BAZAAR_RATE_PER_MIN=3    # throttle harder
# suspend the `bazaar` APIM subscription in the portal: all Bazaar model calls stop, the room is unaffected

# after the workshop
az containerapp delete -g $RG -n $APP --yes
az containerapp env delete -g $RG -n $ENVNAME --yes
az acr delete -g $RG -n $ACR --yes
```

## Cost estimate (list prices, consumption plan; VERIFY in the pricing calculator)

| Item | Assumption | Cost |
|---|---|---|
| Container App, active | 0.5 vCPU + 1 GiB, ~3 h active: 0.5 x 10,800 s x $0.000024 + 1 x 10,800 x $0.000003 | ~$0.16 |
| Container App, idle (min 1) | ~9 h idle at the idle rate (~$0.000003/vCPU-s) | ~$0.08 |
| Monthly free grant | 180,000 vCPU-s + 360,000 GiB-s per subscription | likely makes the two lines above **$0** |
| Container Registry Basic | ~$0.17/day, delete afterwards | ~$0.17 |
| Log Analytics | `--logs-destination none` | $0 |
| Model tokens | ~60 attendees x ~10 calls x ~600 tokens, cheap models | < $1 |
| **Total for the day** | | **< $2** |

Scaled to zero (`--min-replicas 0`) and unused, the app itself costs $0; only the registry keeps billing until
deleted.

## Fallback: run it from your own codespace with a public port

If ACA fails or you'd rather not deploy, the same file runs in a codespace (the instructor's, never an attendee's):

```bash
python3 -m venv /tmp/bazaar-venv && /tmp/bazaar-venv/bin/pip install -q -r demos/bazaar/requirements.txt
export GENAI_BASE_URL=$(grep '^GENAI_BASE_URL=' labs/.env | cut -d= -f2)
export BAZAAR_ROOM_TOKEN=<word-on-the-slide>
export BAZAAR_PUBLIC_URL=https://$CODESPACE_NAME-8000.$GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN
cd demos/bazaar && /tmp/bazaar-venv/bin/python app.py      # uses the GENAI_API_KEY already in this codespace
```

Then Ports tab > 8000 > right-click > Port Visibility > **Public** (or
`gh codespace ports visibility 8000:public -c $CODESPACE_NAME`). Attendees use `--base $BAZAAR_PUBLIC_URL`.
Caveats: the codespace stops after its idle timeout (set it to 240 min in GitHub settings and keep a terminal
busy); GitHub rate-limits public ports; the model calls bill to the key in that codespace.
