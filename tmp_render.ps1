param(
    [string]$Src,
    [string]$Pdf
)

$Word = New-Object -ComObject Word.Application
$Word.Visible = $false
try {
    $doc = $Word.Documents.Open($Src, $false, $true)
    try {
        $doc.Fields.Update() | Out-Null
    } catch {}
    $doc.SaveAs([ref]$Pdf, [ref]17)
    $doc.Close($false)
    Write-Host "OK: $Pdf"
} finally {
    $Word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($Word) | Out-Null
}
