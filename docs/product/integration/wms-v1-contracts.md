# WMS V1 Integration Contracts

## Scope

V1 exposes stable internal contracts for ERP, MES, PDA, Excel, manual import, and future API clients. It does not implement scheduled polling, vendor-specific adapters, or direct ERP/MES credentials.

All inbound requests must include:

- `source`: `erp`, `mes`, `pda`, `excel`, `manual`, or `api`
- `contract`: one supported inbound contract
- `idempotency_key`: unique key per source and tenant
- `payload`: contract-specific body

The platform records every accepted request in `wms_integration_request`. Repeating the same `source + idempotency_key` returns the existing result without creating another WMS document.

## Inbound Contracts

| Contract | Purpose | Required payload |
|---|---|---|
| `material` | Material master sync | `material_code`, `material_name`, optional `spec`, `unit`, `category` |
| `purchase_arrival` | ERP purchase arrival | `external_no`, `warehouse_code`, `lines[]` with `material_code`, `quantity`, optional `batch_no` |
| `sales_order` | ERP sales demand | `external_no`, `warehouse_code`, `customer_code`, `lines[]` |
| `mes_work_order` | MES work order header | `external_no`, `work_order_no`, `lines[]` |
| `bom_demand` | MES/BOM material demand | `external_no`, `work_order_no`, `lines[]` |
| `completion_inbound` | MES completion inbound request | `external_no`, `warehouse_code`, `work_order_no`, `lines[]` |

`purchase_arrival` creates a WMS arrival order in V1 and stores `external_source`, `external_id`, `external_no`, and `sync_status`. Other inbound contracts are accepted and recorded for future workflow expansion.

## Outbound Contracts

| Contract | Purpose | Query fields |
|---|---|---|
| `available_stock` | Available stock by material/batch | optional `material_code` |
| `shortage_result` | Safety stock shortage result | optional `material_code` |
| `issue_result` | Production issue flow result | optional `document_no` |
| `inbound_result` | Inbound flow result | optional `document_no` |
| `trace_result` | Batch trace result | required `batch_no` |

## Endpoints

```text
POST /wms/integration/inbound
POST /wms/integration/outbound
GET  /wms/integration/request/list
```

## Idempotency

`source + idempotency_key + tenant_id` is unique. Clients should use the upstream document number plus version, for example `ERP-PO-20260626-0001-v1`.

## Extension Rules

- Add vendor-specific mapping outside WMS core and call these contracts.
- Do not bypass WMS stock ledger services for quantity changes.
- Keep external identifiers on business documents for later reconciliation.
- Store failed adapter attempts as integration requests with `status=failed` when adapter execution is added.
