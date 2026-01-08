# Security Best Practices

Overview: Configure WinSW with least privilege and secure operations.

## Principle of least privilege

- Prefer LocalService or NetworkService when possible.
- If using a user account, restrict rights; set `<allowservicelogon>true</allowservicelogon>` only when necessary.

## Credential handling

- Use `<prompt>` for interactive credential entry when appropriate.
- Avoid plaintext secrets; prefer secure environments and HTTPS downloads.

## Service ACLs

- Define `securityDescriptor` (SDDL) to control who can manage the service.

## Network and downloads

- Use HTTPS; trust the CA; configure proxies carefully.
- Use `failOnError="true"` for critical downloads.

## Filesystem & paths

- Use `%BASE%` for co-located assets.
- Validate working directory and path permissions.

## References

- License (MIT): https://github.com/winsw/winsw/blob/v3/LICENSE.txt
- XML spec security/account sections: https://github.com/winsw/winsw/blob/v3/docs/xml-config-file.md
