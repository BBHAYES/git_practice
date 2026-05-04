<#
.SYNOPSIS
    Returns the largest cost increase (or top N increases) from a list of costs.

.DESCRIPTION
    Given an array of cost values, this function finds the maximum increase
    between any earlier value and any later value in the array.
    If no increase exists (costs are non-increasing), it returns 0.

    When -Top N is specified the function returns the N largest period-over-period
    increases as objects with From, To, and Increase properties, sorted from
    largest to smallest increase.

.PARAMETER Costs
    An array of numeric cost values.

.PARAMETER Top
    Optional. When provided, returns the top N largest period-over-period
    increases as objects (From, To, Increase) instead of a single number.

.OUTPUTS
    Without -Top : [double] The largest increase found, or 0 if costs never go up.
    With    -Top : [PSCustomObject[]] Array of objects with From, To, Increase.

.EXAMPLE
    Get-LargestCostIncrease -Costs 10, 7, 5, 8, 11, 9
    # Returns 6  (from 5 to 11)

.EXAMPLE
    Get-LargestCostIncrease -Costs 100, 90, 80, 70
    # Returns 0  (no increase exists)

.EXAMPLE
    Get-LargestCostIncrease -Costs 3, 10, 6, 15, 8, 20, 4, 18 -Top 3
    # Returns the 3 largest period-over-period increases as objects:
    #   From  To  Increase
    #   ----  --  --------
    #      4  18        14
    #      6  15         9
    #      3  10         7

.EXAMPLE
    $data = Import-Csv costs.csv | Select-Object -ExpandProperty Price
    Get-LargestCostIncrease -Costs $data -Top 10
#>
function Get-LargestCostIncrease {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory, Position = 0)]
        [double[]] $Costs,

        [Parameter()]
        [ValidateRange(1, [int]::MaxValue)]
        [int] $Top
    )

    if ($PSBoundParameters.ContainsKey('Top')) {
        # Return the top N period-over-period increases as objects.
        $increases = for ($i = 1; $i -lt $Costs.Count; $i++) {
            $diff = $Costs[$i] - $Costs[$i - 1]
            if ($diff -gt 0) {
                [PSCustomObject]@{
                    From     = $Costs[$i - 1]
                    To       = $Costs[$i]
                    Increase = $diff
                }
            }
        }

        if ($null -eq $increases) {
            return @()
        }

        return $increases |
            Sort-Object -Property Increase -Descending |
            Select-Object -First $Top
    }
    else {
        # Default: return the single largest increase (any earlier→later pair).
        if ($Costs.Count -lt 2) {
            return [double] 0
        }

        $minSoFar = $Costs[0]
        $largestIncrease = [double] 0

        for ($i = 1; $i -lt $Costs.Count; $i++) {
            $increase = $Costs[$i] - $minSoFar

            if ($increase -gt $largestIncrease) {
                $largestIncrease = $increase
            }

            if ($Costs[$i] -lt $minSoFar) {
                $minSoFar = $Costs[$i]
            }
        }

        return $largestIncrease
    }
}

# Run directly from the command line:
#   pwsh Get-LargestCostIncrease.ps1 10 7 5 8 11 9
#   pwsh Get-LargestCostIncrease.ps1 -Top 3 10 7 5 8 11 9
if ($MyInvocation.InvocationName -ne '.') {
    $topN = $null
    $costArgs = @()

    # Parse optional -Top <n> from $args
    $i = 0
    while ($i -lt $args.Count) {
        if ($args[$i] -eq '-Top' -and ($i + 1) -lt $args.Count) {
            $topN = [int] $args[$i + 1]
            $i += 2
        }
        else {
            $costArgs += [double] $args[$i]
            $i++
        }
    }

    if ($costArgs.Count -gt 0) {
        if ($null -ne $topN) {
            $results = Get-LargestCostIncrease -Costs $costArgs -Top $topN
            $results | Format-Table -AutoSize
        }
        else {
            $result = Get-LargestCostIncrease -Costs $costArgs
            Write-Output "Largest cost increase: $result"
        }
    }
}
