// Application Insights linked to existing LAW — do not log tokens/PII in app code
param name string
param location string
param workspaceResourceId string
param tags object = {}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: name
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspaceResourceId
    RetentionInDays: 30
    IngestionMode: 'LogAnalytics'
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

output id string = appi.id
output name string = appi.name
output connectionString string = appi.properties.ConnectionString
output instrumentationKey string = appi.properties.InstrumentationKey
