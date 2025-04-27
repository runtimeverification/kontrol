from __future__ import annotations

from typing import TYPE_CHECKING

from pyk.kast.inner import KApply

if TYPE_CHECKING:
    from pyk.kast.inner import KInner


class Hevm:
    @staticmethod
    def hevm_success(s: KInner, dst: KInner, out: KInner) -> KApply:
        return KApply('hevm_success', [s, dst, out])

    @staticmethod
    def hevm_fail(s: KInner, dst: KInner) -> KApply:
        return KApply('hevm_fail', [s, dst])
