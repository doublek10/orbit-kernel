# Nigeria Country Package

Fifth and final Country Package of the initial rollout, built out
against the Country Packages Engineering Specification, same
structure as Kenya's, Ghana's, Uganda's and Tanzania's. `active = True`
in `manifest.py` - Nigeria is now offered as a signup option alongside
all four other countries.

Contributes: providers (OPay, PalmPay, Paga, GTBank, Access Bank,
Zenith Bank, Paystack, Flutterwave, Binance Pay), banking rules, tax
configuration (VAT, PAYE, turnover-tiered Companies Income Tax,
Electronic Money Transfer Levy, withholding, payroll/pension/NHF/
NSITF), compliance (KYC via NIN/BVN, AML, CAC registration), NGN
currency, Nigeria-specific validation (phone/TIN/NIN/BVN/CAC number),
provider payload mappings, country events, the default Company
Blueprint applied at registration, localization, regulatory monitoring
sources, and the update-proposal shape.

Loaded dynamically by the Plugin Manager
(`country_packages/loader.py`) based on a company's `country` field -
see `country_packages/registry.py` for the runtime lookup every other
Kernel module uses.

See `changelog/CHANGELOG.md` for version history.

This closes out the initial rollout: Kenya, Ghana, Uganda, Tanzania and
Nigeria are all fully built and `active`. Any future country follows
the same pattern - a new folder under `country_packages/` with this
exact structure, never a change to the Kernel itself.
