# Contarina SOL — Technical specification 0.2

Status: isolated beta, not installed on the user's live Home Assistant.

Verified by an anonymized authenticated SOL browser session (5 Nov 2026):

| Read-only endpoint | Purpose |
| --- | --- |
| GET /api/contracts?active=all | Contracts and pagination |
| GET /api/contracts/{ref} | Contract details including household members |
| GET /api/users/areas/{ref} | Area of type 4 for collection calendar |
| GET /api/sol/ecocalendars | Map area ID to EcoCalendar |
| GET /api/sol/emptying-types | Material codes S, E, U, V, C |
| GET /api/sol/ecocalendar-emptyings | Collection events, one request for all materials |
| GET /api/services/equipment/contract/{ref} | Bin inventory and dates |
| GET /api/users/{ref}/emptyings/{COD_CONTENITORE} | Actual emptying records; ISO date-time range |
| GET /api/users/{ref}/accounting | Invoices and payment states |
| GET /api/users/{ref}/check-balance | Boolean with text/html content-type |
| GET /api/users/refresh-token | JWT refresh |

JWT duration: 3300 seconds. Refresh with a valid JWT returns a new 3300-second JWT; refresh after expiry returns HTTP 401. The integration refreshes automatically every 15 minutes, with a 30-minute expiry margin. Automatic username/password authentication is not implemented due to the browser reCAPTCHA flow.

One Home Assistant device per selected contract. Native calendar, sensors, binary sensors and aggregate-only diagnostics. Billing is polled less frequently than collection/emptying data. Requests are limited to two concurrent GETs.

Out of scope until verified: amount owed, pricing and minimum included emptyings; non-domestic multi-area behavior; uninterrupted renewal past seven days; accessible browser-based token bootstrap.

Before migration, compare the new calendar and entities to waste_collection_schedule, and update all dashboard, AWTRIX, Alexa and mobile notification dependencies. Do not remove legacy configuration without approval.
