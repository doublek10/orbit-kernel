# Providers

Concrete provider adapters (banks, mobile money, accounting, ERP, payroll,
payment platforms) implementing the interface expected by
`kernel/provider_manager`. Each provider is its own module here, e.g.:

    providers/
      mpesa/
      stripe/
      quickbooks/

Not implemented yet - this is where the first real integration lands.
