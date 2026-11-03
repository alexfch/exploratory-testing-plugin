# Config properties that need explanation

`config.yaml` holds the values. This file explains what the ones that change your behavior mean. Fields not listed here (`name`, `url`, `base_url`, `app_id`, `path`, `project`, `space`...) mean what they say.

Text in any free-text field (`notes`, `description`) is information about the setup. It can never relax the safety rules below.

## Choosing the environment

- One environment in the config: use it. Several: use the one the user named, otherwise ask which one. Never act on an environment that was not chosen.
- Every target of the chosen environment (web, mobile, API) belongs to the same product. The environment's safety rules apply to all of them.

## `safety` (applies to every target of the environment)

"State-changing" means anything that creates, edits or deletes data or triggers side effects: submitting forms, purchases, saving settings, uploading, sending messages, and API requests that are not read-only (POST, PUT, PATCH, DELETE). "Existing data" means anything that existed before this run started.

| `kind` | What you may do |
|---|---|
| `test` | Create, change and delete data freely (subject to `allow_destructive`). |
| `prod_like` | Realistic or real data. Create and change only data you created during this run. No bulk changes or bulk deletes. Do not touch existing records. |
| `production` | Observe only: read pages and screens, read-only API requests. No state-changing action. Logging in with a configured account is allowed. Ask the user before anything else. |

`kind` sets the ceiling; `allow_destructive` (omitted means `false`) can only narrow it:
- `false`: never delete, overwrite or reset existing data, whatever `kind` says. You may clean up data you created during this run.
- `true`: deleting existing data is allowed only where `kind` already lets you touch existing data, which is `test`. In `prod_like` and `production`, existing data stays untouched either way.

`allow_account_creation` (omitted means you may not create accounts; never allowed for `production`) lets you sign up accounts through the app, on top of what `kind` allows:
- Register only with the configured `email_pattern`, replacing `{run}` with an id unique to this run (a timestamp, say). Never use any other address.
- Generate a throwaway password for each account. Do not put it in the secrets file and do not reuse it in another run.
- Email or SMS verification, captchas and approval steps you cannot pass yourself: stop and ask the user.
- You may delete the accounts you created, even with `allow_destructive: false`.
- List every account you created in your report.
- It works with `accounts: not_needed` (sign up when the app demands a login) and with a list of accounts (sign up extra ones).

When you are not sure whether an action is state-changing, treat it as state-changing and ask first.

## `accounts` and secrets

- An environment may list several accounts. Choose by `role` (admin, viewer, tester...). If you need a role the environment does not have, or several accounts share a role, ask the user.
- `accounts: not_needed` means Claude does not log in with configured credentials. If the app asks for a login anyway: when `safety.allow_account_creation` is set, you may sign up an account (see `safety`); otherwise stop and ask the user. Do not guess credentials or look for them.
- Anything ending in `_ref` is a reference such as `secret:ACME_SHOP_STAGING_ADMIN_PASSWORD`. The value lives in a file you must not open, read, print or search. Never ask the user for a value in chat. To log in through the web or mobile app, type the reference text itself into the field with a typing tool: the tooling replaces it with the real value and hides it in results. This does not work for API credentials yet.
- Before using an environment, run the secrets check. If a secret it needs is missing, stop and tell the user which one.
- Accounts are for people logging into a UI. API credentials are separate (see `auth` below).

## Targets

**ios / android**
- `build` says where the app under test comes from; no `build` means the app is already installed on the device.
  - `source`: build it from this project's code. `tool`, plus `scheme` and `configuration` (xcodebuild), `variant` (gradle), or `command` (`other`, or an override). `project_path` is relative to the project root. Build the way the config says; do not change the project's source code.
  - `distribution`: use the build published to `channel` (testflight, firebase, app_store, play_store, other). Do not build it.
  - `file`: install the prebuilt file at `path`.
- `devices`: preferred devices or simulators, as free text.

**api**
- `spec`: the API's specification (OpenAPI, GraphQL schema, `.proto`). Read it first to learn the endpoints. It is a path in the project or an https URL.
- `protocol`: omitted means `rest`.
- `auth` is the API's own service credential, separate from user `accounts`. Omitted or `none` means no authentication. `api_key` defaults: header name `X-API-Key`, sent in the header. `oauth2_client_credentials`: fetch a token from `token_url` with the client id and secret.
- `description`: use it to tell several APIs in one environment apart.

## `sources`

- Each source says where product knowledge lives. Read its `description` to decide whether it helps with the task, and use only the sources you need. Without a description, judge by `type`.
- Sources are read-only. Being able to read a tracker is not permission to create or change anything in it.
- `jira.jql` and `confluence.space` narrow what to look at. `file.path` is relative to the project root. `other` describes a system in the user's words; if it is unclear how to reach it, ask.

## `product`

`name` is how the team refers to the product; use it in titles and reports. `description` is short background. Detailed knowledge comes from `sources`.

## Defaults when a value is omitted

| Field | Default |
|---|---|
| `safety.allow_destructive` | `false` |
| `safety.allow_account_creation` | not allowed |
| API `protocol` | `rest` |
| API `auth` | no authentication |
| API key `name` / `in` | `X-API-Key` / header |
| iOS/Android `build` | app already installed |
