$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$outputDir = Join-Path $root "output"
$srcItem = Get-ChildItem $outputDir -Filter *.docx |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($null -eq $srcItem) {
    throw "Source thesis not found in output directory."
}

$src = $srcItem.FullName
$out = Join-Path $outputDir "thesis_latex_equations.docx"

if (-not (Test-Path $src)) {
    throw "Source thesis not found: $src"
}

function Set-EquationParagraph {
    param(
        [Parameter(Mandatory = $true)] $Document,
        [Parameter(Mandatory = $true)] $Paragraph,
        [Parameter(Mandatory = $true)] [string] $Latex,
        [Parameter(Mandatory = $true)] [string] $Number
    )

    $availWidth = $Document.PageSetup.PageWidth - $Document.PageSetup.LeftMargin - $Document.PageSetup.RightMargin
    $paragraphText = "`t$Latex`t($Number)"

    $Paragraph.Range.Text = $paragraphText
    $Paragraph.Format.TabStops.ClearAll()
    $null = $Paragraph.Format.TabStops.Add($availWidth / 2, 1, 0)
    $null = $Paragraph.Format.TabStops.Add($availWidth, 2, 0)
    $Paragraph.Alignment = 0
    $Paragraph.Range.ParagraphFormat.SpaceBefore = 0
    $Paragraph.Range.ParagraphFormat.SpaceAfter = 0
    $Paragraph.Range.ParagraphFormat.LineSpacingRule = 0
    $Paragraph.Range.ParagraphFormat.FirstLineIndent = 0
    $Paragraph.Range.ParagraphFormat.LeftIndent = 0
    $Paragraph.Range.ParagraphFormat.RightIndent = 0

    $formulaRange = $Paragraph.Range.Duplicate
    $find = $formulaRange.Find
    $find.ClearFormatting()
    $find.Text = $Latex
    $find.Forward = $true
    $find.Wrap = 0

    if ($find.Execute()) {
        $null = $Document.OMaths.Add($formulaRange)
        $Document.OMaths.Item($Document.OMaths.Count).BuildUp()
    } else {
        throw "Unable to locate formula text after paragraph rewrite: $Latex"
    }
}

function Find-ParagraphByPatterns {
    param(
        [Parameter(Mandatory = $true)] $Document,
        [Parameter(Mandatory = $true)] [string[]] $Patterns
    )

    foreach ($paragraph in $Document.Paragraphs) {
        $text = $paragraph.Range.Text.Trim()
        $matched = $true
        foreach ($pattern in $Patterns) {
            if ($text -notlike "*$pattern*") {
                $matched = $false
                break
            }
        }
        if ($matched) {
            return $paragraph
        }
    }

    throw "Could not find target paragraph by patterns: $($Patterns -join ' | ')"
}

function Replace-ParagraphWithEquation {
    param(
        [Parameter(Mandatory = $true)] $Document,
        [Parameter(Mandatory = $true)] [string[]] $Patterns,
        [Parameter(Mandatory = $true)] [string] $Latex,
        [Parameter(Mandatory = $true)] [string] $Number
    )

    $paragraph = Find-ParagraphByPatterns -Document $Document -Patterns $Patterns
    Set-EquationParagraph -Document $Document -Paragraph $paragraph -Latex $Latex -Number $Number
}

$word = $null
$doc = $null

try {
    Copy-Item $src $out -Force

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0

    $doc = $word.Documents.Open($out)

    Replace-ParagraphWithEquation `
        -Document $doc `
        -Patterns @("Q = (1 / 2m)", "A_ij - k_i k_j / 2m", "c_i, c_j") `
        -Latex "Q=\frac{1}{2m}\sum_{ij}\left(A_{ij}-\frac{k_i k_j}{2m}\right)\delta(c_i,c_j)" `
        -Number "2-1"

    Replace-ParagraphWithEquation `
        -Document $doc `
        -Patterns @("F_", "(1 -", ")D") `
        -Latex "F_{\lambda}=\lambda Q+(1-\lambda)D" `
        -Number "2-2"

    Replace-ParagraphWithEquation `
        -Document $doc `
        -Patterns @("pr = (", "p_e", "p_w") `
        -Latex "pr=\frac{p_e+p_w}{2}" `
        -Number "2-3"

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
