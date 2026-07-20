# Uganda Country Package

Third Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's and Ghana's.
`active = True` in `manifest.py` - Uganda is now offered as a signup
option alongside Kenya and Ghana.

Contributes: providers (MTN Mobile Money, Airtel Money, Stanbic Bank
Uganda, Centenary Bank, Flutterwave, Binance Pay), banking rules, tax
configuration (VAT, PAYE, corporate tax, mobile money levy,
withholding, payroll/NSSF), compliance (KYC/AML), UGX currency,
Uganda-specific validation (phone/TIN/NIN), provider payload mappings,
country events, the default Company Blueprint applied at registration,
localization, regulatory monitoring sources, and the update-proposal
shape.

Loaded dynamically by the Plugin Manager
(`country_packages/loader.py`) based on a company's `country` field -
see `country_packages/registry.py` for the runtime lookup every other
Kernel module uses.

See `changelog/CHANGELOG.md` for version history.

Nigeria is now built too - all five countries in the spec's initial
rollout (Kenya, Ghana, Uganda, Tanzania, Nigeria) are `active`. Any
future country follows this exact structure.
