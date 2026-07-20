# Ghana Country Package - Changelog

## v1.0.0 - Initial Release

Full build-out of the Ghana Country Package (second Country Package
built against the Country Packages Engineering Specification, same
structure as Kenya's):

- `manifest.py` - package metadata, feature flags, min Kernel version
- `providers/` - MTN MoMo, Vodafone Cash, AirtelTigo Money, GCB Bank, Ecobank Ghana, Paystack, Flutterwave, Binance Pay, Sandbox Mobile Money
- `banking/` - supported banks, sort codes, settlement rules, transfer types
- `mobile_money/` - MTN MoMo, Vodafone Cash, AirtelTigo Money callback shapes, status codes
- `payment_gateways/` - Paystack, Flutterwave
- `crypto/` - Binance Pay
- `taxes/` - VAT + NHIL/GETFund/COVID levies, PAYE, corporate tax, electronic transfer levy, withholding tax, payroll taxes
- `compliance/` - KYC, AML, business registration, record retention
- `currencies/` - GHS
- `validation/` - phone, TIN, Ghana Card, business registration number, GhanaPost GPS address
- `workflows/` - large cash transaction review + e-levy extensions
- `mappings/` - MTN MoMo, Vodafone Cash callbacks -> canonical events
- `events/` - payment.received, payment.mtn_momo.received/.failed, payment.vodafone_cash.received, payment.bank.completed, invoice.created/.paid, tax.filed
- `defaults/` - default Company Blueprint applied at registration
- `localization/` - locale, timezone, date format
- `monitoring/` - Regulatory Intelligence trusted sources (poller not yet wired to a live job)
- `updater/` - Update Proposal shape
- `health/` - package-level health check

Registered as `active = True` in the Country Package registry - Ghana
is now offered at signup alongside Kenya. Next up: Uganda, Tanzania,
Nigeria.
