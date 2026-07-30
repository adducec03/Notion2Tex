#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Run notion2tex via Docker against a file anywhere on disk, with no need
  to clone this repo. Output is written next to the input file, exactly
  like running notion2tex locally would.

.EXAMPLE
  ./notion2tex-docker.ps1 C:\Users\me\Downloads\Export.zip

.EXAMPLE
  ./notion2tex-docker.ps1 C:\Users\me\Downloads\Export.zip --dark

.EXAMPLE
  ./notion2tex-docker.ps1 C:\Users\me\Downloads\Page.html --tex-only

.NOTES
  Always pulls the latest ":latest" from the registry first (every push to
  main republishes it), so you never run a stale cached copy. Pin a version
  instead with:
    $env:NOTION2TEX_IMAGE = "ghcr.io/adducec03/notion2tex:v1.2.3"
#>

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$InputPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    Write-Error "file not found: $InputPath"
    exit 1
}

$Image = if ($env:NOTION2TEX_IMAGE) { $env:NOTION2TEX_IMAGE } else { "ghcr.io/adducec03/notion2tex:latest" }

$ResolvedPath = Resolve-Path -LiteralPath $InputPath
$InputDir = Split-Path -Parent $ResolvedPath
$InputName = Split-Path -Leaf $ResolvedPath

docker run --rm --pull always `
    -v "${InputDir}:/data" `
    -w /data `
    $Image `
    $InputName @ExtraArgs
