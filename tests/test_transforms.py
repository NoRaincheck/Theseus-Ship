from theseus_ship.grammar import load_grammar
from theseus_ship.parser import parse_source
from theseus_ship.transforms import (
    apply_delete,
    apply_transform,
    apply_unwrap,
    generate_candidates,
    result_error_count,
)
from theseus_ship.tree import NodeInfo, TransformCandidate, TransformKind


class TestApplyDelete:
    def test_delete_statement(self) -> None:
        source = b"x = 1\ny = 2\n"
        node = NodeInfo("assignment", 0, 5, 3, False, ("identifier", "integer"))
        result = apply_delete(source, node)
        assert result == b"\ny = 2\n"

    def test_delete_middle(self) -> None:
        source = b"a\nb\nc\n"
        node = NodeInfo("expression_statement", 2, 4, 1, False, ())
        result = apply_delete(source, node)
        assert result == b"a\nc\n"


class TestApplyUnwrap:
    def test_unwrap_parens(self) -> None:
        source = b"(x + 1)\n"
        target = NodeInfo(
            "parenthesized_expression", 0, 7, 5, False, ("binary_expression",)
        )
        child = NodeInfo("binary_expression", 1, 6, 4, False, ())
        result = apply_unwrap(source, target, child)
        assert result == b"x + 1\n"


class TestApplyTransform:
    def test_valid_delete(self) -> None:
        grammar = load_grammar("python")
        source = b"def foo(): pass\nx = 1\n"
        result = parse_source(source, grammar)

        pass_node = next(
            n for n in result.all_nodes if n.kind == "pass_statement"
        )
        candidate = TransformCandidate(
            target=pass_node, kind=TransformKind.DELETE
        )
        root = result.root_node

        new = apply_transform(source, candidate, grammar, root_node=root)
        assert new is not None
        new_source, new_result = new
        assert b"pass" not in new_source

    def test_delete_root_rejected(self) -> None:
        grammar = load_grammar("python")
        source = b"pass\n"
        result = parse_source(source, grammar)
        root = result.root_node

        candidate = TransformCandidate(
            target=root, kind=TransformKind.DELETE
        )
        new = apply_transform(source, candidate, grammar, root_node=root)
        assert new is None


class TestGenerateCandidates:
    def test_generates_delete_candidates(self) -> None:
        grammar = load_grammar("python")
        source = b"def foo(): pass\n"
        result = parse_source(source, grammar)
        candidates = generate_candidates(result, grammar)

        delete_candidates = [c for c in candidates if c.kind == TransformKind.DELETE]
        assert len(delete_candidates) > 0

    def test_no_root_delete(self) -> None:
        grammar = load_grammar("python")
        source = b"pass\n"
        result = parse_source(source, grammar)
        candidates = generate_candidates(result, grammar)

        root_deletes = [
            c
            for c in candidates
            if c.kind == TransformKind.DELETE
            and c.target.byte_start == result.root_node.byte_start
            and c.target.byte_end == result.root_node.byte_end
        ]
        assert len(root_deletes) == 0

    def test_largest_first_ordering(self) -> None:
        grammar = load_grammar("python")
        source = b"def foo(): pass\nx = 1\n"
        result = parse_source(source, grammar)
        candidates = generate_candidates(result, grammar)

        token_counts = [c.target.token_count for c in candidates]
        assert token_counts == sorted(token_counts, reverse=True)


class TestResultErrorCount:
    def test_no_errors(self) -> None:
        grammar = load_grammar("python")
        source = b"x = 1\n"
        assert result_error_count(source, grammar) == 0

    def test_with_errors(self) -> None:
        grammar = load_grammar("python")
        source = b"x = (1 + 2\n"
        assert result_error_count(source, grammar) > 0
