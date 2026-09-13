# Build script for QuantFlow PWA
param (
    [string]$TargetDir = "$PSScriptRoot",
    [string]$BuilderDir = "C:\Users\diken\AppData\Local\Temp\quantflow_builder"
)

Write-Host "=== BUILDING QUANTFLOW PWA FRONTEND ==="
Write-Host "Source Directory:  $TargetDir"
Write-Host "Builder Directory: $BuilderDir"

if (-not (Test-Path $BuilderDir)) {
    New-Item -ItemType Directory -Path $BuilderDir -Force | Out-Null
}

# 1. Sync package.json and node_modules
Copy-Item "$TargetDir\package.json" -Destination "$BuilderDir\package.json" -Force

if (-not (Test-Path "$BuilderDir\node_modules")) {
    if (Test-Path "C:\Users\diken\AppData\Local\Temp\test_npm\node_modules") {
        Write-Host "Reusing pre-installed node_modules from test_npm..."
        Copy-Item -Path "C:\Users\diken\AppData\Local\Temp\test_npm\node_modules" -Destination "$BuilderDir\node_modules" -Recurse -Force
    } else {
        Write-Host "Running npm install in builder..."
        Push-Location $BuilderDir
        cmd.exe /c "npm.cmd install"
        Pop-Location
    }
}

# 2. Sync configs and source code
Copy-Item "$TargetDir\vite.config.ts" -Destination "$BuilderDir\" -Force
Copy-Item "$TargetDir\tailwind.config.js" -Destination "$BuilderDir\" -Force
Copy-Item "$TargetDir\postcss.config.js" -Destination "$BuilderDir\" -Force
Copy-Item "$TargetDir\tsconfig.json" -Destination "$BuilderDir\" -Force
Copy-Item "$TargetDir\tsconfig.node.json" -Destination "$BuilderDir\" -Force
Copy-Item "$TargetDir\index.html" -Destination "$BuilderDir\" -Force

if (Test-Path "$TargetDir\public") {
    if (Test-Path "$BuilderDir\public") { Remove-Item -Recurse -Force "$BuilderDir\public" }
    Copy-Item -Path "$TargetDir\public" -Destination "$BuilderDir\public" -Recurse -Force
}

if (Test-Path "$TargetDir\src") {
    if (Test-Path "$BuilderDir\src") { Remove-Item -Recurse -Force "$BuilderDir\src" }
    Copy-Item -Path "$TargetDir\src" -Destination "$BuilderDir\src" -Recurse -Force
}

# 3. Execute compilation and build
Write-Host "Executing production build: tsc && vite build..."
Push-Location $BuilderDir
cmd.exe /c "npx tsc && npx vite build"
$exitCode = $LASTEXITCODE
Pop-Location

if ($exitCode -eq 0) {
    Write-Host "Compilation and build successful!"
    $destDist = "$TargetDir\dist"
    if (Test-Path $destDist) { Remove-Item -Recurse -Force $destDist }
    Copy-Item -Path "$BuilderDir\dist" -Destination $destDist -Recurse -Force
    Write-Host "Production bundle deployed to: $destDist"
    exit 0
} else {
    Write-Error "Production build failed with exit code $exitCode"
    exit $exitCode
}
