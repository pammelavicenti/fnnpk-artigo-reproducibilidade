param([string]$Base, [string]$Saida)
# Procura a faixa de cinco blocos (amarelo, ciano, verde, vermelho, azul) em cada canto de cada imagem.
Add-Type -AssemblyName System.Drawing
$files = Get-ChildItem $Base -Recurse -File -Filter *.png
function Hue($c) { return $c.GetHue() }
function Sat($c) { return $c.GetSaturation() }
function Bloco($h, $s, $cor) {
  if ($s -lt 0.25) { return $false }
  switch ($cor) {
    'Y' { return ($h -ge 40 -and $h -le 80) }
    'C' { return ($h -ge 160 -and $h -le 200) }
    'G' { return ($h -ge 90 -and $h -le 150) }
    'R' { return ($h -le 40 -or $h -ge 340) }
    'B' { return ($h -ge 220 -and $h -le 270) }
  }
}
$rows = foreach ($f in $files) {
  $hash = (Get-FileHash $f.FullName -Algorithm SHA256).Hash
  $img = [Drawing.Bitmap]::FromFile($f.FullName)
  $W = $img.Width; $H = $img.Height; $k = $W / 1024.0
  $ordem = 'Y','C','G','R','B'
  $melhor = 0; $canto = ''
  # canto inferior direito, direta e espelhada, e demais cantos
  $variantes = @(
    @{n='inf-dir'; x={param($i) $W-1-[int]((4-$i+0.5)*16*$k)}; y={$H-1-[int](8*$k)}},
    @{n='inf-esq'; x={param($i) [int]((4-$i+0.5)*16*$k)}; y={$H-1-[int](8*$k)}},
    @{n='sup-dir'; x={param($i) $W-1-[int]((4-$i+0.5)*16*$k)}; y={[int](8*$k)}},
    @{n='sup-esq'; x={param($i) [int]((4-$i+0.5)*16*$k)}; y={[int](8*$k)}}
  )
  foreach ($v in $variantes) {
    $acertos = 0
    for ($i = 0; $i -lt 5; $i++) {
      $x = [Math]::Min($W-1,[Math]::Max(0,(& $v.x $i))); $y = [Math]::Min($H-1,[Math]::Max(0,(& $v.y)))
      $c = $img.GetPixel($x,$y)
      if (Bloco (Hue $c) (Sat $c) $ordem[$i]) { $acertos++ }
    }
    if ($acertos -gt $melhor) { $melhor = $acertos; $canto = $v.n }
  }
  $img.Dispose()
  [pscustomobject]@{ classe=$f.Directory.Name; arquivo=$f.Name; largura=$W; altura=$H; blocos=$melhor; canto=$canto; hash=$hash }
}
$rows | Export-Csv $Saida -NoTypeInformation -Encoding UTF8
"--- tamanhos"; $rows | Group-Object { "$($_.largura)x$($_.altura)" } | Sort-Object Count -Descending | Select-Object -First 8 Name,Count | Format-Table -AutoSize
"--- blocos coincidentes (5 = marca completa)"; $rows | Group-Object classe,blocos | Sort-Object Name | Select-Object Name,Count | Format-Table -AutoSize
"--- com 4 ou 5 blocos"; $rows | Where-Object { $_.blocos -ge 4 } | Group-Object classe | Select-Object Name,Count | Format-Table -AutoSize
"--- FN"; $rows | Where-Object { $_.classe -eq 'FN' } | Select-Object arquivo,largura,altura,blocos,canto | Format-Table -AutoSize
"--- duplicatas exatas"; $rows | Group-Object hash | Where-Object { $_.Count -gt 1 } | ForEach-Object { ($_.Group | ForEach-Object { $_.classe + '/' + $_.arquivo }) -join ' = ' }
