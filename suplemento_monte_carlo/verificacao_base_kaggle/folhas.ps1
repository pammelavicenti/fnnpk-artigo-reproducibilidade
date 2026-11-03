param([string]$Base, [string]$Csv, [string]$Saida)
Add-Type -AssemblyName System.Drawing
$r = Import-Csv $Csv
"--- cruzamento: quadrada 1024x1024 x marca completa"
$r | Group-Object { "$(if ($_.largura -eq '1024' -and $_.altura -eq '1024') {'1024x1024'} else {'outro'}) | blocos=$($_.blocos)" } | Sort-Object Name | Select-Object Name,Count | Format-Table -AutoSize
"--- por classe: com marca / total"
$r | Group-Object classe | ForEach-Object { "{0}: {1}/{2}" -f $_.Name, (($_.Group | Where-Object { [int]$_.blocos -eq 5 }).Count), $_.Count }
function Folha($lista, $arq, $col) {
  $t = 256; $n = $lista.Count; $lin = [Math]::Ceiling($n / $col)
  $bmp = New-Object Drawing.Bitmap(($col*$t),($lin*($t+22))); $g = [Drawing.Graphics]::FromImage($bmp); $g.Clear([Drawing.Color]::White)
  $fnt = New-Object Drawing.Font('Arial',10)
  for ($i=0;$i -lt $n;$i++) {
    $it = $lista[$i]; $p = Join-Path (Join-Path $Base ('FNNPK\' + $it.classe)) $it.arquivo
    if (-not (Test-Path $p)) { $p = (Get-ChildItem $Base -Recurse -File -Filter $it.arquivo | Select-Object -First 1).FullName }
    $im = [Drawing.Image]::FromFile($p)
    $x = ($i % $col)*$t; $y = [Math]::Floor($i/$col)*($t+22)
    $g.DrawImage($im,$x+2,$y+20,$t-4,$t-4); $g.DrawString("$($it.classe)/$($it.arquivo) b=$($it.blocos)",$fnt,[Drawing.Brushes]::Black,$x+2,$y+2)
    $im.Dispose()
  }
  $bmp.Save($arq); $g.Dispose(); $bmp.Dispose()
}
Folha @($r | Where-Object { $_.classe -eq 'FN' } | Select-Object -First 8) (Join-Path $Saida 'fn.png') 4
$com = @($r | Where-Object { $_.classe -ne 'FN' -and [int]$_.blocos -eq 5 } | Get-Random -Count 8 -SetSeed 7)
Folha $com (Join-Path $Saida 'def_com_marca.png') 4
$sem = @($r | Where-Object { [int]$_.blocos -le 1 } | Get-Random -Count 12 -SetSeed 7)
Folha $sem (Join-Path $Saida 'sem_marca.png') 4
# recorte ampliado do canto de uma imagem sem marca e de uma com marca
$p1 = (Get-ChildItem $Base -Recurse -File -Filter 'fn1.png' | Select-Object -First 1).FullName
$im = [Drawing.Image]::FromFile($p1); $o = New-Object Drawing.Bitmap(640,240); $g = [Drawing.Graphics]::FromImage($o); $g.InterpolationMode='NearestNeighbor'
$g.DrawImage($im,(New-Object Drawing.Rectangle(0,0,640,240)),(New-Object Drawing.Rectangle(($im.Width-120),($im.Height-45),120,45)),[Drawing.GraphicsUnit]::Pixel)
$o.Save((Join-Path $Saida 'canto_fn1.png')); $g.Dispose(); $o.Dispose(); $im.Dispose()
