# Rules of engagement

rules_version: 1

These are the rules the testing agents follow in each kind of environment. The kind comes from `safety.kind` in `config.yaml`, and the Setup skill checks that this file has a section for every kind your config uses.

This file belongs to you. Make it stricter or looser, or rewrite it. Keep this structure so the checks pass:
- the three kind sections `## test`, `## prod_like` and `## production` (the kinds are fixed; the config schema accepts no others),
- under each kind, the lists `### Allowed`, `### Sandboxed` and `### Forbidden` (write `- (none)` for an empty list),
- the `## Modifiers` section, which explains `allow_destructive` and `allow_account_creation`,
- a rule ID (`R-01`, `R-02`...) at the start of every rule, unique in the file.

Rules for a single run do not belong here. Tell the Orchestrator when you start the run; they are recorded in that run's `engagement.md`.

Agents read this file and never edit it. Updating the plugin does not update this file.

## Terms

- **Allowed**: the agent may do it freely.
- **Sandboxed**: the agent may do it, but only inside the stated restriction.
- **Forbidden**: the agent must never do it.
- **State-changing** means anything that creates, edits or deletes data or triggers side effects: submitting forms, purchases, saving settings, uploading, sending messages, and API requests that are not read-only (POST, PUT, PATCH, DELETE).
- **Existing data** means anything that existed before this run started.

## test

### Allowed
- R-01 Create, change and delete data: submit forms, make purchases with test payment methods, upload files, save settings, send messages to test recipients.
- R-02 Send any API request, including POST, PUT, PATCH and DELETE.
- R-03 Test performance, load, security and third-party integrations when the change under test brings a risk there.

### Sandboxed
- (none)

### Forbidden
- (none)

## prod_like

### Allowed
- R-04 Read pages, screens and data, and send read-only API requests.
- R-05 Log in with the configured accounts.
- R-06 Test performance, load, security and third-party integrations when the change under test brings a risk there.

### Sandboxed
- R-07 Create and change data only if it was created during this run, and clean it up afterwards.

### Forbidden
- R-08 Change, overwrite or delete existing data.
- R-09 Bulk changes and bulk deletes.

## production

### Allowed
- R-10 Read pages and screens, and send read-only API requests.
- R-11 Log in with a configured account.

### Sandboxed
- R-12 Anything not listed in this section: ask the user first. If you cannot ask, skip it and log it as a problem.

### Forbidden
- R-13 Any state-changing action.
- R-14 Creating accounts.
- R-15 Load, stress and performance testing.
- R-16 Security probing: fuzzing, injection attempts, vulnerability scanners, brute-force attempts.
- R-17 Actions that trigger side effects in third-party systems: payments, email, SMS, notifications to partners.
- R-18 Using real people's personal data: do not use it as test input, and do not copy it into notes, bug reports or screenshots.

## Modifiers

These apply on top of the kind, according to the environment's settings in `config.yaml`.

- R-19 `allow_destructive` false or omitted: never delete, overwrite or reset existing data, whatever the kind says. You may clean up data you created during this run.
- R-20 `allow_destructive: true`: deleting existing data is allowed only where the kind lets you touch existing data (`test`). In `prod_like` and `production`, existing data stays untouched either way.
- R-21 `allow_account_creation` omitted: do not create accounts.
- R-22 `allow_account_creation` set (never for `production`): sign up accounts through the app only with the configured `email_pattern`, replacing `{run}` with an id unique to this run. Generate a throwaway password for each account and never put it in the secrets file. Stop and ask the user for verification, captcha or approval steps you cannot pass yourself. List every account you created in the report. You may delete accounts you created, even with `allow_destructive: false`.

## General

- R-23 When you are not sure whether an action changes state, treat it as state-changing and follow the rules for state-changing actions.
