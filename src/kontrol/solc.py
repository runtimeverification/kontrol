from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import deque
from functools import cache, cached_property
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

import pyevmasm  # type: ignore

if TYPE_CHECKING:
    from typing import Any

    Json = dict[str, Any]

    """
    An AstNodeSourceMapEntry is triple (s,l,f) where
    s denotes the start offset in bytes
    l denotes the length in bytes
    f denotes the identifier of the source unit
    See: https://docs.soliditylang.org/en/latest/internals/source_mappings.html
    """
    AstNodeSourceMapEntry = tuple[int, int, int]

    """
    A ContractSourceMapEntry is a tuple (s,l,f,j,m) where
    s denotes the start offset in bytes
    l denotes the length in bytes
    f denotes the identifier of the source unit
    j denotes the jump type 'i', 'o', or '-'
    m denotes the modifier depth
    See: https://docs.soliditylang.org/en/latest/internals/source_mappings.html
    """
    ContractSourceMapEntry = tuple[int, int, int, str, int]

    """
    A contract source map is a map from instruction offsets to source map entries.
    See: https://docs.soliditylang.org/en/latest/internals/source_mappings.html
    """
    ContractSourceMap = dict[int, ContractSourceMapEntry]

    """
    A line,column pair
    """
    LineColumn = tuple[int, int]

    """
    A source range is a tuple (start_line, start_column, end_line, end_column)
    """
    SourceRange = tuple[int, int, int, int]


_LOGGER = logging.getLogger(__name__)


class Instruction:

    data: pyevmasm.Instruction
    compilation_unit: CompilationUnit
    contract: ContractSource
    source_map_entry: ContractSourceMapEntry
    offset: int

    def __init__(
        self,
        data: pyevmasm.Instruction,
        compilation_unit: CompilationUnit,
        contract: ContractSource,
        source_map_entry: ContractSourceMapEntry,
        offset: int,
    ):
        self.data = data
        self.compilation_unit = compilation_unit
        self.contract = contract
        self.source_map_entry = source_map_entry
        self.offset = offset

    @property
    def pc(self) -> int:
        return self.data.pc

    @property
    def bytes(self) -> bytes:
        return self.data.bytes

    @property
    def operand_size(self) -> int:
        return self.data.operand_size

    def __str__(self) -> str:
        return f'{self.data}'

    def source_range(self) -> SourceRange:
        try:
            (s, l, f, *_) = self.source_map_entry
            try:
                source = self.compilation_unit.get_source_by_id(f)
            except KeyError:
                try:
                    source = self.contract.generated_sources[f]
                except KeyError:
                    return (1, 1, 1, 1)
            start_line, start_column = source.offset_to_position(s)
            end_line, end_column = source.offset_to_position(s + l - 1)
            return (start_line, start_column, end_line, end_column)
        except Exception:
            return (1, 1, 1, 1)

    def node(self) -> AstNode:
        try:
            s, l, f, j, m = self.source_map_entry
            try:
                source = self.compilation_unit.get_source_by_id(f)
            except KeyError:
                source = self.contract.generated_sources[f]
            node = source.ast.find_by_range(s, s + l)
            assert node is not None
            return node
        except Exception as error:
            raise Exception('Node not found.') from error

    def is_jump_in(self) -> bool:
        return self.source_map_entry[3] == 'i'

    def is_jump_out(self) -> bool:
        return self.source_map_entry[3] == 'o'


class AstNode:
    json: Json
    parent: AstNode | None
    source: Source

    def __init__(self, dct: Json, source: Source, parent: AstNode | None = None):
        self.json = dct
        self.source = source
        self.parent = parent

    def __hash__(self) -> int:
        result = self.json.get('id')
        if isinstance(result, int):
            return result
        result = self.json.get('src')
        if isinstance(result, str):
            return hash(result)
        raise TypeError('AstNode.id is not an int.')

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AstNode):
            return False
        return self.json.get('src') == other.json.get('src')

    ###########################################################################
    # Traveral Methods

    def _children(self) -> Iterator[AstNode]:
        """Iterate all direct children."""
        values = self.json.values()
        for value in values:
            if AstNode.is_solidity_node_like(value):
                yield AstNode(value, self.source, self)
            elif isinstance(value, list):
                for child in value:
                    if AstNode.is_solidity_node_like(child):
                        yield AstNode(child, self.source, self)
        return

    @cache  # noqa: B019
    def children(self) -> list[AstNode]:
        return list(self._children())

    def descendants(self) -> Iterator[AstNode]:
        """Iterate all descendants in breadth-first order."""
        queue = deque(self.children())
        while len(queue) > 0:
            current = queue.popleft()
            yield current
            queue.extend(current.children())
        return

    def ancestors(self) -> Iterator[AstNode]:
        """Iterate all ancestor nodes from younger to older"""
        current = self.parent
        while current is not None:
            yield current
            current = current.parent
        return

    def root(self) -> AstNode:
        """Return the root node"""
        current = self
        while current.parent is not None:
            current = current.parent
        return current

    def closest_block(self) -> AstNode | None:
        """Find the closest surrounding block."""
        if self.is_block():
            return self
        for ancestor in self.ancestors():
            if ancestor.is_block():
                return ancestor
        return None

    def closest_for_loop(self) -> AstNode | None:
        """Find the closest surrounding for loop."""
        if self.is_for_loop():
            return self
        for ancestor in self.ancestors():
            if ancestor.is_for_loop():
                return ancestor
        return None

    def enclosing_block(self) -> AstNode | None:
        """Find the closest surrounding block."""
        for ancestor in self.ancestors():
            if ancestor.is_block():
                return ancestor
        return None

    def closest_stmt(self) -> AstNode | None:
        """Find the closest parent statement."""
        if self.is_solidity_statement():
            return self
        for ancestor in self.ancestors():
            if ancestor.is_solidity_statement():
                return ancestor
        return None

    def closest_stmt_or_block(self) -> AstNode | None:
        """Find the closest parent statement or block."""
        if self.is_statement() or self.is_block():
            return self
        for ancestor in self.ancestors():
            if ancestor.is_statement() or ancestor.is_block():
                return ancestor
        return None

    def closest_function_definition(self) -> AstNode | None:
        """Find the closest parent function definition"""
        if self.is_function_definition() or self.is_modifier_definition():
            return self
        for ancestor in self.ancestors():
            if ancestor.is_function_definition() or ancestor.is_modifier_definition():
                return ancestor
        return None

    def closest_contract_definition(self) -> AstNode | None:
        """Find the closest parent contract definition"""
        if self.json.get('nodeType') == 'ContractDefinition':
            return self
        for ancestor in self.ancestors():
            if ancestor.json.get('nodeType') == 'ContractDefinition':
                return ancestor
        return None

    def is_first_in_block(self) -> bool:
        """Check if the node is the first in a block"""
        block = self.enclosing_block()
        if block is None:
            return False
        children = list(block.children())
        return children[0] == self

    def is_first_in_for_loop(self) -> bool:
        """Check if the node is the first in a for loop"""
        loop = self.closest_for_loop()
        if loop is None:
            return False
        initialization_expression = AstNode(loop.json.get('initializationExpression', {}), self.source, loop)
        return self == initialization_expression

    def is_last_in_block(self) -> bool:
        """Check if the node is the last in a block"""
        block = self.enclosing_block()
        if block is None:
            return False
        children = list(block.children())
        return children[-1] == self

    def first_stmt(self) -> AstNode | None:
        """
        Find the first stmt in the function body if any.
        """
        if not self.is_function_definition():
            return None

        stmts = self.json.get('body', {}).get('statements', [])
        if len(stmts) > 0:
            return AstNode(stmts[0], self.source, self)
        return None

    def nearest_stmt(self) -> AstNode | None:
        """
        Find the nearest statement.

        If the current node is inside a statement, we return the closest stmt.
        Otherwise, if the current node is in the initialization of a function,
        we return the first statement.

        Otherwise, if the current node is at the end of a function,
        we return the last statement.
        """
        stmt = self.closest_stmt()
        if stmt is not None:
            return stmt

        f = self.closest_function_definition()
        if f is None:
            return None
        stmt = f.first_stmt()
        return stmt

    def variable_declarations(self) -> Iterator[AstNode]:
        """Iterate all descendant variable declarations"""
        for descendant in self.descendants():
            if descendant.is_variable_declaration():
                yield descendant
        return

    def declaring_scope(self) -> AstNode | None:
        """If this node is a variable declaration, return it's declaring scope."""
        if not self.is_variable_declaration():
            return None
        scope_id = self.json.get('scope')
        if isinstance(scope_id, int):
            return self.root().find_by_id(scope_id)
        raise TypeError('AstNode.scope is not an int.')

    def local_variable_declarations(self) -> Iterator[AstNode]:
        if not self.is_block():
            return
        scope_id = self.json.get('id')
        for declaration in self.variable_declarations():
            if declaration.json.get('scope', None) == scope_id:
                yield declaration
        return

    def for_variable_declarations(self) -> Iterator[AstNode]:
        if not self.is_for_loop():
            return
        scope_id = self.json.get('id')
        for declaration in self.variable_declarations():
            if declaration.json.get('scope', None) == scope_id:
                yield declaration
        return

    def variable_info(self) -> tuple[str, str]:
        if not self.is_variable_declaration():
            return '', ''
        else:
            return (
                self.json.get('typeDescriptions', {}).get('typeIdentifier', ''),
                self.json.get('storageLocation', ''),
            )

    def variable_reference_declaration_id(self) -> int:
        if not self.is_variable_declaration():
            return -1
        else:
            return self.json.get('typeName', {}).get('referencedDeclaration', -1)

    def find_by_id(self, node_id: int) -> AstNode | None:  # type: ignore
        """Search all descendants for the given node id."""
        if self.json.get('id') == node_id:
            return self

        for descendant in self.descendants():
            if descendant.json.get('id') == node_id:
                return descendant

    @cache  # noqa: B019
    def sourcemap(self) -> AstNodeSourceMapEntry:
        """Return the source map associated with this node.

        The first component is the start offset in unicode points.
        The second compnent is the length in unicode points.
        The third compnent is the identifier of the source unit.
        """
        parts = self.json['src'].split(':')
        start, length, source_id = (int(part) for part in parts)
        return (start, length, source_id)

    def source_text(self) -> str:
        """Return the source text associated with this node."""
        start, length, source_id = self.sourcemap()
        return self.source.source_text[start : start + length]

    def find_by_range(self, range_start: int, range_end: int) -> AstNode | None:
        """Find the inner-most AstNode surrounding the given source range"""
        start, l, source_id = self.sourcemap()  # noqa: E741
        end = start + l
        if not (start <= range_start and range_end <= end):
            return None
        closest = self
        queue = deque(self.children())
        while len(queue) > 0:
            current = queue.popleft()
            start, l, source_id = current.sourcemap()  # noqa: E741
            end = start + l
            if start <= range_start and range_end <= end:
                queue = deque(current.children())
                closest = current
        return closest

    def find_in_line(self, line: int) -> list[AstNode]:
        """Find all AstNodes starting in the given source line

        The line and column numbers start at 1.
        """
        line_offset = self.source.position_to_offset((line, 1))
        next_line_offset = self.source.position_to_offset((line + 1, 1))
        result: list[AstNode] = []
        queue = deque(self.descendants())
        while len(queue) > 0:
            current = queue.popleft()
            node_offset, _, _ = current.sourcemap()
            if line_offset <= node_offset and node_offset < next_line_offset:
                result.append(current)
        return result

    @cached_property
    def line(self) -> int | None:
        """Return the line number of this node."""
        start, _, _ = self.sourcemap()
        return self.source.offset_to_position(start)[0]

    @cached_property
    def column(self) -> int | None:
        """Return the column number of this node."""
        start, _, _ = self.sourcemap()
        return self.source.offset_to_position(start)[1]

    def source_range(self) -> SourceRange:
        start, l, _ = self.sourcemap()
        range = self.source.offset_to_position(start) + self.source.offset_to_position(start + l - 1)
        return range

    def find_in_offset(self, line_offset: int) -> list[AstNode]:
        """Find all AstNodes starting in the given source line

        The line and column numbers start at 1.
        """
        # line_offset = self.source.position_to_offset((line, 1))xw
        result: list[AstNode] = []
        queue = deque(self.descendants())
        while len(queue) > 0:
            current = queue.popleft()
            node_offset, _, _ = current.sourcemap()
            if line_offset <= node_offset and node_offset < (line_offset + 1):
                result.append(current)
        return result

    def get(self, name: str, default: Any) -> Any:
        if name in self.json:
            return self.json[name]
        else:
            return default

    ###########################################################################
    # Type Checking

    def is_constructor(self) -> bool:
        return self.is_function_definition() and self.json.get('kind') == 'constructor'

    @staticmethod
    def is_node_like(node: Any) -> bool:
        return isinstance(node, dict) and 'nodeType' in node and isinstance(node['nodeType'], str)

    @staticmethod
    def is_solidity_node_like(node: Any) -> bool:
        return AstNode.is_node_like(node) and not node['nodeType'].startswith('Yul')

    def is_statement(self) -> bool:
        return self.is_solidity_statement() or self.is_yul_statement()

    def is_solidity_statement(self) -> bool:
        node_type = self.json['nodeType']
        is_pure_statement = node_type.endswith('Statement')
        is_yul = node_type.startswith('Yul')
        if is_pure_statement and not is_yul:
            return node_type not in ('ForStatement', 'WhileStatement', 'IfStatement')
        if node_type == 'Return':
            return True
        if self.is_condition():
            return True
        return False

    def is_yul_statement(self) -> bool:
        return self.json['nodeType'] in (
            'YulAssignment',
            'YulExpressionStatement',
            'YulIf',
            'YulSwitch',
            'YulForLoop',
            'YulLeave',
            'YulBreak',
            'YulContinue',
            'YulFunctionCall',
        )

    def is_function_definition(self) -> bool:
        return self.is_yul_function_definition() or self.is_solidity_function_definition()

    def is_yul_function_definition(self) -> bool:
        return self.json['nodeType'] == 'YulFunctionDefinition'

    def is_solidity_function_definition(self) -> bool:
        return self.json['nodeType'] == 'FunctionDefinition'

    def is_modifier_definition(self) -> bool:
        return self.json['nodeType'] == 'ModifierDefinition'

    def is_block(self) -> bool:
        return self.json['nodeType'] == 'Block'

    def is_if(self) -> bool:
        return self.json['nodeType'] == 'IfStatement'

    def is_for_loop(self) -> bool:
        return self.json['nodeType'] == 'ForStatement'

    def is_condition(self) -> bool:
        if self.parent is None:
            return False
        if not 'condition' in self.parent.json:
            return False
        return self.json == self.parent.json['condition']

    def is_while_loop(self) -> bool:
        return self.json['nodeType'] == 'WhileStatement'

    def is_variable_declaration(self) -> bool:
        return self.json['nodeType'] == 'VariableDeclaration'

    def is_variable_declaration_statement(self) -> bool:
        return self.json['nodeType'] == 'VariableDeclarationStatement'


class Source:
    """
    Represents a source unit used during compilation.
    """

    _uuid: int

    """
    Virtual name of the source. This looks like a file path,
    but it might be a generated pseudo name.
    """
    _name: str

    """
    The output standard Json, i.e. output.sources.$name
    """
    _json: Json

    """
    The original source text.
    """
    _source_text: str

    """
    A flag indicating that this source was generated by the compiler.
    """
    _generated: bool

    """
    A map of byte offsets to (line, column)-pairs.
    """
    _positions: dict[int, LineColumn]

    """
    A map of (line, column)-pairs to byte offsets.
    """
    _offsets: dict[LineColumn, int]

    def __init__(self, uuid: int, name: str, json: Json, source_text: str, generated: bool = False):
        self._uuid = uuid
        self._name = name
        self._json = json
        self._source_text = source_text
        self._generated = generated
        self._positions = {}
        self._offsets = {}
        self._cache_source_map()

    @property
    def uuid(self) -> int:
        """
        A universal unique identifier for the source unit.
        Use id to get a local relative to the compilation unit.
        """
        return self._uuid

    @property
    def id(self) -> int:
        """
        The local id of the source unit relative to the compilation unit.
        Use uuid to get a univeral id.
        """
        result = self._json.get('id')
        if isinstance(result, int):
            return result
        raise TypeError('Source.json.id is not an int.')

    @property
    def ast(self) -> AstNode:
        dct = self._json.get('ast')
        if isinstance(dct, dict):
            return AstNode(dct, self)
        raise TypeError('Source.json.ast is not a dict.')

    def offset_to_position(self, offset: int) -> LineColumn:
        """Return the (line, column)-pair for a given byte-offset.

        lines and columns start at 1.
        """
        return self._positions[offset]

    def position_to_offset(self, position: LineColumn) -> int:
        """Return the byte-offset of a given (line, column)-pair

        lines and columns start at 1.
        """
        return self._offsets[position]

    @property
    def source_text(self) -> str:
        return self._source_text

    def _cache_source_map(self) -> None:
        line, column = (1, 1)
        for offset in range(len(self.source_text)):
            self._positions[offset] = (line, column)
            self._offsets[(line, column)] = offset
            char = self.source_text[offset]
            if char == '\n':
                line, column = (line + 1, 1)
            else:
                column = column + len(char.encode('utf-8'))

    @property
    def offsets(self) -> dict[LineColumn, int]:
        """Map from (line, column)-pairs to byte offsets."""
        return self._offsets

    @property
    def name(self) -> str:
        return self._name

    def is_generated(self) -> bool:
        return self._generated


class ContractSource:
    _uuid: int
    _file_path: str
    _contract_name: str
    _json: Any
    _compilation_unit: CompilationUnit

    _source_map: ContractSourceMap
    _init_source_map: ContractSourceMap
    _storage_layout: list[dict[str, Any]]

    def __init__(
        self, id: int, file_path: str, contract_name: str, json: Any, compilation_unit: CompilationUnit
    ) -> None:
        self._uuid = id
        self._file_path = file_path
        self._contract_name = contract_name
        self._json = json
        self._compilation_unit = compilation_unit
        self._source_map = {}
        self._init_source_map = {}
        self._cache_source_map()
        self._cache_init_source_map()
        self._storage_layout = []

    @property
    def uuid(self) -> int:
        """
        A unique identifier for the contract.
        """
        return self._uuid

    @property
    def file_path(self) -> str:
        """
        The file path for the contract.
        """
        return self._file_path

    @cached_property
    def generated_sources(self) -> dict[int, Source]:
        """
        Return a map of all associated generated sources.

        The key is the local source id (not the uuid) of the source.
        """
        sources: dict[int, Source] = {}
        generated_sources = self._json.get('evm', {}).get('bytecode', {}).get('generatedSources', [])
        generated_sources += self._json.get('evm', {}).get('deployedBytecode', {}).get('generatedSources', [])
        for generated_source in generated_sources:
            source_id = generated_source['id']
            source_uuid = to_uuid(f'{self.uuid}:{source_id}')
            name = generated_source.get('name')
            contents = generated_source.get('contents', '')
            source = Source(source_uuid, name, generated_source, contents, True)
            sources[source.id] = source
        return sources

    @cached_property
    def instructions(self) -> list[Instruction]:
        def map(offset: int, instruction: pyevmasm.Instruction) -> Instruction:
            source_map_entry = self._source_map.get(offset, (-1, -1, -1, '-', 0))
            return Instruction(instruction, self._compilation_unit, self, source_map_entry, offset)

        return [
            map(offset, instruction)
            for offset, instruction in enumerate(pyevmasm.disassemble_all(self.get_deployed_bytecode))
        ]

    @cached_property
    def init_instructions(self) -> list[Instruction]:
        def map(offset: int, instruction: pyevmasm.Instruction) -> Instruction:
            source_map_entry = self._init_source_map.get(offset, (-1, -1, -1, '-', 0))
            return Instruction(instruction, self._compilation_unit, self, source_map_entry, offset)

        return [
            map(offset, instruction)
            for offset, instruction in enumerate(pyevmasm.disassemble_all(self.get_init_bytecode))
        ]

    @cached_property
    def pc_to_instruction_offsets(self) -> dict[int, int]:
        result = {}
        for i, instr in enumerate(self.instructions):
            pc_start = instr.pc
            pc_end = instr.pc + instr.operand_size + 1
            for pc in range(pc_start, pc_end):
                result[pc] = i
        return result

    @cached_property
    def init_pc_to_instruction_offsets(self) -> dict[int, int]:
        result = {}
        for i, instr in enumerate(self.init_instructions):
            pc_start = instr.pc
            pc_end = instr.pc + instr.operand_size + 1
            for pc in range(pc_start, pc_end):
                result[pc] = i
        return result

    def instruction_by_pc(self, pc: int) -> Instruction:
        offset = self.pc_to_instruction_offsets[pc]
        return self.instructions[offset]

    def init_instruction_by_pc(self, pc: int) -> Instruction:
        offset = self.init_pc_to_instruction_offsets[pc]
        return self.init_instructions[offset]

    @cached_property
    def get_deployed_bytecode(self) -> bytes:
        ref = self._json.get('evm') if 'evm' in self._json else self._json
        raw = ref.get('deployedBytecode').get('object').removeprefix('0x')
        return bytes.fromhex(raw)

    @cached_property
    def get_init_bytecode(self) -> bytes:
        ref = self._json.get('evm') if 'evm' in self._json else self._json
        raw = ref.get('bytecode').get('object').removeprefix('0x')
        return bytes.fromhex(raw)

    @property
    def get_source_map(self) -> ContractSourceMap:
        """Map from instruction to source map entries

        See: https://docs.soliditylang.org/en/latest/internals/source_mappings.html
        """
        return self._source_map

    def get_storage(self) -> list[dict[str, Any]]:
        return self._json.get('storageLayout', {}).get('storage', [])

    def offset_to_source_map_entry(self, offset: int) -> ContractSourceMapEntry:
        return self._source_map.get(offset, (-1, -1, -1, '-', 0))

    def offset_to_init_source_map_entry(self, offset: int) -> ContractSourceMapEntry:
        return self._init_source_map.get(offset, (-1, -1, -1, '-', 0))

    def _cache_source_map(self) -> None:
        ref = self._json.get('evm') if 'evm' in self._json else self._json
        raw = ref.get('deployedBytecode', {}).get('sourceMap', '')
        instrs_srcmap = raw.split(';')
        s, l, f, j, m = (0, 0, 0, '', 0)  # noqa: E741
        for i, instr_srcmap in enumerate(instrs_srcmap):
            fields = instr_srcmap.split(':')
            s = int(fields[0]) if len(fields) > 0 and fields[0] else s
            l = int(fields[1]) if len(fields) > 1 and fields[1] else l  # noqa: E741
            f = int(fields[2]) if len(fields) > 2 and fields[2] else f
            j = fields[3] if len(fields) > 3 and fields[3] else j
            m = int(fields[4]) if len(fields) > 4 and fields[4] else m
            self._source_map[i] = (s, l, f, j, m)

    def _cache_init_source_map(self) -> None:
        ref = self._json.get('evm') if 'evm' in self._json else self._json
        raw = ref.get('bytecode', {}).get('sourceMap', '')
        instrs_srcmap = raw.split(';')
        s, l, f, j, m = (0, 0, 0, '', 0)  # noqa: E741
        for i, instr_srcmap in enumerate(instrs_srcmap):
            fields = instr_srcmap.split(':')
            s = int(fields[0]) if len(fields) > 0 and fields[0] else s
            l = int(fields[1]) if len(fields) > 1 and fields[1] else l  # noqa: E741
            f = int(fields[2]) if len(fields) > 2 and fields[2] else f
            j = fields[3] if len(fields) > 3 and fields[3] else j
            m = int(fields[4]) if len(fields) > 4 and fields[4] else m
            self._init_source_map[i] = (s, l, f, j, m)


class CompilationUnit:
    """Easy access to Solidity standard json"""

    _id: int
    _sources: dict[int, Source]  # Source UUID => Source
    _contracts: dict[bytes, ContractSource]

    def __init__(self, id: int, sources: dict[int, Source], contracts: dict[bytes, ContractSource]):
        self._id = id
        self._sources = sources
        self._contracts = contracts

    @property
    def uuid(self) -> int:
        """
        A unique identifier for the compilation unit.
        """
        return self._id

    @staticmethod
    def load_build_info(foundry_root: Path) -> CompilationUnit:
        build_info_files = (foundry_root / 'out' / 'build-info').glob('*.json')
        build_info = json.loads(max(build_info_files, key=os.path.getmtime).read_text())
        sources: dict[int, Source] = {}  # Source id => Source
        contracts: dict[bytes, ContractSource] = {}  # CBOR metadata => contract
        compilation_unit_uuid = to_uuid(build_info['id'])
        compilation_unit = CompilationUnit(compilation_unit_uuid, sources, contracts)
        try:
            for source_name, source_json in build_info.get('output', {}).get('sources', {}).items():
                absolute_path = source_json.get('ast').get('absolutePath')
                source_uuid = to_uuid(f'{compilation_unit_uuid}:{source_name}')
                source_text = build_info.get('input', {}).get('sources', {}).get(source_name, {}).get('content', '')
                source = Source(source_uuid, source_name, source_json, source_text)
                sources[source_uuid] = source
                contracts_json = build_info.get('output', {}).get('contracts', {}).get(source_name, {})
                for contract_name, contract_json in contracts_json.items():
                    contract_uuid = to_uuid(f'{source_uuid}:{contract_name}')
                    contract = ContractSource(
                        contract_uuid, absolute_path, contract_name, contract_json, compilation_unit
                    )
                    contract_bytecode = contract.get_deployed_bytecode
                    cbor_data = CompilationUnit.get_cbor_data(contract_bytecode)
                    contracts[cbor_data] = contract

                    # Add all generated sources
                    for generated_source in contract.generated_sources.values():
                        sources[generated_source.uuid] = generated_source

        except (KeyError, IndexError):
            _LOGGER.error(
                '.output.contracts.$contract_name.evm.deployedBytecode.generatedSources not found in build-info file.'
            )
        except FileNotFoundError:
            _LOGGER.error('No build-info file found in build-info directory.')

        return compilation_unit

    def contracts(self) -> list[ContractSource]:
        return list(self._contracts.values())

    def get_instruction(self, contract_bytecode: bytes, pc: int) -> Instruction:
        # First try to match init bytecode 1-to-1
        try:
            contract_source = self.get_contract_by_initcode(contract_bytecode)
            return contract_source.init_instruction_by_pc(pc)
        except Exception:
            pass

        # We cannot identify the contract by the full deployed bytecode.

        # The deployed bytecode on-chain can be different from the
        # deployed bytecode given in the standard json.
        # This can for example be the case, when a library is linked at deployment time
        # or when an immutable varirable is initialized at deployment time.
        # Hence, to identify the contract, we only look at the CBOR-encoded metadata
        # at the end of the bytecode. This metadata should not change between deployments.

        # We don't actually need to decode it, we just need to know the length of the metadata.
        cbor_data = CompilationUnit.get_cbor_data(contract_bytecode)
        contract = self._contracts.get(cbor_data, None)
        if contract is not None:
            return contract.instruction_by_pc(pc)

        # The former method can fail to detect the contract, if the CBOR_DATA
        # is not at the end of the bytecode. In this case we use this slower
        # method to find the contract. Notice, that it is possible to trick
        # the method into return the wrong contract by copying the CBOR_DATA
        # of another contract into the malicuous contract's bytecode.
        for cbor_data, contract in self._contracts.items():
            if cbor_data in contract_bytecode:
                return contract.instruction_by_pc(pc)
        raise Exception('Contract not found.')

    def get_contract_by_initcode(self, bytecode: bytes) -> ContractSource:
        for contract in self._contracts.values():
            if contract.get_init_bytecode == bytecode:
                return contract
        raise Exception('Contract initialization code not found.')

    @staticmethod
    def get_cbor_data(contract_bytecode: bytes) -> bytes:
        # Notice, that the CBOR_DATA is not necessarily at the end of the bytecode.
        # Hence this method can return incorrect data.
        cbor_length = contract_bytecode[-2:]  # last two bytes
        cbor_length = int.from_bytes(cbor_length, byteorder='big')  # type: ignore
        cbor_data = contract_bytecode[-cbor_length - 2 : -2]  # type: ignore
        return cbor_data

    def get_source_by_id(self, source_id: int) -> Source:
        for source in self._sources.values():
            if source.id == source_id:
                return source
        raise KeyError('Source not found.')

    def get_source_by_uuid(self, source_uuid: int) -> Source | None:
        return self._sources.get(source_uuid, None)

    def get_ast_node(self, ast_node_id: int) -> AstNode | None:
        for source in self._sources.values():
            ast_node = source.ast.find_by_id(ast_node_id)
            if ast_node is not None:
                return ast_node
        return None

    def get_source_from_path(self, path: Path) -> Source | None:
        for source in self._sources.values():
            if source._name == str(path):
                return source
        return None


def to_uuid(s: str) -> int:
    # Compute the SHA-256 hash of the input string
    sha256_hash = hashlib.sha256(s.encode('utf-8')).hexdigest()
    # Convert the hexadecimal hash to an integer
    hash_int = int(sha256_hash, 16) % (2**31)
    return hash_int
