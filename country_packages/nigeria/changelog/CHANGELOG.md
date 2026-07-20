# Nigeria Country Package - Changelog

## v1.0.0 - Initial Release

Full build-out of the Nigeria Country Package (fifth and last Country
Package of the initial rollout, built against the Country Packages
Engineering Specification, same structure as Kenya's, Ghana's,
Uganda's and Tanzania's):

- `manifest.py` - package metadata, feature flags, min Kernel version
- `providers/` - OPay, PalmPay, Paga, GTBank, Access Bank, Zenith Bank, Paystack, Flutterwave, Binance Pay, Sandbox Mobile Money
- `banking/` - supported banks, NIBSS codes, settlement rules, transfer types
- `mobile_money/` - OPay, PalmPay, Paga callback shapes, status codes
- `payment_gateways/` - Paystack, Flutterwave
- `crypto/` - Binance Pay
- `taxes/` - VAT, PAYE, Companies Income Tax (turnover-tiered), Electronic Money Transfer Levy, withholding tax, payroll taxes (pension, NHF, NSITF)
- `compliance/` - KYC (NIN/BVN), AML, business registration (CAC), record retention
- `currencies/` - NGN
- `validation/` - phone, TIN, NIN, BVN, CAC registration number
- `workflows/` - large cash transaction review + electronic money transfer levy extensions
- `mappings/` - OPay, PalmPay, Paga callbacks -> canonical events
- `events/` - payment.received, payment.opay.received/.failed, payment.palmpay.received, payment.paga.received, payment.bank.completed, invoice.created/.paid, tax.filed
- `defaults/` - default Company Blueprint applied at registration
- `localization/` - locale, timezone, date format
- `monitoring/` - Regulatory Intelligence trusted sources (poller not yet wired to a live job)
- `updater/` - Update Proposal shape
- `health/` - package-level health check

Registered as `active = True` in the Country Package registry -
Nigeria is now offered at signup alongside Kenya, Ghana, Uganda and
Tanzania. This closes out the initial rollout: all five countries in
the spec's `country_packages/` list are now fully built and active.
