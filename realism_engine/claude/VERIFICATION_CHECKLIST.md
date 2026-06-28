# Verification Checklist

After Claude implements the realism engine, check these.

## CLI

- [ ] Existing `python main.py script` still works or has a safe replacement.
- [ ] New realistic mode exists.
- [ ] Realistic mode asks for product, audience, platform, tone, goal.
- [ ] Realistic mode can accept observed issues.
- [ ] Generated script is saved to the vault.

## Prompt pipeline

- [ ] Master rules are loaded.
- [ ] Proof inventory is loaded.
- [ ] Approved claim bank is loaded.
- [ ] Banned claim bank is loaded.
- [ ] Claims are graded before script generation.
- [ ] Realism filter runs after generation.
- [ ] Compliance filter runs before final output.
- [ ] Final output includes recommended/aggressive/soft versions.

## Safety checks

The final output must not say:

- [ ] “I guarantee”
- [ ] “I can get you top 3”
- [ ] “Top 3 gets 70%” without source
- [ ] Fake case studies
- [ ] Fake scarcity
- [ ] “Google will show you above competitors”

## Realism checks

- [ ] 10-second cold call opener exists.
- [ ] CTA is low pressure.
- [ ] Script sounds like a local operator.
- [ ] Script does not sound like a webinar pitch.
- [ ] Script can be spoken naturally.
