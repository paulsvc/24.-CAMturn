# PowerShell launch script for LatheCAM
$env:PYTHONPATH = "$PSScriptRoot\src"
python -m lathecam.main @args
