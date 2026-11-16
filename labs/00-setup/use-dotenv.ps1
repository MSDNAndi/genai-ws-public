# Drop the lab settings from the environment, so labs/.env wins again.
# Usage (dot-source it):   . .\00-setup\use-dotenv.ps1            -> this PowerShell window only
#                          . .\00-setup\use-dotenv.ps1 -Persist   -> also delete them from your Windows user
#                                                                    environment (new windows, VS Code, ...)
param([switch]$Persist)
$prefixes = 'GENAI_', 'OLLAMA_', 'LMSTUDIO_', 'FOUNDRY_LOCAL_', 'COMFYUI_', 'TTS_'
$names = Get-ChildItem Env: | Where-Object { $n = $_.Name; $prefixes | Where-Object { $n.StartsWith($_) } } |
    ForEach-Object Name
foreach ($n in $names) { Remove-Item "Env:$n"; "  removed $n (this window)" }
if ($Persist) {
    foreach ($scope in 'User') {
        $vars = [Environment]::GetEnvironmentVariables($scope).Keys |
            Where-Object { $k = $_; $prefixes | Where-Object { $k.StartsWith($_) } }
        foreach ($n in $vars) { [Environment]::SetEnvironmentVariable($n, $null, $scope); "  removed $n (Windows user profile)" }
    }
    $machine = [Environment]::GetEnvironmentVariables('Machine').Keys |
        Where-Object { $k = $_; $prefixes | Where-Object { $k.StartsWith($_) } }
    if ($machine) { "  still set machine-wide (needs an admin): $($machine -join ', ') - System Properties > Environment Variables" }
    "  Restart VS Code / terminals so they pick up the change."
}
"  Now labs/.env is used. Check with:  python 00-setup/settings.py"
