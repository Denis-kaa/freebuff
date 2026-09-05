# CHECKLIST.md — PM OS

## Before server changes

- [ ] Read project MANIFEST/ROADMAP/STEPS.
- [ ] Check backup and current service status.
- [ ] Confirm workspace/runtime boundary.
- [ ] Record non-obvious architecture choices in ADR.

## After changes

- [ ] Python syntax/import check on whimco.
- [ ] Backend regression.
- [ ] Stage acceptance.
- [ ] Frontend tests/build.
- [ ] Playwright smoke: console/page/network errors.
- [ ] Update lessons and evidence.
- [ ] Update roadmap and audit matrix.

## Security

- [ ] Permission check on backend.
- [ ] Workspace isolation.
- [ ] IDOR test.
- [ ] Sensitive-field masking.
- [ ] No secrets in source or report.
