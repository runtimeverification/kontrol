from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply

if TYPE_CHECKING:
    from pyk.kast.inner import KInner


class Hevm:
    @staticmethod
    def help_info(proof_id: str) -> list[str]:
        res_lines: list[str] = []
        _, test = proof_id.split('.')
        if not test.startswith('proveFail'):
            res_lines.append('')
            res_lines.append('See `hevm_success` predicate for more information:')
            res_lines.append(
                'https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/hevm.md#hevm-success-predicate'
            )
        else:
            res_lines.append('')
            res_lines.append('See `hevm_fail` predicate for more information:')
            res_lines.append(
                'https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/hevm.md#hevm-fail-predicate'
            )
        res_lines.append('')
        res_lines.append('Access documentation for Kontrol at https://docs.runtimeverification.com/kontrol')
        return res_lines

    @staticmethod
    def hevm_success(s: KInner, dst: KInner, out: KInner) -> KApply:
        return KApply('hevm_success', [s, dst, out])

    @staticmethod
    def hevm_fail(s: KInner, dst: KInner) -> KApply:
        return KApply('hevm_fail', [s, dst])
