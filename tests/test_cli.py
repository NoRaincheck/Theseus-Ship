import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from theseus_ship.cli import parse_args, parse_duration, _run


class TestParseDuration:
    def test_seconds(self) -> None:
        assert parse_duration("30s") == 30.0

    def test_minutes(self) -> None:
        assert parse_duration("5m") == 300.0

    def test_hours(self) -> None:
        assert parse_duration("1h") == 3600.0

    def test_invalid(self) -> None:
        with pytest.raises(argparse.ArgumentTypeError, match="Invalid duration"):
            parse_duration("abc")


class TestParseArgs:
    def test_all_flags(self) -> None:
        args = parse_args(
            ["test.py", "--test", "echo ok", "--lang", "python",
             "-o", "out.py", "--max-time", "30m", "--max-tests", "100",
             "-j", "4", "-v", "-q"]
        )
        assert args.input == "test.py"
        assert args.test == "echo ok"
        assert args.lang == "python"
        assert args.output == "out.py"
        assert args.max_time == 1800.0
        assert args.max_tests == 100
        assert args.jobs == 4
        assert args.verbose is True
        assert args.quiet is True

    def test_defaults(self) -> None:
        args = parse_args(["test.py", "--test", "echo ok"])
        assert args.input == "test.py"
        assert args.test == "echo ok"
        assert args.lang is None
        assert args.output is None
        assert args.max_time is None
        assert args.max_tests is None
        assert args.jobs == 1
        assert args.verbose is False
        assert args.quiet is False

    def test_missing_test(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["test.py"])


class TestRun:
    def test_file_not_found(self) -> None:
        args = parse_args(["nonexistent.py", "--test", "true"])
        assert _run(args) == 1

    def test_reduce_python(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("def unused(): pass\ndef used(): return 42\nprint(used())\n")
            input_path = f.name

        output_path = input_path + ".reduced"
        try:
            args = parse_args(
                [input_path, "--test", "true", "-o", output_path, "-q"]
            )
            assert _run(args) == 0
            output = Path(output_path).read_bytes()
            assert len(output) <= len(Path(input_path).read_bytes())
        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_reduce_with_stats(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write("x = 1\ny = 2\n")
            input_path = f.name

        try:
            args = parse_args([input_path, "--test", "true", "-q"])
            assert _run(args) == 0
        finally:
            Path(input_path).unlink(missing_ok=True)


class TestCLIEntryPoint:
    def test_help_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "theseus_ship", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "theseus-ship" in result.stdout
