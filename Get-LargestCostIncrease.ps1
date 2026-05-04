<#
.SYNOPSIS
    Returns the largest cost increase from a list of costs.

.DESCRIPTION
    Given an array of cost values, this function finds the maximum increase
    between any earlier value and any later value in the array.
    If no increase exists (costs are non-increasing), it returns 0.

.PARAMETER Costs
    An array of numeric cost values.

.OUTPUTS
    [double] The largest increase found, or 0 if costs never go up.

.EXAMPLE
    Get-LargestCostIncrease -Costs 10, 7, 5, 8, 11, 9
    # Returns 6  (from 5 to 11)

.EXAMPLE
    Get-LargestCostIncrease -Costs 100, 90, 80, 70
    # Returns 0  (no increase exists)

.EXAMPLE
    $data = Import-Csv costs.csv | Select-Object -ExpandProperty Price
    Get-LargestCostIncrease -Costs $data
#>
function Get-LargestCostIncrease {
    [CmdletBinding()]
    [OutputType([double])]
    param (
        [Parameter(Mandatory, Position = 0)]
        [double[]] $Costs
    )

    if ($Costs.Count -lt 2) {
        return 0
    }

    $minSoFar = $Costs[0]
    $largestIncrease = 0

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

# Run directly from the command line:
#   pwsh Get-LargestCostIncrease.ps1 10 7 5 8 11 9
if ($MyInvocation.InvocationName -ne '.') {
    if ($args.Count -gt 0) {
        $result = Get-LargestCostIncrease -Costs ([double[]] $args)
        Write-Output "Largest cost increase: $result"
    }
}
