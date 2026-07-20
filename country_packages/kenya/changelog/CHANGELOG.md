# Kenya Country Package - Changelog

## v1.0.0 - Initial Release

Full build-out of the Kenya Country Package (first Country Package built
against the Country Packages Engineering Specification):

- `manifest.py` - package metadata, feature flags, min Kernel version
- `providers/` - M-Pesa, Airtel Money, KCB Bank, Equity Bank, Flutterwave, Binance Pay, Sandbox Mobile Money
- `banking/` - supported banks, bank codes, settlement rules, transfer types
- `mobile_money/` - M-Pesa and Airtel Money IPN/callback shapes, status codes
- `payment_gateways/` - Flutterwave
- `crypto/` - Binance Pay
- `taxes/` - VAT, PAYE, corporate tax, digital service tax, withholding tax, payroll taxes
- `compliance/` - KYC, AML, business registration, record retention
- `currencies/` - KES
- `validation/` - phone, KRA PIN, national ID, business registration number, postal code
- `workflows/` - large cash transaction review extension
- `mappings/` - M-Pesa STK callback, Airtel Money callback -> canonical events
- `events/` - payment.received, payment.mpesa.received/.failed, payment.bank.completed, invoice.created/.paid, tax.filed
- `defaults/` - default Company Blueprint applied at registration
- `localization/` - locale, timezone, date format
- `monitoring/` - Regulatory Intelligence trusted sources (poller not yet wired to a live job)
- `updater/` - Update Proposal shape
- `health/` - package-level health check

Registered as `active = True` in the Country Package registry - this is
the only Country Package the Frontend offers at signup until Uganda is
built out the same way.
