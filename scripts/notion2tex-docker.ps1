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

.EXAMPLE
  ./notion2tex-docker.ps1 --config
  # Interactive menu; saves a profile.

.EXAMPLE
  ./notion2tex-docker.ps1 --check

.NOTES
  Always pulls the latest ":latest" from the registry first (every push to
  main republishes it), so you never run a stale cached copy. Pin a version
  instead with:
    $env:NOTION2TEX_IMAGE = "ghcr.io/adducec03/notion2tex:v1.2.3"
#>

param(
    [Parameter(Position = 0)]
    [string]$InputPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

$Image = if ($env:NOTION2TEX_IMAGE) { $env:NOTION2TEX_IMAGE } else { "ghcr.io/adducec03/notion2tex:latest" }

# --config's saved profiles need to survive past a single `docker run
# --rm` (the container's own filesystem is thrown away on exit) -- mount
# the same host directory a local (non-Docker) install would use, onto
# the container path the Dockerfile exports as XDG_CONFIG_HOME.
$ConfigHostDir = Join-Path $env:APPDATA "notion2tex"
New-Item -ItemType Directory -Force -Path $ConfigHostDir | Out-Null

# --config's arrow-key menu (and any other interactive prompt) needs a
# real terminal to render -- added only when the host session actually is
# one, so this still works fine in non-interactive/piped contexts.
$TtyFlag = @()
if (-not [Console]::IsInputRedirected -and -not [Console]::IsOutputRedirected) {
    $TtyFlag = @("-it")
}

# Standalone actions that take no input file: mount the current directory
# instead of a file's parent (e.g. so a plain `notion2tex-docker.ps1
# Export.zip` run afterward has the same working directory feel).
$StandaloneFlags = @("--config", "--check", "--version", "--help", "-h")
if ([string]::IsNullOrEmpty($InputPath) -or $StandaloneFlags -contains $InputPath) {
    $PassthroughArgs = @()
    if ($InputPath) { $PassthroughArgs += $InputPath }
    $PassthroughArgs += $ExtraArgs

    docker run --rm @TtyFlag --pull always `
        -v "${PWD}:/data" `
        -v "${ConfigHostDir}:/config/notion2tex" `
        -w /data `
        $Image `
        @PassthroughArgs
    exit $LASTEXITCODE
}

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    Write-Error "file not found: $InputPath"
    exit 1
}

$ResolvedPath = Resolve-Path -LiteralPath $InputPath
$InputDir = Split-Path -Parent $ResolvedPath
$InputName = Split-Path -Leaf $ResolvedPath

docker run --rm --pull always `
    -v "${InputDir}:/data" `
    -v "${ConfigHostDir}:/config/notion2tex" `
    -w /data `
    $Image `
    $InputName @ExtraArgs
exit $LASTEXITCODE
