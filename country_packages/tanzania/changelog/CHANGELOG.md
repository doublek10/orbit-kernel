# Tanzania Country Package - Changelog

## v1.0.0 - Initial Release

Full build-out of the Tanzania Country Package (fourth Country Package
built against the Country Packages Engineering Specification, same
structure as Kenya's, Ghana's and Uganda's):

- `manifest.py` - package metadata, feature flags, min Kernel version
- `providers/` - M-Pesa (Vodacom), Tigo Pesa, HaloPesa, Airtel Money, CRDB Bank, NMB Bank, Flutterwave, Binance Pay, Sandbox Mobile Money
- `banking/` - supported banks, clearing codes, settlement rules, transfer types
- `mobile_money/` - M-Pesa, Tigo Pesa, HaloPesa callback shapes, status codes
- `payment_gateways/` - Flutterwave
- `crypto/` - Binance Pay
- `taxes/` - VAT, PAYE, corporate tax, mobile money levy, withholding tax, payroll taxes (NSSF, SDL)
- `compliance/` - KYC, AML, business registration, record retention
- `currencies/` - TZS
- `validation/` - phone, TIN, NIDA National ID, business registration number
- `workflows/` - large cash transaction review + mobile money levy extensions
- `mappings/` - M-Pesa, Tigo Pesa, HaloPesa callbacks -> canonical events
- `events/` - payment.received, payment.mpesa.received/.failed, payment.tigo_pesa.received/.failed, payment.halopesa.received, payment.bank.completed, invoice.created/.paid, tax.filed
- `defaults/` - default Company Blueprint applied at registration
- `localization/` - locale, timezone, date format
- `monitoring/` - Regulatory Intelligence trusted sources (poller not yet wired to a live job)
- `updater/` - Update Proposal shape
- `health/` - package-level health check

Registered as `active = True` in the Country Package registry -
Tanzania is now offered at signup alongside Kenya, Ghana and Uganda.
Nigeria is next and last in the initial rollout.
