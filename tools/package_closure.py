"""Read-only package closure summary. Simulation is not installation or VM acceptance."""
import bootstrap_packages
import upgrade_policy
import user_install


def summarize(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('transaction'), dict):
        raise ValueError('Package review payload is incomplete')
    transaction = payload['transaction']
    requested = set(payload.get('packages') or [])
    new = transaction.get('new') or []
    if not isinstance(new, list) or any(not isinstance(name, str) for name in new):
        raise ValueError('Package simulation additions are invalid')
    direct = [name for name in new if name.split(':', 1)[0] in requested]
    dependencies = [name for name in new if name not in direct]
    return {'requested': len(requested), 'missing_candidates': len(payload.get('pinned') or []),
            'direct_additions': direct, 'dependency_additions': dependencies,
            'changes': list(transaction.get('upgraded_or_changed') or []),
            'removals': list(transaction.get('removed') or []),
            'blockers': list(payload.get('blockers') or []),
            'upgrade_policy': upgrade_policy.classify(transaction),
            'closure_accepted': False, 'packages_installed': False,
            'note': 'Dependency simulation is not a stock-Ubuntu closure or upgrade approval.'}


def review(root, run=None):
    parent = user_install.private_directory(root / 'work/bootstrap')
    case = user_install.private_directory(parent / ('closure-' + user_install.stamp()))
    plan = bootstrap_packages.prepare(case, run=run) if run else bootstrap_packages.prepare(case)
    summary = summarize(plan['payload'])
    summary.update(status='blocked' if plan.get('blockers') else 'review-required',
                   native_blockers=plan.get('blockers') or [])
    return summary
