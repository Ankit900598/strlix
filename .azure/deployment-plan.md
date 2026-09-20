# Azure Deployment Plan — Strlix hosted backend

**Status:** Deployed  
**Date:** 2026-09-20  
**Mode:** MODIFY existing PhoneCodex Azure (do not delete `phonecodex-dev` resources)  
**Recipe:** Bicep + zip-deploy Node to App Service. No `azd init -t`. No new OpenAI account.  
**Public URL:** https://phonecodex-backend.azurewebsites.net  
**Verified:** GET /health 200; POST /compile-promise 401 without secret; compile JSON with secret. Vision OFF.

## Goal

Closed APK testers call Understand over HTTPS. Use the 4-day Azure credit window for the strongest useful models, not cheapest defaults. PolicyEngine remains law. AI does not enforce.

## Architecture

| Piece | Azure |
|---|---|
| API | App Service Linux Node 20, existing RG `phonecodex-dev` |
| Models | Existing Cognitive Services / Foundry account `ay186mnc-1561-resource` |
| Speech | Existing `phonecodex-speech-dev` (unchanged) |
| Auth | `STRLIX_BACKEND_APP_SECRET` required on hosted POST routes |
| App | Android `BACKEND_BASE_URL` + secret via `local.properties` / env, not git |

## Model ladder (credit window)

| Job | Primary | Fallback |
|---|---|---|
| Promise Compiler | `gpt-6-astra` if deployable | `gpt-5.6-sol` |
| Classifier | `gpt-5.6-terra` if deployable | `gpt-5.6-luna` then current `pc-lab-best` / `pc-lab-strong` |
| Vision | strongest image-capable available | default **OFF** in app and hosted env |

## Forbidden

- Commit secrets / edit `.env`
- NSG `0.0.0.0/0`
- New OpenAI resource
- Delete PhoneCodex resources
- Let cloud AI override PolicyEngine / emergency allows
- Break localhost (`127.0.0.1:8787`, empty secret = local-open)

## Validation

- `GET /health` public HTTPS
- POST `/compile-promise` without secret = 401
- POST with secret returns compile JSON
- Local `npm start` still works
