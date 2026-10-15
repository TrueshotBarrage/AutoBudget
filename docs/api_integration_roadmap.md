# API integration roadmap

Updated: 2026-10-15

Plaid is now implemented in **autobudget_v3**, the Expo/Supabase app. It is not being added to this old Python Gmail tool.

The [current working roadmap](https://github.com/TrueshotBarrage/autobudget_v3/blob/master/docs/api_integration_roadmap.md) replaces the original proposal here:

1. Support multiple bank connections and link bank-reported credit-card balances to the balance sheet.
2. Add hourly, server-side sync while keeping manual Sync available.
3. Improve automatic categories with merchant memory, keyword rules, and explicit card defaults.

Venture X is already connected, manual sync works, and edits survive repeat syncs. Gmail remains separate; no changes to this repo's pipeline are planned.
