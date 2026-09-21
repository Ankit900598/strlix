// Strlix market backend — billion-user security foundation (small SKUs today)
// RG ONLY: rg-zevi-cloudphone (eastus2). Never touch phonecodex-* / other RGs.
targetScope = 'resourceGroup'

@description('Azure region')
param location string = resourceGroup().location

@description('Postgres region — eastus2 often blocked on Startups; use centralus')
param postgresLocation string = 'centralus'

@description('Name prefix')
param prefix string = 'zevi-strlix'

@description('Postgres admin login')
param postgresAdmin string = 'strlixadmin'

@secure()
@description('Postgres admin password — store in Key Vault after deploy')
param postgresPassword string

@description('Bootstrap firewall IPv4 for admin/migrations')
param bootstrapClientIp string = ''

@description('Existing Log Analytics workspace name')
param lawName string = 'law-zevi-strlix'

var tags = {
  project: 'strlix'
  component: 'market-backend'
  scale: 'billion-user-foundation'
  privacy: 'per-user-rls'
}

var kvName = 'kv-${prefix}'
var pgName = 'psql-${prefix}'
var redisName = 'redis-${prefix}'
var appiName = 'appi-${prefix}'

resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: lawName
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'kv'
  params: {
    name: kvName
    location: location
    tags: tags
  }
}

var fwRules = empty(bootstrapClientIp) ? [] : [
  {
    name: 'BootstrapAdmin'
    startIp: bootstrapClientIp
    endIp: bootstrapClientIp
  }
]

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    name: pgName
    location: postgresLocation
    administratorLogin: postgresAdmin
    administratorLoginPassword: postgresPassword
    databaseName: 'strlix'
    storageSizeGB: 32
    tags: tags
    firewallRules: fwRules
  }
}

module redis 'modules/redis.bicep' = {
  name: 'redis'
  params: {
    name: redisName
    location: location
    tags: tags
  }
}

module appInsights 'modules/appinsights.bicep' = {
  name: 'appinsights'
  params: {
    name: appiName
    location: location
    workspaceResourceId: law.id
    tags: tags
  }
}

output keyVaultName string = keyVault.outputs.name
output keyVaultUri string = keyVault.outputs.uri
output postgresFqdn string = postgres.outputs.fqdn
output postgresName string = postgres.outputs.name
output databaseName string = postgres.outputs.databaseName
output redisHost string = redis.outputs.hostName
output redisNote string = redis.outputs.stub
output appInsightsName string = appInsights.outputs.name
output appInsightsConnectionString string = appInsights.outputs.connectionString
