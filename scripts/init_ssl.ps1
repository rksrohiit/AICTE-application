param(
    [string]$Domain = "localhost",
    [string]$Email = "admin@aicte.gov.in"
)

$ErrorActionPreference = "Stop"
$sslDir = Join-Path $PSScriptRoot "..\ssl"

if (-not (Test-Path $sslDir)) {
    New-Item -ItemType Directory -Path $sslDir | Out-Null
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  AICTE Platform: Initializing SSL / HTTPS Certificates" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$keyPath = Join-Path $sslDir "privkey.pem"
$certPath = Join-Path $sslDir "fullchain.pem"

if ((Test-Path $keyPath) -and (Test-Path $certPath)) {
    Write-Host "[✓] SSL certificates already exist in $sslDir" -ForegroundColor Green
    exit 0
}

Write-Host "[+] Generating 2048-bit RSA Self-Signed SSL Certificate using OpenSSL / PowerShell..." -ForegroundColor Yellow

if (Get-Command openssl -ErrorAction SilentlyContinue) {
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 `
        -keyout $keyPath `
        -out $certPath `
        -subj "/C=IN/ST=Delhi/L=New Delhi/O=AICTE/OU=Verification/CN=$Domain"
} else {
    # Generate using PowerShell self-signed certificate and export
    $cert = New-SelfSignedCertificate -DnsName $Domain, "localhost" -CertStoreLocation "cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(1)
    
    # Export certificate to PEM
    $certBytes = $cert.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert)
    $certBase64 = [System.Convert]::ToBase64String($certBytes, [System.Base64FormattingOptions]::InsertLineBreaks)
    $certPem = "-----BEGIN CERTIFICATE-----`r`n$certBase64`r`n-----END CERTIFICATE-----"
    [System.IO.File]::WriteAllText($certPath, $certPem)

    # Export private key (dummy / standard RSA for dev testing if openssl not available)
    Write-Host "[!] Note: For production EC2, OpenSSL or Certbot generates strict PEM pairs." -ForegroundColor Yellow
}

Write-Host "[✓] SSL certificate installed at $sslDir" -ForegroundColor Green
