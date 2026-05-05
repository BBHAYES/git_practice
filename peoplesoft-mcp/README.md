# PeopleSoft MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that
connects your AI assistant (e.g. Claude Desktop) directly to Oracle PeopleSoft.
Ask natural-language questions about employees, departments, purchase orders,
budgets, and more — the AI does the rest.

---

## Features

| Category | Tools |
|---|---|
| **HR** | `get_employee`, `search_employees`, `get_job_data`, `get_department`, `get_position` |
| **Finance** | `get_vendor`, `get_purchase_order`, `get_budget`, `get_voucher` |
| **PS Query** | `list_ps_queries`, `run_ps_query` |
| **Admin** | `get_system_info`, `get_business_units` |

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `python --version` |
| PeopleSoft 9.2+ | PT 8.54 or later recommended for OAuth 2.0 |
| Integration Broker enabled | REST Listening Connector active |
| Operator ID with API access | See *Permissions* section below |

---

## Quick Start

### 1. Install dependencies

```bash
cd peoplesoft-mcp
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your PeopleSoft URL, credentials, and auth method
```

Minimum `.env` for Basic Auth:
```
PEOPLESOFT_BASE_URL=https://ps.example.com:8000
PEOPLESOFT_USERNAME=PS_API_USER
PEOPLESOFT_PASSWORD=secret
```

For OAuth 2.0:
```
PEOPLESOFT_BASE_URL=https://ps.example.com:8000
PEOPLESOFT_AUTH_METHOD=oauth
PEOPLESOFT_USERNAME=PS_API_USER
PEOPLESOFT_PASSWORD=secret
PEOPLESOFT_OAUTH_CLIENT_ID=my-client-id
PEOPLESOFT_OAUTH_CLIENT_SECRET=my-client-secret
```

### 3. Run the server

```bash
# stdio transport — for Claude Desktop / local MCP clients
python server.py

# SSE transport — for web-based MCP clients
python server.py --transport sse
```

---

## Claude Desktop Integration

Add this block to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "peoplesoft": {
      "command": "python",
      "args": ["/path/to/peoplesoft-mcp/server.py"],
      "env": {
        "PEOPLESOFT_BASE_URL": "https://ps.example.com:8000",
        "PEOPLESOFT_USERNAME": "PS_API_USER",
        "PEOPLESOFT_PASSWORD": "secret"
      }
    }
  }
}
```

Restart Claude Desktop and the PeopleSoft tools will appear automatically.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `PEOPLESOFT_BASE_URL` | ✅ | — | PeopleSoft web server base URL |
| `PEOPLESOFT_USERNAME` | ✅ | — | PeopleSoft operator ID |
| `PEOPLESOFT_PASSWORD` | ✅ | — | Operator password |
| `PEOPLESOFT_AUTH_METHOD` | | `basic` | `basic` or `oauth` |
| `PEOPLESOFT_OAUTH_CLIENT_ID` | OAuth only | — | OAuth client ID |
| `PEOPLESOFT_OAUTH_CLIENT_SECRET` | OAuth only | — | OAuth client secret |
| `PEOPLESOFT_TIMEOUT` | | `30` | HTTP timeout in seconds |
| `PEOPLESOFT_VERIFY_SSL` | | `true` | Set `false` to skip TLS verification (dev only) |

---

## PeopleSoft Permissions

The operator used for API calls needs these PeopleSoft permission lists:

| Permission List | Purpose |
|---|---|
| `PTPT1000` | Integration Broker access |
| `HCCPHR1000` | HR personal/job data (HRMS) |
| `EPIB1000` | Finance / eProcurement (FSCM) |
| `PTPT4200` | PS Query runtime |

Assign via: **PeopleTools > Security > User Profiles > Roles**

---

## Tool Reference

### HR

#### `get_employee(employee_id)`
Returns personal data (name, address, date of hire, etc.) for an employee.

#### `search_employees(last_name, first_name, department_id, location_code, employee_status, max_rows)`
Searches the personal data table. All parameters are optional; at least one
filter is recommended to limit result size.

#### `get_job_data(employee_id, employee_record)`
Returns the current job row: job code, department, salary grade, FTE, standard
hours, and manager EMPLID.

#### `get_department(department_id, setid)`
Returns department description, manager, and GL ChartField defaults.

#### `get_position(position_number)`
Returns position details including budgeted FTE, job code, and department.

### Finance

#### `get_vendor(vendor_id, setid)`
Returns vendor name, address, payment terms, and status from AP.

#### `get_purchase_order(business_unit, po_id)`
Returns PO header (buyer, vendor, total amount) and line details.

#### `get_budget(business_unit, ledger_group, fiscal_year, accounting_period, department_id, account)`
Queries the commitment control (KK) ledger for budget vs. actuals balances.

#### `get_voucher(business_unit, voucher_id)`
Returns payable voucher header including vendor, invoice date, and payment status.

### PS Query

#### `list_ps_queries(name_filter, owner, max_rows)`
Lists queries available to the current user. Filter by name prefix or owner type.

#### `run_ps_query(query_name, bind_values, output_format, max_rows)`
Executes a saved PS Query. Pass bind variables as a dictionary:
```
bind_values={"BIND1": "FINANCE", "BIND2": "2024"}
```

### Admin

#### `get_system_info()`
Pings the Integration Gateway and returns database and PeopleTools version info.

#### `get_business_units(application)`
Lists all business units for `FSCM` or `HRMS`.

---

## Architecture

```
Claude Desktop / AI client
        │  MCP (stdio or SSE)
        ▼
  server.py  (FastMCP)
        │  async HTTP (httpx)
        ▼
  PeopleSoft Integration Broker
  /PSIGW/RESTListeningConnector/…
        │
        ▼
  PeopleSoft Application Server
  (HCM / FSCM / CS)
```

---

## Security Notes

- **Never commit `.env`** — it is in `.gitignore`.
- Use OAuth 2.0 instead of Basic Auth in production.
- Create a dedicated service account with the minimum required permissions.
- Use HTTPS (`PEOPLESOFT_VERIFY_SSL=true`) in all non-development environments.
- Rotate credentials and OAuth secrets regularly.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `HTTP 401` | Wrong credentials or auth method | Check username/password and `AUTH_METHOD` |
| `HTTP 403` | Missing permission list | Add required permission lists to the operator |
| `HTTP 404` | Service not found | Verify Integration Broker service name and that it is active |
| Connection refused | Wrong `BASE_URL` or firewall | Confirm URL and network path to the PeopleSoft web server |
| SSL errors | Self-signed cert | Add cert to trust store, or set `PEOPLESOFT_VERIFY_SSL=false` (dev only) |

Check Integration Broker logs in PeopleSoft:
**PeopleTools > Integration Broker > Monitor Integrations > Monitor Message**
