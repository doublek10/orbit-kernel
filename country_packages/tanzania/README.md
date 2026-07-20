# Tanzania Country Package

Fourth Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's, Ghana's and
Uganda's. `active = True` in `manifest.py` - Tanzania is now offered
as a signup option alongside Kenya, Ghana and Uganda.

Contributes: providers (M-Pesa/Vodacom, Tigo Pesa, HaloPesa, Airtel
Money, CRDB Bank, NMB Bank, Flutterwave, Binance Pay), banking rules,
tax configuration (VAT, PAYE, corporate tax, mobile money levy,
withholding, payroll/NSSF/SDL), compliance (KYC/AML), TZS currency,
Tanzania-specific validation (phone/TIN/NIDA National ID), provider
payload mappings, country events, the default Company Blueprint
applied at registration, localization, regulatory monitoring sources,
and the update-proposal shape.

Loaded dynamically by the Plugin Manager
(`country_packages/loader.py`) based on a company's `country` field -
see `country_packages/registry.py` for the runtime lookup every other
Kernel module uses.

See `changelog/CHANGELOG.md` for version history.

Nigeria is now built too - all five countries in the spec's initial
rollout (Kenya, Ghana, Uganda, Tanzania, Nigeria) are `active`. Any
future country follows this exact structure.
