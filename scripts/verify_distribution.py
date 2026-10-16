"""Install a built wheel outside the checkout and exercise the public surface."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def verify(wheel: Path) -> None:
    wheel = wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="promptatlas wheel smoke ") as directory:
        root = Path(directory)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        scripts = environment / ("Scripts" if os.name == "nt" else "bin")
        python = scripts / ("python.exe" if os.name == "nt" else "python")
        cli = scripts / ("promptatlas.exe" if os.name == "nt" else "promptatlas")
        env = {**os.environ, "PYTHONUTF8": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
        env.pop("PYTHONPATH", None)

        def run(*command: str, input_text: str | None = None) -> str:
            completed = subprocess.run(
                list(command),
                cwd=root,
                env=env,
                input=input_text,
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )
            if completed.returncode:
                raise RuntimeError(
                    f"Command failed: {command}\n{completed.stdout}\n{completed.stderr}"
                )
            return completed.stdout

        run(str(python), "-m", "pip", "install", "--no-deps", str(wheel))
        report = json.loads(
            run(
                str(python),
                "-I",
                "-c",
                """
import json
import promptatlas
from promptatlas import AtlasStore, generate_prompt, lint_prompt, parse_prompt
assert len(AtlasStore()) >= 10
assert 'Never' in generate_prompt('a customer support agent')
assert not lint_prompt('You are a reviewer.\\nNever invent evidence.')
spec = parse_prompt('You are a reviewer.\\nNever invent evidence.')
assert spec.to_dict() == parse_prompt(spec.raw).to_dict()
print(json.dumps({'module': promptatlas.__file__, 'version': promptatlas.__version__, 'components': len(AtlasStore())}))
""",
            )
        )
        assert environment in Path(report["module"]).parents, report
        assert report["version"] in run(str(cli), "--version")
        assert json.loads(run(str(cli), "validate", "--require-source", "--json"))["ok"]
        parsed = json.loads(run(str(cli), "parse", "-", "--json", input_text="You are a reviewer."))
        assert parsed["stats"] == {"role": 1}
        results = json.loads(run(str(cli), "search", "--kind", "guardrail", "--json"))
        assert results["total"] >= 2
        output = root / "eval with spaces.json"
        run(str(cli), "eval", "a support agent", "--out", str(output), "--provider", "echo")
        config = json.loads(output.read_text(encoding="utf-8"))
        assert json.loads(config["prompts"][0])[0]["role"] == "system"
        print(json.dumps({"wheel": wheel.name, "ok": True, **report}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    verify(parser.parse_args().wheel)
