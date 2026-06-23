<#
.SYNOPSIS
    Launcher for trip.com CLI (trip-cli)
#>
param(
    [Parameter(ValueFromRemainingArguments=$true)]
    $Args
)
$venvPy = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    & $venvPy -m trip_cli @Args
} else {
    python -m trip_cli @Args
}
