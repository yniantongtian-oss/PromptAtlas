# Security policy

## Supported code

Security fixes target the latest commit on the default branch. Versioned releases,
when published, identify their supported source commit in the release notes.

## Reporting a vulnerability

Use the repository's private vulnerability reporting option on the GitHub
Security tab when available. Otherwise open an issue describing the affected
version and impact without posting credentials, private prompts, or exploit data.
Do not send reports to a placeholder email address.

## Trust boundaries

PromptAtlas reads prompt text as data. It does not run prompt-defined tools,
execute embedded code, fetch source URLs, load models, or access API credentials.
Custom atlas files are user-selected local inputs. File writes require explicit
output paths; the bundled atlas is read-only.

The CLI and parser do not sandbox hostile or extremely large files. Process only
files appropriate to the available resources. Custom JSONL stores support a
single writer; they are not a transactional multi-user database.

Exported promptfoo files contain the actual prompt being evaluated. Inspect them
before running an external provider, since that step can transmit content and
incur charges. A synthetic canary check is not a comprehensive security audit or
a guarantee that an agent will resist injection.
