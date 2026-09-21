// Azure Cache for Redis — Basic C0 foundation
// NOTE: Private Endpoint requires Premium SKU. Basic = TLS 1.2 + access key + no PE.
@description('Redis for sessions (sess:{user_id}:{jti}) and rate limits')
param name string
param location string
param tags object = {}

resource redis 'Microsoft.Cache/redis@2024-11-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

output id string = redis.id
output name string = redis.name
output hostName string = redis.properties.hostName
output sslPort int = redis.properties.sslPort
output stub string = 'Basic C0: no private endpoints — use TLS+auth; upgrade Premium for PE (phase-2)'
