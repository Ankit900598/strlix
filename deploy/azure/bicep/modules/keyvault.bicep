// Key Vault — RBAC, soft-delete, purge protection (best practice: never disable purge protection)
@description('Key Vault for Strlix secrets (DB, JWT, payment test keys)')
param name string
param location string
param tags object = {}

resource kv 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled' // Phase-2: private endpoint + VNet
    networkAcls: {
      defaultAction: 'Allow' // tighten when PE + ACA VNet ready
      bypass: 'AzureServices'
    }
  }
}

output id string = kv.id
output name string = kv.name
output uri string = kv.properties.vaultUri
