# API Integration Roadmap

> Last updated: 2026-10-13 · Status: Proposed, not implemented

## Add Plaid, keep Gmail

- Use Plaid to get transactions straight from supported banks, without parsing emails.
- Keep Gmail for banks and purchases Plaid doesn't cover.
- Start small: connect one bank, save its transactions, and export them to CSV.

## Check the free Trial first

- Trial is for eligible US/Canada developers and US/Canadian institutions. It won't connect Korean banks.
- Transactions is included. The limit is 10 bank login connections, called Items; each can include multiple accounts.
- Deleted and duplicate connections still use up that limit. Test with fake accounts in Sandbox first.
- Upgrading to a paid plan starts billing for existing Transactions connections. You can't switch back to Trial.

Sources: [Trial details](https://support.plaid.com/hc/en-us/articles/39994173227159-What-is-the-Plaid-Trial-plan), [billing rules](https://plaid.com/docs/account/billing/#trial-plans).

## Build a small first version

1. Add a simple “Connect bank” page using Plaid Link. Keep bank access tokens private on the server.
2. Add separate tables for bank connections, accounts, and transactions. Reuse the existing PostgreSQL setup.
3. Add a sync command using `/transactions/sync`. Save its progress marker together with each completed batch.
4. Handle changed and removed transactions too. A pending purchase can become a new posted transaction with a different ID.
5. Export posted transactions with their account, currency, and source. Use Plaid for linked accounts to avoid counting Gmail copies twice.

The current email tables only support adding records. Plaid needs to update them too. See [Plaid's sync guide](https://plaid.com/docs/transactions/add-to-app/).

## Try it, then automate

- Test updates, removals, and repeat runs in Sandbox.
- Connect one real bank after confirming eligibility and coverage.
- Start with manual sync, then add daily cron.
- Before hosting the connection page, protect its routes and disable Flask debug mode.
- Leave webhooks, direct bank APIs, and a larger app redesign for later.
