---
name: setup
description: Create or update the exploratory testing plugin's configuration for the current project by interviewing the user (product, environments, test accounts, web/mobile/API targets, where product knowledge lives). Use when no config exists, validation fails, or the user wants to add or change an environment, account, build, or source.
---

# Exploratory testing: setup

Interview the user, write the project's config file, and do not finish until the config validates and every secret it references is set.

**Path check, before anything else.** Claude Code fills in this skill's paths with real absolute paths when it loads the skill. If you can still read the words CLAUDE_PROJECT_DIR, CLAUDE_PLUGIN_ROOT or CLAUDE_SKILL_DIR inside a path or command anywhere in this skill (other than in this paragraph), the filling-in did not happen. Stop. Do not run any command and do not guess a path. Tell the user: "The plugin's paths were not resolved, so I can't continue safely. Please reload the plugin or start a new session."

- Config file: `${CLAUDE_PROJECT_DIR}/exploratory-testing/config.yaml`
- Validator: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/validate_config.py" <config>`
- Secrets: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_secret.py" {check|template} <config>`
- Rules check: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_roe.py" --config <config>`

## Hard rules

1. **Never ask for a password, token or key in chat, and never write one into any file you create.** The config holds only references (`secret:NAME`). If the user pastes a real secret anyway, tell them not to, do not use or store it, and advise rotating it.
2. **Never open, read, print or search the secrets file** (`~/exploratory-testing/secrets.env`). Only the two scripts touch it.
3. **Setup is not complete** until `validate_config.py` and `check_roe.py` print `OK` and `check_secret.py check` exits 0. Do not tell the user it is done before that.
4. **Do not invent config fields, and never edit the validator or the schema** to make a config pass. Fix the config.
5. **Every environment needs an explicit safety level and an explicit answer about logins, both chosen by the user.** Never default either silently, never write `accounts: not_needed` unless the user said Claude should not log in there, and never write `allow_account_creation` or invent its email address unless the user asked for it and gave you the address.
6. If you cannot ask the user questions (scheduled or headless run), stop and say setup is needed. Do not guess.
7. If the session is not inside a project folder, ask which folder is the project root and use `<that folder>/exploratory-testing/config.yaml`.
8. `exploratory-testing/rules-of-engagement.md` is the user's file. Never edit it. If `check_roe.py` reports an error in it, show the error and let the user decide how to fix it.

## Step 0: Create or update?

If the config file exists, run the validator on it.
- Invalid: tell the user what is wrong in one line and offer to fix it, then continue from Step 5.
- Valid: ask what they want to change (add an environment, change an environment, accounts, sources, start over). Change only that part and skip to Step 5. For "start over", copy the file to `config.yaml.bak` first.

If it does not exist, continue with Step 1.

## Step 1: Discover before asking

Look quietly, then propose what you found instead of asking from scratch:
- Connected tools: a Jira or Confluence connector, other trackers.
- The repo: product name (README, package.json, app name), `docs/` or specs, `openapi.yaml/json` or a GraphQL schema, `*.xcworkspace` / `*.xcodeproj`, `build.gradle`, `pubspec.yaml`, React Native or Expo config, scripts that start the web app.
- On macOS with Xcode installed, `xcodebuild -list -json` on a found project lists schemes you can offer.

## Step 2: Shape questions

Ask these together in one AskUserQuestion call (or one plain-text message). Skip any that discovery already answered clearly; confirm those instead.

1. **What will be tested?** (multi-select) Web app / iOS app / Android app / Backend API
2. **How many test environments?** One / Two or three / Four or more
3. **Do tests need to log in?** No login / One account per environment / Several accounts (roles) per environment
4. **Where does product knowledge live?** (multi-select) Jira / Confluence or wiki / Files in the repo / Web pages / Something else

## Step 3: Details, only for what applies

Ask in small batches, one environment at a time. Offer "same as the previous environment, except..." to avoid repetition. Propose values from discovery.

**Product:** name and one or two sentences on what it is and who uses it (optional, but ask).

**Each environment:**
- `name`: lowercase letters, digits, `_` or `-` (staging, uat).
- `safety.kind`, always asked, with these meanings:
  - `test`: data may be freely created, changed and deleted.
  - `prod_like`: realistic or real data. Create or change only data made during a run; no bulk deletes; do not touch existing records.
  - `production`: observe only; no state-changing actions.
  - The exact rules each kind brings are in `exploratory-testing/rules-of-engagement.md` (created in Step 5). The user can edit that file.
  - Also ask whether destructive actions are allowed (`allow_destructive`). For `production` it is always false.
  - For `test` and `prod_like` only, ask whether Claude may create accounts itself by signing up through the app. If yes, ask for the email address to register with and turn it into a pattern with one `{run}` before the `@`, such as `qa+{run}@acme-test.com`. It must be an address the team controls or a test domain; never propose an address on a domain the user does not control. Write `allow_account_creation: {email_pattern: ...}` under `safety`, and omit the field when the answer is no.
- Targets (one entry per thing tested), asking only for the types chosen in Step 2:
  - **web:** `url` (http or https).
  - **ios / android:** `app_id` (bundle ID or package name). Build: from this project's source, from a distribution channel (testflight, firebase, app_store, play_store, other), a prebuilt file, or none. For a source build with Xcode: `project_path` and `scheme` (and optionally `configuration`). For Gradle: `variant`. Other tools: flutter, react_native, expo, or `other` with a `command`. Optional `devices`.
  - **api:** `base_url`, optional `protocol` (rest default, graphql, grpc, soap), optional `spec` (file path or https URL), optional `description`. Auth: none, bearer, api_key, basic, or oauth2_client_credentials. These are service credentials, separate from user logins.
- Accounts, always asked. If Claude should not log in there, write `accounts: not_needed` (the user's answer, never your guess). Otherwise list each account with its `username` and a `role` (admin, viewer, tester...); roles let later steps choose the right account.

**Sources**, one per place chosen in Step 2 (question 4), each with a short free-text `description` saying what it holds and how to use it (for example "Epics are features; NFRs are tagged nfr"). Draft the description from what you found and let the user edit it.
- Jira: `project` key (capitals), optional `site`, optional `jql`. Confluence: `space`, optional `site`. File: `path` relative to the project root. Web page: `url`. Anything else: `type: other` with a `description`.

## Step 4: Secret names

Every password, token, key or client secret becomes a reference `secret:NAME`. Never ask the user to choose or type names.
- Build NAME from the product, environment and purpose, in capitals with underscores: `ACME_SHOP_STAGING_ADMIN_PASSWORD`, `ACME_SHOP_STAGING_API_TOKEN`. It must start with a letter or `_`.
- The product prefix matters: the secrets file is shared by every project on this computer.
- If the user says an account is the same in two environments, reuse one NAME.
- Say once, plainly: use dedicated, low-privilege test accounts. A password typed into a login form during testing passes through the session. For `production`, prefer no login or a read-only account.

## Step 5: Create workspace folder

- Run:
    mkdir -p "${CLAUDE_PROJECT_DIR}/exploratory-testing"
    cp -Rn "${CLAUDE_SKILL_DIR}/references/workspace-template/." "${CLAUDE_PROJECT_DIR}/exploratory-testing/"
  (If the user named another project root under hard rule 7, use that folder in place of the project folder path at the start of both commands.)
  (-n never overwrites existing files, so re-running on an existing project is safe.)


## Step 6: Write the config

Write `config.yaml` with `schema_version: 1`. Save it as `config.yaml` in the `exploratory-testing` folder you created in Step 5, under the project root. Use only the shapes below.

```yaml
schema_version: 1
product:
  name: Acme Shop
  description: Online store for small businesses.
environments:
  - name: staging
    safety:
      kind: test
      allow_account_creation: {email_pattern: "qa+{run}@acme-test.com"}
    accounts:
      - username: qa-admin@acme.com
        role: admin
        password_ref: secret:ACME_SHOP_STAGING_ADMIN_PASSWORD
    targets:
      - type: web
        url: https://staging.acme.com
      - type: ios
        app_id: com.acme.shop.staging
        build:
          type: source
          tool: xcodebuild
          project_path: ios/Shop.xcworkspace
          scheme: Shop-Staging
      - type: api
        base_url: https://api.staging.acme.com
        spec: docs/openapi.yaml
        auth:
          type: bearer
          token_ref: secret:ACME_SHOP_STAGING_API_TOKEN
  - name: uat
    safety: {kind: prod_like, allow_destructive: false}
    accounts: not_needed
    targets:
      - type: web
        url: https://uat.acme.com
sources:
  - type: jira
    project: SHOP
    description: Epics are features; NFRs are tagged "nfr". Bugs go here too.
  - type: file
    path: docs/feature-a.md
    description: Feature A description, the spec for the release under test.
```

Every environment needs `accounts`: a list of accounts, or `not_needed`. Other options you may need: build `type: distribution` with `channel`, build `type: file` with `path`, api auth `api_key` (`key_ref`, optional `name`, `in`), `basic` (`username`, `password_ref`), `oauth2_client_credentials` (`token_url`, `client_id`, `client_secret_ref`, optional `scope`).

The file contains usernames. Ask whether it should be committed for the team or kept private; if private, add `exploratory-testing/` to `.gitignore`.

## Step 7: Validate and fix

Run the validator. It prints one line per problem, never a secret value. Fix every `ERROR` in the config and run it again until it prints `OK`. If an error needs an answer from the user, ask. A missing `safety` or `accounts` always does: never fill either in yourself. Show `WARN` lines (for example a path that does not exist yet) and let the user decide whether they matter.

Then run `check_roe.py`. It checks that `exploratory-testing/rules-of-engagement.md` has a section for every `safety.kind` the config uses. Show any `ERROR` and `WARN` lines; the file is the user's to fix.

If any of these scripts cannot start (for example "command not found", or a missing-package message), tell the user that Python 3 (available as `python3`) and the `pyyaml` and `jsonschema` packages are required, and stop. Do not tell them setup is done.

## Step 8: Secrets

1. Run `check_secret.py template <config>`. It adds an empty `NAME=` line for each secret the config references.
2. Tell the user, in their own words: open `~/exploratory-testing/secrets.env` in an editor, type each value right after its `=` sign with no quotes, and save. List each NAME with the account or API it belongs to (run `check_secret.py check <config>` to get the list). Remind them not to paste values into the chat.
3. Wait until the user says they are done, then run `check_secret.py check <config>`.
4. Repeat from step 2 until it exits 0. Warnings (quotes around a value, stray spaces, duplicates, a malformed line, file readable by others) name the secret or line, never the value; relay them and have the user fix the file.
5. Suggest that they add a rule in their Claude Code permission settings denying reads of the `~/exploratory-testing` folder, so Claude cannot open the secrets file.

## Step 9: Finish

Only when all three scripts pass, confirm briefly: the product, each environment with its safety level and targets, and the sources. Tell the user that `exploratory-testing/rules-of-engagement.md` holds the rules for each kind of environment and that they can edit it. Say that `/exploratory-testing:setup` changes any of it later.
