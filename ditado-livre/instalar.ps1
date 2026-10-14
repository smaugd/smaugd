# Instalador do Ditado Livre. O jeito mais fácil: clique duas vezes em instalar.bat
# (ou no PowerShell: powershell -ExecutionPolicy Bypass -File .\instalar.ps1)
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== Ditado Livre: instalação ==" -ForegroundColor Cyan

# 1) Python 3.10 ou mais novo
function Get-PythonVersion($exe, $pyArgs) {
    try {
        $out = & $exe @pyArgs -c "import sys; print(sys.version_info[0] * 100 + sys.version_info[1])" 2>$null
        if ($LASTEXITCODE -eq 0) { return [int]$out }
    } catch {}
    return 0
}
$python = $null
$pyArgs = @()
foreach ($candidate in @(@{exe = "py"; args = @("-3")}, @{exe = "python"; args = @()})) {
    $found = Get-PythonVersion $candidate.exe $candidate.args
    if ($found -ge 310) { $python = $candidate.exe; $pyArgs = $candidate.args; $version = $found; break }
}
if (-not $python) {
    Write-Host "Python 3.10+ não encontrado. Instalando o Python 3.12 pelo winget..." -ForegroundColor Yellow
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    Write-Host "Feche esta janela e rode o instalar.ps1 de novo." -ForegroundColor Yellow
    exit 1
}
Write-Host "Usando Python: $python ($version)"

# 2) Ambiente isolado (.venv) e dependências
if (-not (Test-Path ".venv")) { & $python @pyArgs -m venv .venv }
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
function Invoke-Checked { & $args[0] $args[1..($args.Length - 1)]; if ($LASTEXITCODE -ne 0) { throw "Falhou: $args" } }
Invoke-Checked $venvPython -m pip install --upgrade pip
Invoke-Checked $venvPython -m pip install -e .

# 3) Bibliotecas da placa NVIDIA (CUDA 12 + cuDNN 9) para o Whisper rodar na GPU
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    Write-Host "Placa NVIDIA detectada: instalando bibliotecas CUDA (download grande, só na primeira vez)..." -ForegroundColor Cyan
    Invoke-Checked $venvPython -m pip install -e ".[gpu]"
} else {
    Write-Host "nvidia-smi não encontrado: o Whisper vai rodar no processador (mais lento)." -ForegroundColor Yellow
    Write-Host "Se você tem placa NVIDIA, atualize o driver em https://www.nvidia.com/Download/index.aspx e rode este instalador de novo."
}

if ($env:CI) { Write-Host "CI: pulando atalho."; exit 0 }

# 4) Atalho na Área de Trabalho
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")
$shortcut = $shell.CreateShortcut((Join-Path $desktop "Ditado Livre.lnk"))
$shortcut.TargetPath = Join-Path $PSScriptRoot ".venv\Scripts\pythonw.exe"
$shortcut.Arguments = "-m ditado_livre"
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "Ditado por voz gratuito"
$shortcut.Save()

Write-Host ""
Write-Host "Pronto! Abra 'Ditado Livre' na Área de Trabalho (ou rode iniciar.bat)." -ForegroundColor Green
Write-Host "Para a limpeza com IA local, instale o Ollama (https://ollama.com) e rode: ollama pull qwen2.5:3b"
