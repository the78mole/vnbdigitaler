# Semantic Versioning Guide for VNBdigitaler

This repository uses automatic semantic versioning based on commit messages using [paulhatch/semantic-version](https://github.com/PaulHatch/semantic-version).

## Commit Message Patterns

The automatic versioning system analyzes commit messages and determines version bumps based on the following patterns:

### 🚀 Major Version Bump (Breaking Changes)

Triggers a major version increment (e.g., v1.2.3 → v2.0.0)

**Patterns:**

- `BREAKING CHANGE:` in commit message or body
- `!:` at the end of the commit type
- `!)` at the end of the commit type

**Examples:**

```
feat!: redesign database schema (BREAKING CHANGE)
refactor!: remove deprecated API endpoints
fix!: change configuration format (BREAKING CHANGE)
```

### 🎯 Minor Version Bump (New Features)

Triggers a minor version increment (e.g., v1.2.3 → v1.3.0)

**Patterns:**

- `feat:` - New features
- `refactor:` - Code refactoring
- `fix:` - Bug fixes

**Examples:**

```
feat: add automatic company matching system
refactor: improve rollout quota processing
fix: resolve database connection timeout issues
```

### 🐛 Patch Version Bump (Default)

Triggers a patch version increment (e.g., v1.2.3 → v1.2.4)

**Patterns:**

- Any other commit message format
- Documentation updates
- Minor improvements
- Configuration changes

**Examples:**

```
docs: update README with new API endpoints
chore: update dependencies
style: fix code formatting
test: add unit tests for company matcher
```

## Configuration Details

The semantic versioning is configured with:

- **Tag Prefix**: `v` (creates tags like `v1.2.3`)
- **Version Format**: `${major}.${minor}.${patch}`
- **Bump Each Commit**: `true` (each commit can trigger a version bump)
- **Search Commit Body**: `true` (searches entire commit message)

## Release Creation

Releases are automatically created when:

1. The central data update workflow runs successfully
2. Meaningful changes are detected (new companies, updated quotas, etc.)
3. The workflow is not in dry-run or check-only mode

### Release Contents

Each release includes:

- **Excel Files**: Original BNetzA rollout reports (`.xlsx`)
- **CSV Files**: Converted data for programmatic access (`.csv`)
- **JSON Files**: Summary metadata and statistics
- **Release Notes**: Detailed summary of changes and data quality information

## Examples of Effective Commit Messages

### For Data Updates (Minor Bump)

```
feat: update Q1 2025 rollout quotas
feat: add support for new BNetzA report format
fix: resolve company matching accuracy issues
refactor: improve rollout data processing pipeline
```

### For Infrastructure Changes (Patch Bump)

```
chore: update GitHub Actions workflow dependencies
docs: improve setup documentation
test: add integration tests for company updater
style: apply consistent code formatting
```

### For Breaking Changes (Major Bump)

```
feat!: migrate to new database schema (BREAKING CHANGE)
refactor!: change API response format (BREAKING CHANGE)
fix!: update configuration structure (BREAKING CHANGE)
```

## Best Practices

1. **Be Descriptive**: Use clear, descriptive commit messages
2. **Use Conventional Commits**: Follow the `type: description` format
3. **Single Purpose**: One logical change per commit
4. **Breaking Changes**: Always include `BREAKING CHANGE` in the body for major changes
5. **Scope**: Consider adding scope for clarity: `feat(company-matcher): add fuzzy matching`

## Monitoring Releases

- **Automatic Creation**: Releases are created automatically during scheduled data updates
- **GitHub Releases**: Check the [Releases page](../../releases) for the latest data
- **Workflow Summaries**: Review GitHub Actions summaries for detailed update information

## Manual Release Creation

While releases are primarily automated, you can manually trigger the central data update workflow:

1. Go to [Actions](../../actions)
2. Select "Central Data Update Workflows"
3. Click "Run workflow"
4. Choose appropriate options (update type, force update, etc.)

---

*This versioning strategy ensures that data releases are properly versioned and tracked while maintaining compatibility and clear change communication.*
