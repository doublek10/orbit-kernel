# Uganda Country Package - Changelog

## v1.0.0 - Initial Release

Full build-out of the Uganda Country Package (third Country Package
built against the Country Packages Engineering Specification, same
structure as Kenya's and Ghana's):

- `manifest.py` - package metadata, feature flags, min Kernel version
- `providers/` - MTN Mobile Money, Airtel Money, Stanbic Bank Uganda, Centenary Bank, Flutterwave, Binance Pay, Sandbox Mobile Money
- `banking/` - supported banks, clearing codes, settlement rules, transfer types
- `mobile_money/` - MTN Mobile Money, Airtel Money callback shapes, status codes
- `payment_gateways/` - Flutterwave
- `crypto/` - Binance Pay
- `taxes/` - VAT, PAYE, corporate tax, mobile money levy, withholding tax, payroll taxes (NSSF, local service tax)
- `compliance/` - KYC, AML, business registration, record retention
- `currencies/` - UGX
- `validation/` - phone, TIN, National ID Number (NIN), business registration number
- `workflows/` - large cash transaction review + mobile money levy extensions
- `mappings/` - MTN MoMo, Airtel Money callbacks -> canonical events
- `events/` - payment.received, payment.mtn_momo.received/.failed, payment.airtel.received/.failed, payment.bank.completed, invoice.created/.paid, tax.filed
- `defaults/` - default Company Blueprint applied at registration
- `localization/` - locale, timezone, date format
- `monitoring/` - Regulatory Intelligence trusted sources (poller not yet wired to a live job)
- `updater/` - Update Proposal shape
- `health/` - package-level health check

Registered as `active = True` in the Country Package registry - Uganda
is now offered at signup alongside Kenya and Ghana. Next up: Tanzania,
Nigeria.
