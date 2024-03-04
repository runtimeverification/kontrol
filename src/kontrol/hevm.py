from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply

if TYPE_CHECKING:
    from pyk.kast.inner import KInner


class Hevm:
    @staticmethod
    def help_info() -> list[str]:
        res_lines: list[str] = []
        print_foundry_success_info = any('hevm_success' in line for line in res_lines)
        if print_foundry_success_info:
            res_lines.append('')
            res_lines.append('See `hevm_success` predicate for more information:')
            res_lines.append(
                'https://github.com/runtimeverification/kontrol/blob/master/src/kontrol/kdist/hevm.md#hevm-success-predicate'
            )
        res_lines.append('')
        res_lines.append(
            'Access documentation for KEVM foundry integration at https://docs.runtimeverification.com/kontrol'
        )
        return res_lines

    @staticmethod
    def hevm_success(s: KInner, dst: KInner, out: KInner) -> KApply:
        return KApply('hevm_success', [s, dst, out])

    @staticmethod
    def hevm_fail(s: KInner, dst: KInner) -> KApply:
        return KApply('hevm_fail', [s, dst])
