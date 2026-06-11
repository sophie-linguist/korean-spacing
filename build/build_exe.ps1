param(
    [string]$DictDbPath = "dict.db"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$spec = Join-Path $PSScriptRoot "korean-spacing.spec"

# 스펙 파일을 소스로 빌드(웹 UI 엔트리 + HTML/사전 JSON 번들 + pywebview 수집).
python -m PyInstaller $spec --noconfirm --distpath $dist --workpath (Join-Path $root "build\pyi-build")

if (Test-Path -LiteralPath (Join-Path $root $DictDbPath)) {
    Copy-Item -LiteralPath (Join-Path $root $DictDbPath) -Destination (Join-Path $dist "dict.db") -Force
    "copied dict.db to dist"
} else {
    "dict.db not found at $DictDbPath (sidecar copy skipped)"
}
