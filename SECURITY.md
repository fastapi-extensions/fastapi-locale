# Security policy

## Supported versions

Security fixes go into the latest release.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting on this repository
("Security" tab, then "Report a vulnerability"). You will get an answer within seven days.

## Design notes

- Locale values from requests are validated as language tags and only compared with the configured
  locales. They are never used to build file paths.
- `Accept-Language` input is cut to a fixed length before parsing.
- Translated strings can only substitute named values. They cannot read attributes or items, so a
  malicious catalog cannot reach application data through placeholders.
