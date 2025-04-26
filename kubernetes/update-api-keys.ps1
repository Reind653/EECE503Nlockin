param(
    [Parameter(Mandatory=$true)]
    [string]$OpenAIKey,
    
    [Parameter(Mandatory=$true)]
    [string]$AnthropicKey
)

$secretFile = "manifests/api-keys-secret.yaml"
$secretContent = Get-Content -Path $secretFile -Raw

$secretContent = $secretContent -replace '"YOUR_OPENAI_API_KEY"', "`"$OpenAIKey`""
$secretContent = $secretContent -replace '"YOUR_ANTHROPIC_API_KEY"', "`"$AnthropicKey`""

Set-Content -Path $secretFile -Value $secretContent

Write-Host "API keys updated in $secretFile" 