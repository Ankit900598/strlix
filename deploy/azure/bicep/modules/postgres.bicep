// Azure Database for PostgreSQL Flexible Server — Burstable B1ms foundation
// Encryption at rest: Azure-managed (CMEK = phase-2). TLS required.
@description('Postgres Flexible Server for multi-tenant market data + RLS')
param name string
param location string
param administratorLogin string
@secure()
param administratorLoginPassword string
param databaseName string = 'strlix'
param storageSizeGB int = 32
param tags object = {}
param firewallRules array = [] // [{name, startIp, endIp}]

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: administratorLogin
    administratorLoginPassword: administratorLoginPassword
    storage: {
      storageSizeGB: storageSizeGB
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    // Public access: CAE has no VNet. Private access needs delegated subnet (phase-2 GP + VNet).
    network: {
      publicNetworkAccess: 'Enabled'
    }
    authConfig: {
      activeDirectoryAuth: 'Disabled'
      passwordAuth: 'Enabled'
    }
  }
}

resource cfgRequireSSL 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2024-08-01' = {
  parent: pg
  name: 'require_secure_transport'
  properties: {
    value: 'on'
    source: 'user-override'
  }
}

resource db 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: databaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource allowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = {
  parent: pg
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource extraRules 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2024-08-01' = [for (rule, i) in firewallRules: {
  parent: pg
  name: rule.name
  properties: {
    startIpAddress: rule.startIp
    endIpAddress: rule.endIp
  }
}]

output id string = pg.id
output name string = pg.name
output fqdn string = pg.properties.fullyQualifiedDomainName
output databaseName string = db.name
