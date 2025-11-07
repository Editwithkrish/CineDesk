Param([
  string]$Root = "static_site",
  [string]$Bind = "http://127.0.0.1:8000/"
)

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add($Bind)
$listener.Start()
Write-Host "Serving '$Root' at $Bind (Ctrl+C to stop)"

function Get-ContentType($path) {
  switch ([System.IO.Path]::GetExtension($path).ToLower()) {
    ".html" { return "text/html" }
    ".css"  { return "text/css" }
    ".js"   { return "application/javascript" }
    ".json" { return "application/json" }
    default  { return "text/plain" }
  }
}

while ($true) {
  $context = $listener.GetContext()
  $req = $context.Request
  $res = $context.Response
  $path = $req.Url.AbsolutePath
  if ($path -eq "/") { $path = "/index.html" }
  $file = Join-Path $Root ($path.TrimStart('/'))
  if (Test-Path $file) {
    $bytes = [System.IO.File]::ReadAllBytes($file)
    $res.ContentType = Get-ContentType($file)
    $res.OutputStream.Write($bytes, 0, $bytes.Length)
  } else {
    $res.StatusCode = 404
    $msg = [System.Text.Encoding]::UTF8.GetBytes("Not found: $path")
    $res.OutputStream.Write($msg, 0, $msg.Length)
  }
  $res.Close()
}