# Kenya Country Package

The first Country Package built out against the Country Packages
Engineering Specification. `active = True` in `manifest.py` - this is
the only country the Frontend offers at signup today.

Contributes: providers (M-Pesa, Airtel Money, KCB, Equity, Flutterwave,
Binance Pay), banking rules, tax configuration (VAT/PAYE/corporate/DST/
withholding/payroll), compliance (KYC/AML), KES currency, Kenya-specific
validation (phone/KRA PIN/national ID), provider payload mappings,
country events, the default Company Blueprint applied at registration,
localization, regulatory monitoring sources, and the update-proposal
shape.

Loaded dynamically by the Plugin Manager (`country_packages/loader.py`)
based on a company's `country` field from the Company Resolver - see
`country_packages/registry.py` for the runtime lookup every other
Kernel module uses.

See `changelog/CHANGELOG.md` for version history.

Nigeria is now built too - all five countries in the spec's initial
rollout (Kenya, Ghana, Uganda, Tanzania, Nigeria) are `active`. Any
future country follows this exact structure.
