// Container App ca-market-api — system-assigned MI, Key Vault refs, ACR pull
param name string
param location string
param environmentId string
param acrLoginServer string
param image string
param keyVaultUri string
param tags object = {}
@description('Min replicas; 0 saves credits when idle')
param minReplicas int = 0
param maxReplicas int = 3

resource ca 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        allowInsecure: false
        transport: 'Auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: 'system'
        }
      ]
      secrets: [
        {
          name: 'database-url'
          keyVaultUrl: '${keyVaultUri}secrets/database-url'
          identity: 'system'
        }
        {
          name: 'jwt-secret'
          keyVaultUrl: '${keyVaultUri}secrets/jwt-secret'
          identity: 'system'
        }
        {
          name: 'redis-url'
          keyVaultUrl: '${keyVaultUri}secrets/redis-url'
          identity: 'system'
        }
        {
          name: 'redis-password'
          keyVaultUrl: '${keyVaultUri}secrets/redis-password'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'market-api'
          image: image
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'PORT', value: '8080' }
            { name: 'STRLIX_PAY_MODE', value: 'test' }
            { name: 'STRLIX_JWT_ISS', value: 'strlix-market' }
            { name: 'STRLIX_JWT_AUD', value: 'market-api' }
            { name: 'STRLIX_JWT_ACCESS_TTL_SEC', value: '900' }
            { name: 'STRLIX_JWT_REFRESH_TTL_SEC', value: '604800' }
            { name: 'STRLIX_DATABASE_URL', secretRef: 'database-url' }
            { name: 'STRLIX_JWT_SECRET', secretRef: 'jwt-secret' }
            { name: 'STRLIX_REDIS_URL', secretRef: 'redis-url' }
            { name: 'STRLIX_REDIS_PASSWORD', secretRef: 'redis-password' }
            { name: 'STRLIX_CORS_ORIGINS', value: '*' }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: { path: '/health', port: 8080 }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: { path: '/ready', port: 8080 }
              initialDelaySeconds: 5
              periodSeconds: 10
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
    }
  }
}

output id string = ca.id
output name string = ca.name
output fqdn string = ca.properties.configuration.ingress.fqdn
output principalId string = ca.identity.principalId
