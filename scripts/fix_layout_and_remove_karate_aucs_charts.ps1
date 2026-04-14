$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$src = Join-Path $root "output\thesis_latex_equations.docx"
$out = Join-Path $root "output\thesis_latex_layout_fixed.docx"

if (-not (Test-Path $src)) {
    throw "Source file not found: $src"
}

function Trim-WordText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    return $Text.Replace("`r", "").Replace("`a", "").Replace(([char]7).ToString(), "").Trim()
}

function Paragraph-HasShape {
    param($Paragraph)
    try {
        if ($Paragraph.Range.InlineShapes.Count -gt 0) { return $true }
    } catch {}
    try {
        $count = $Paragraph.Range.ShapeRange.Count
        if ($count -gt 0) { return $true }
    } catch {}
    return $false
}

function Delete-FigureByCaptionPattern {
    param(
        $Document,
        [string[]]$Patterns
    )

    for ($i = 1; $i -le $Document.Paragraphs.Count; $i++) {
        $para = $Document.Paragraphs.Item($i)
        $text = Trim-WordText $para.Range.Text
        $matched = $true
        foreach ($pattern in $Patterns) {
            if ($text -notlike "*$pattern*") {
                $matched = $false
                break
            }
        }
        if ($matched) {
            $start = $para.Range.Start
            $end = $para.Range.End

            for ($j = $i - 1; $j -ge [Math]::Max(1, $i - 4); $j--) {
                $prev = $Document.Paragraphs.Item($j)
                $prevText = Trim-WordText $prev.Range.Text
                if (Paragraph-HasShape $prev) {
                    $start = $prev.Range.Start
                    break
                }
                if ($prevText -ne "") {
                    break
                }
                $start = $prev.Range.Start
            }

            $range = $Document.Range($start, $end)
            $range.Delete()
            return $true
        }
    }

    return $false
}

$word = $null
$doc = $null

try {
    Copy-Item $src $out -Force

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($out)

    $usableWidth = $doc.PageSetup.PageWidth - $doc.PageSetup.LeftMargin - $doc.PageSetup.RightMargin
    $targetWidth = [double]($usableWidth * 0.96)

    foreach ($shape in $doc.InlineShapes) {
        try {
            if ($shape.Width -gt $targetWidth) {
                try { $shape.LockAspectRatio = -1 } catch {}
                $shape.Width = $targetWidth
            }
        } catch {}
    }

    foreach ($shape in $doc.Shapes) {
        try {
            if ($shape.Width -gt $targetWidth) {
                try { $shape.LockAspectRatio = -1 } catch {}
                $shape.Width = $targetWidth
            }
        } catch {}
    }

    foreach ($table in $doc.Tables) {
        try {
            $table.AllowAutoFit = $true
            $table.AutoFitBehavior(2) | Out-Null
            if ($table.PreferredWidthType -ne 2) {
                $table.PreferredWidthType = 2
            }
            $table.PreferredWidth = 100
        } catch {}
    }

    $captions = @(
        @("Karate", "AUCS", "5-1"),
        @("Karate", "AUCS", "5-2"),
        @("Karate", "AUCS", "5-3")
    )

    foreach ($captionPatterns in $captions) {
        [void](Delete-FigureByCaptionPattern -Document $doc -Patterns $captionPatterns)
    }

    $doc.Save()
    $doc.Close()
    $word.Quit()

    Write-Output "DONE $out"
}
finally {
    if ($doc -ne $null) {
        try { $doc.Close() } catch {}
    }
    if ($word -ne $null) {
        try { $word.Quit() } catch {}
    }
}
