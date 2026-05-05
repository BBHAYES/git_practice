"""
PeopleSoft MCP Server
=====================
A Model Context Protocol server that exposes PeopleSoft HR, Finance, and
Query tools to any MCP-compatible AI client (e.g. Claude Desktop).

Run with:
    python server.py               # stdio transport (default for Claude Desktop)
    python server.py --transport sse  # SSE transport for web clients
"""

from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP

from client import PeopleSoftClient, client_from_env

load_dotenv()

# ---------------------------------------------------------------------------
# Lifespan: create / close the shared HTTP client
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict[str, Any]]:  # type: ignore[type-arg]
    ps_client = client_from_env()
    async with ps_client:
        yield {"ps": ps_client}


mcp = FastMCP(
    name="PeopleSoft MCP",
    instructions=(
        "Tools for querying and managing Oracle PeopleSoft data including "
        "HR (employees, jobs, departments), Finance (vendors, purchase orders, "
        "budgets), and running PeopleSoft Queries."
    ),
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Helper: extract the shared client from the MCP context
# ---------------------------------------------------------------------------

def _ps(ctx: Context) -> PeopleSoftClient:
    return ctx.request_context.lifespan_context["ps"]


# ---------------------------------------------------------------------------
# ── HR Tools ────────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_employee(employee_id: str, *, ctx: Context) -> dict[str, Any]:
    """Get personal and employment data for a single employee by Employee ID.

    Args:
        employee_id: The PeopleSoft EMPLID (e.g. "00001234").
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path("HRMS", "CI_PERSONAL_DATA", employee_id)
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def search_employees(
    last_name: str = "",
    first_name: str = "",
    department_id: str = "",
    location_code: str = "",
    employee_status: str = "A",
    max_rows: int = 50,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Search for employees by name, department, or location.

    Args:
        last_name: Partial or full last name (case-insensitive).
        first_name: Partial or full first name (case-insensitive).
        department_id: PeopleSoft department code (e.g. "FINANCE").
        location_code: Site/location code.
        employee_status: "A" = Active, "I" = Inactive, "T" = Terminated. Default "A".
        max_rows: Maximum number of rows to return (1–200). Default 50.
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {"MAXROWS": min(max(1, max_rows), 200)}
    if last_name:
        params["LAST_NAME"] = last_name.upper()
    if first_name:
        params["FIRST_NAME"] = first_name.upper()
    if department_id:
        params["DEPTID"] = department_id
    if location_code:
        params["LOCATION"] = location_code
    if employee_status:
        params["EMPL_STATUS"] = employee_status

    try:
        data = await ps.get(ps.ib_path("HRMS", "CI_PERSONAL_DATA"), **params)
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_job_data(
    employee_id: str,
    employee_record: int = 0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Get the current job assignment (title, department, salary grade, etc.)
    for an employee.

    Args:
        employee_id: The PeopleSoft EMPLID.
        employee_record: Employee record number (default 0 for primary job).
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path("HRMS", "CI_JOB_DATA", employee_id, str(employee_record))
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_department(department_id: str, setid: str = "", *, ctx: Context) -> dict[str, Any]:
    """Retrieve department information including description and manager.

    Args:
        department_id: The PeopleSoft department code (e.g. "FINANCE").
        setid: Optional TableSet ID. Defaults to the installation default.
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {}
    if setid:
        params["SETID"] = setid
    try:
        data = await ps.get(
            ps.ib_path("HRMS", "CI_DEPT_TBL", department_id), **params
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_position(position_number: str, *, ctx: Context) -> dict[str, Any]:
    """Get details for a specific position (job code, FTE, department, etc.).

    Args:
        position_number: PeopleSoft position number (e.g. "00001234").
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path("HRMS", "CI_POSITION_DATA", position_number)
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# ── Finance Tools ────────────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_vendor(vendor_id: str, setid: str = "", *, ctx: Context) -> dict[str, Any]:
    """Look up a vendor (supplier) record from PeopleSoft Payables.

    Args:
        vendor_id: PeopleSoft vendor ID.
        setid: Optional TableSet ID.
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {}
    if setid:
        params["SETID"] = setid
    try:
        data = await ps.get(
            ps.ib_path("FSCM", "CI_VENDOR", vendor_id), **params
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_purchase_order(
    business_unit: str,
    po_id: str,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Retrieve a Purchase Order header and line details.

    Args:
        business_unit: PeopleSoft business unit (e.g. "US001").
        po_id: Purchase order number (e.g. "0000012345").
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path("FSCM", "CI_PO_HDR", business_unit, po_id)
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_budget(
    business_unit: str,
    ledger_group: str,
    fiscal_year: int = 0,
    accounting_period: int = 0,
    department_id: str = "",
    account: str = "",
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Query budget ledger balances from PeopleSoft General Ledger.

    Args:
        business_unit: PeopleSoft business unit (e.g. "US001").
        ledger_group: Ledger group name (e.g. "ACTUALS").
        fiscal_year: Fiscal year (0 = current year).
        accounting_period: Accounting period 1–12 (0 = all periods).
        department_id: Optional department filter.
        account: Optional GL account filter.
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {"BUSINESS_UNIT": business_unit, "LEDGER_GROUP": ledger_group}
    if fiscal_year:
        params["FISCAL_YEAR"] = fiscal_year
    if accounting_period:
        params["ACCOUNTING_PERIOD"] = accounting_period
    if department_id:
        params["DEPTID"] = department_id
    if account:
        params["ACCOUNT"] = account
    try:
        data = await ps.get(ps.ib_path("FSCM", "CI_LEDGER_KK"), **params)
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_voucher(
    business_unit: str,
    voucher_id: str,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Retrieve a Payables voucher (invoice) by business unit and voucher ID.

    Args:
        business_unit: PeopleSoft business unit (e.g. "US001").
        voucher_id: Voucher ID (e.g. "00001234").
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path("FSCM", "CI_VCHR_HDR", business_unit, voucher_id)
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# ── PeopleSoft Query Tools ───────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_ps_queries(
    name_filter: str = "",
    owner: str = "",
    max_rows: int = 100,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """List available PeopleSoft Queries accessible to the current user.

    Args:
        name_filter: Optional partial query name to filter results.
        owner: Optional owner type: "P" = Public, "U" = User private.
        max_rows: Maximum number of queries to return (default 100).
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {"MAXROWS": min(max(1, max_rows), 500)}
    if name_filter:
        params["QRYNAME"] = name_filter.upper()
    if owner:
        params["QRYOWNER"] = owner
    try:
        data = await ps.get(ps.ib_path("QUERY", "QUERY_LIST"), **params)
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def run_ps_query(
    query_name: str,
    bind_values: dict[str, str] | None = None,
    output_format: str = "json",
    max_rows: int = 500,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """Execute a PeopleSoft Query and return the results.

    Args:
        query_name: The name of the PS Query to run (e.g. "HR_DEPT_LIST").
        bind_values: Optional dictionary of PeopleSoft bind variable names to
                     values. Keys must match the bind variable names defined in
                     the query (e.g. {"BIND1": "FINANCE", "BIND2": "2024"}).
        output_format: "json" or "xml". Default "json".
        max_rows: Maximum rows to return (1–2000). Default 500.
    """
    ps = _ps(ctx)
    params: dict[str, Any] = {
        "QRYNAME": query_name.upper(),
        "MAXROWS": min(max(1, max_rows), 2000),
        "OUTFORMAT": output_format.upper(),
    }
    if bind_values:
        params.update(bind_values)

    try:
        data = await ps.get(ps.ib_path("QUERY", "QUERY_RUN"), **params)
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# ── System / Admin Tools ─────────────────────────────────────────────────────
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_system_info(*, ctx: Context) -> dict[str, Any]:
    """Return PeopleSoft environment metadata: tools version, database,
    and integration gateway status."""
    ps = _ps(ctx)
    try:
        data = await ps.get(ps.ib_path("PSIGW", "PingDatabase"))
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@mcp.tool()
async def get_business_units(application: str = "FSCM", *, ctx: Context) -> dict[str, Any]:
    """List business units defined in the PeopleSoft installation.

    Args:
        application: "FSCM" (default) or "HRMS".
    """
    ps = _ps(ctx)
    try:
        data = await ps.get(
            ps.ib_path(application, "CI_BUS_UNIT_TBL"),
            MAXROWS=200,
        )
        return {"success": True, "data": data}
    except httpx.HTTPStatusError as exc:
        return {"success": False, "error": f"HTTP {exc.response.status_code}", "detail": exc.response.text}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    transport = "stdio"
    if "--transport" in sys.argv:
        idx = sys.argv.index("--transport")
        if idx + 1 < len(sys.argv):
            transport = sys.argv[idx + 1]

    if transport == "sse":
        mcp.run(transport="sse")
    else:
        mcp.run(transport="stdio")
