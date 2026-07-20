# Ghana Country Package

Second Country Package built out against the Country Packages
Engineering Specification, same structure as Kenya's. `active = True`
in `manifest.py` - Ghana is now offered as a signup option alongside
Kenya.

Contributes: providers (MTN MoMo, Vodafone Cash, AirtelTigo Money, GCB
Bank, Ecobank Ghana, Paystack, Flutterwave, Binance Pay), banking
rules, tax configuration (VAT + NHIL/GETFund/COVID levies, PAYE,
corporate tax, electronic transfer levy, withholding, payroll),
compliance (KYC/AML), GHS currency, Ghana-specific validation
(phone/TIN/Ghana Card/GhanaPost GPS), provider payload mappings,
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
