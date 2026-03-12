from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_release_control_plane.demo.scenarios import bundle_for_scenario
from ai_release_control_plane.logging_utils import configure_logging
from ai_release_control_plane.runtime.control_plane import ControlPlane


def _cp(args: argparse.Namespace) -> ControlPlane:
    return ControlPlane(
        profile=getattr(args, "profile", "local-demo"),
        mode=getattr(args, "mode", "mock"),
        scenario=getattr(args, "scenario", "success"),
    )


def _print(payload: object) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _resolve_candidate(cp: ControlPlane, args: argparse.Namespace) -> str:
    candidate = getattr(args, "candidate", None)
    bundle = getattr(args, "bundle", None)
    if candidate:
        return candidate
    if bundle:
        return cp.create_candidate(bundle, actor=getattr(args, "actor", "cli")).candidate_id
    msg = "Provide --candidate or --bundle"
    raise ValueError(msg)


def cmd_register_bundle(args: argparse.Namespace) -> None:
    cp = _cp(args)
    bundle = cp.register_bundle(Path(args.file), actor=args.actor)
    _print(bundle.model_dump(mode="json"))


def cmd_diff_bundles(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.diff_bundles(args.base_bundle, args.candidate_bundle))


def cmd_validate_offline(args: argparse.Namespace) -> None:
    cp = _cp(args)
    result = cp.evaluate_offline(_resolve_candidate(cp, args), args.environment)
    _print(result.model_dump(mode="json"))


def cmd_run_shadow(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _ = args.environment
    result = cp.run_shadow(_resolve_candidate(cp, args))
    _print(result.model_dump(mode="json"))


def cmd_rollout_start(args: argparse.Namespace) -> None:
    cp = _cp(args)
    rollout = cp.start_rollout(_resolve_candidate(cp, args), args.environment, args.strategy)
    _print(rollout)


def cmd_rollout_pause(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.rollout.pause(args.rollout_id))


def cmd_rollout_resume(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.rollout.resume(args.rollout_id))


def cmd_rollout_abort(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.rollout.abort(args.rollout_id, args.reason))


def cmd_promote(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.promote(_resolve_candidate(cp, args), actor=args.actor).model_dump(mode="json"))


def cmd_rollback(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.rollback(_resolve_candidate(cp, args), args.reason, actor=args.actor))


def cmd_approve(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _ = args.environment
    rec = cp.approve(
        _resolve_candidate(cp, args), args.approver, args.role, args.reason, approved=not args.reject
    )
    _print(rec.model_dump(mode="json"))


def cmd_inspect(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.inspect(args.entity, args.id))


def cmd_report(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _ = args.bundle
    _print(cp.report(_resolve_candidate(cp, args), args.format))


def cmd_doctor(args: argparse.Namespace) -> None:
    cp = _cp(args)
    _print(cp.doctor())


def cmd_demo_run(args: argparse.Namespace) -> None:
    cp = _cp(args)
    bundle = cp.register_bundle(bundle_for_scenario(args.scenario), actor="demo")
    candidate = cp.create_candidate(bundle.bundle_id, actor="demo", notes=f"scenario={args.scenario}")
    offline = cp.evaluate_offline(candidate.candidate_id, bundle.target_environment.value)
    if not offline.passed:
        memo = cp.report(candidate.candidate_id, args.output_format)
        _print({"status": "blocked_offline", "candidate_id": candidate.candidate_id, "memo": memo})
        return
    shadow = cp.run_shadow(candidate.candidate_id)
    if not shadow.passed and args.scenario == "shadow_disagreement":
        memo = cp.report(candidate.candidate_id, args.output_format)
        _print({"status": "hold_shadow", "candidate_id": candidate.candidate_id, "memo": memo})
        return
    rollout = cp.start_rollout(candidate.candidate_id, bundle.target_environment.value, args.strategy)
    rollout_result = cp.run_rollout_until_decision(rollout["rollout_id"])
    if rollout_result["status"] == "rolled_back":
        memo = cp.report(candidate.candidate_id, args.output_format)
        _print({"status": "rolled_back", "candidate_id": candidate.candidate_id, "memo": memo})
        return
    cp.approve(candidate.candidate_id, approver="release-manager", role="release_board", reason="demo")
    decision = cp.promote(candidate.candidate_id, actor="release-manager")
    memo = cp.report(candidate.candidate_id, args.output_format)
    _print(
        {
            "status": "promoted",
            "candidate_id": candidate.candidate_id,
            "decision": decision.model_dump(mode="json"),
            "memo": memo,
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="releasectl")
    parser.add_argument("--profile", default="local-demo")
    parser.add_argument("--mode", default="mock", choices=["mock", "real"])
    parser.add_argument("--scenario", default="success")
    parser.add_argument("--log-level", default="INFO")

    def add_common_args(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--profile", default="local-demo")
        sp.add_argument("--mode", default="mock", choices=["mock", "real"])
        sp.add_argument("--scenario", default="success")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("register-bundle")
    add_common_args(p)
    p.add_argument("--file", required=True)
    p.add_argument("--actor", default="system")
    p.set_defaults(func=cmd_register_bundle)

    p = sub.add_parser("diff-bundles")
    add_common_args(p)
    p.add_argument("--base-bundle", required=True)
    p.add_argument("--candidate-bundle", required=True)
    p.set_defaults(func=cmd_diff_bundles)

    p = sub.add_parser("validate-offline")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--environment", required=True)
    p.set_defaults(func=cmd_validate_offline)

    p = sub.add_parser("run-shadow")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--environment")
    p.set_defaults(func=cmd_run_shadow)

    p = sub.add_parser("rollout")
    add_common_args(p)
    rollout_sub = p.add_subparsers(dest="rollout_command", required=True)
    rs = rollout_sub.add_parser("start")
    add_common_args(rs)
    rs.add_argument("--candidate")
    rs.add_argument("--bundle")
    rs.add_argument("--environment", required=True)
    rs.add_argument("--strategy", default="canary")
    rs.set_defaults(func=cmd_rollout_start)
    rp = rollout_sub.add_parser("pause")
    add_common_args(rp)
    rp.add_argument("--rollout-id", required=True)
    rp.set_defaults(func=cmd_rollout_pause)
    rr = rollout_sub.add_parser("resume")
    add_common_args(rr)
    rr.add_argument("--rollout-id", required=True)
    rr.set_defaults(func=cmd_rollout_resume)
    ra = rollout_sub.add_parser("abort")
    add_common_args(ra)
    ra.add_argument("--rollout-id", required=True)
    ra.add_argument("--reason", required=True)
    ra.set_defaults(func=cmd_rollout_abort)

    p = sub.add_parser("promote")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--actor", default="system")
    p.set_defaults(func=cmd_promote)

    p = sub.add_parser("rollback")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--reason", required=True)
    p.add_argument("--actor", default="operator")
    p.set_defaults(func=cmd_rollback)

    p = sub.add_parser("approve")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--environment")
    p.add_argument("--approver", default="release-manager")
    p.add_argument("--role", default="release_board")
    p.add_argument("--reason", default="")
    p.add_argument("--reject", action="store_true")
    p.set_defaults(func=cmd_approve)

    p = sub.add_parser("inspect")
    add_common_args(p)
    p.add_argument("--entity", required=True)
    p.add_argument("--id")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("report")
    add_common_args(p)
    p.add_argument("--candidate")
    p.add_argument("--bundle")
    p.add_argument("--format", default="json", choices=["json", "markdown", "html", "csv"])
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("doctor")
    add_common_args(p)
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("demo-run")
    add_common_args(p)
    p.add_argument("--strategy", default="canary")
    p.add_argument("--output-format", default="json", choices=["json", "markdown", "html", "csv"])
    p.set_defaults(func=cmd_demo_run)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()
