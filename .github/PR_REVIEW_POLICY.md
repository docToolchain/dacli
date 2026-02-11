# Pull Request Review Policy

This document defines the review requirements for pull requests to the dacli project, implementing a risk-based sampling approach as recommended by Tier 2 security practices.

## Review Requirements by Change Type

### 🔴 Mandatory Review (100%)

**All PRs in these categories require human review before merge:**

1. **Security-sensitive changes**
   - Authentication, authorization, cryptography
   - Input validation, sanitization
   - File system operations with user-controlled paths
   - Dependency updates with security advisories

2. **Breaking changes**
   - Public API modifications
   - Changes to CLI interface or MCP tools
   - Configuration format changes

3. **Architecture changes**
   - New components or major refactoring
   - Changes to core parsers (AsciiDoc, Markdown)
   - Database schema or data model changes

4. **Release preparation**
   - Version bumps to MINOR or MAJOR
   - Release branch merges

### 🟡 Sampling Review (~20-30%)

**Sample these PRs for review (aim for 20-30% coverage):**

1. **Bug fixes**
   - Review at least 1 in 3-5 bug fix PRs
   - Prioritize fixes for critical bugs or frequently used features

2. **Internal refactoring**
   - Review 1 in 4-5 refactoring PRs
   - Focus on complex refactorings or large file changes

3. **Test additions**
   - Review 1 in 5 test-only PRs
   - Prioritize reviews of property-based tests or integration tests

4. **Documentation updates**
   - Review 1 in 5 documentation PRs
   - Focus on user-facing documentation (manual, tutorial)

### 🟢 Auto-merge Eligible

**These PRs can be auto-merged after automated checks pass:**

1. **Dependency updates (non-security)**
   - PATCH version bumps for dependencies
   - Must pass all CI checks including `pip-audit`
   - No breaking changes in changelog

2. **Formatting/linting fixes**
   - Changes from Ruff auto-fix or pre-commit hooks
   - No logic changes

3. **PATCH version bumps**
   - Small bug fixes with passing tests
   - No API changes

## Sampling Strategy

### Selection Criteria

When sampling PRs for review, prioritize:

1. **Complexity**: Larger diffs, multiple files changed
2. **Risk area**: Changes to parsers, file handlers, or services
3. **Author experience**: New contributors get more reviews
4. **Test coverage**: PRs with low test coverage get more scrutiny

### Monthly Target

- **Minimum**: 20% of all non-mandatory PRs reviewed
- **Target**: 25-30% for better coverage
- Track monthly in project metrics

## Review Checklist

When reviewing a PR, verify:

- [ ] **Code quality**
  - Follows project conventions (see CLAUDE.md)
  - No code smells or obvious bugs
  - Appropriate error handling

- [ ] **Tests**
  - New features have tests
  - Bug fixes have regression tests
  - Tests are meaningful (not just coverage)

- [ ] **Documentation**
  - Public API changes documented
  - README/manual updated if needed
  - Code comments for complex logic

- [ ] **Security**
  - No hardcoded secrets or credentials
  - Input validation for user-controlled data
  - Safe file operations (no path traversal)

- [ ] **Performance**
  - No obvious performance regressions
  - Efficient algorithms for large documents

## Automated Checks (Always Required)

All PRs must pass these automated checks before merge:

1. ✅ **Ruff linting** (no errors)
2. ✅ **All tests pass** (702+ tests)
3. ✅ **Code coverage** maintained or improved
4. ✅ **Pre-commit hooks** pass
5. ✅ **Dependency scan** (pip-audit)
6. ✅ **CodeQL SAST** (no high/critical findings)

## AI-Assisted Development

For PRs marked as AI-assisted (commits from `R{AI}f D. Müller`):

- **Apply normal review rules** - AI assistance doesn't bypass review requirements
- **Extra scrutiny for**: Security-sensitive code, complex logic, edge cases
- **AI Code Review workflow** runs automatically on all PRs

## Responsibilities

- **PR Author**: Ensure all automated checks pass, provide clear description
- **Reviewers**: Follow this policy, provide constructive feedback
- **Maintainers**: Track sampling rate, adjust policy as needed

## Metrics Tracking

Track these metrics monthly:

- Total PRs merged
- PRs by category (mandatory/sampling/auto-merge)
- Actual sampling rate achieved
- Review time (median, p95)

Review and adjust policy quarterly based on metrics and team feedback.

---

**Policy Version**: 1.0
**Last Updated**: 2026-02-11
**Next Review**: 2026-05-11
