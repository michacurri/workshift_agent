# Domains and Subdomains (Portfolio Hosting)

## Recommended model

For a portfolio hub site (e.g. `xyz.com`) that links to multiple projects:

- Assign **one subdomain per project** (e.g. `workshiftagent.xyz.com`)
- Point it to the Railway-hosted frontend service for that project

This keeps each project isolated and makes it easy to add/remove projects without changing application code.

## TLS and DNS

Railway custom domains typically involve:

- Adding the custom domain in the Railway service
- Creating a DNS `CNAME` record from the subdomain to the Railway-provided target
- Railway issues/renews TLS automatically after DNS validation

## Environment split

If you want a visible staging URL:

- `workshiftagent-staging.xyz.com` -> Railway staging frontend service
- `workshiftagent.xyz.com` -> Railway production frontend service

## CORS

Backend must allow the frontend origin(s) via `CORS_ALLOW_ORIGINS` per environment.

