#!/usr/bin/env python3
# SPDX-License-Identifier: EPL-2.0
"""Compare source-generated ECJ on a real Camel class and a small generic control."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

CAMEL_URL = ("https://raw.githubusercontent.com/apache/camel/"
             "8314239af1d44bba087620cf237d7cb6a6608e70/"
             "core/camel-util/src/main/java/org/apache/camel/util/ArtifactUtils.java")
CAMEL_SHA = "ba269aa023b0f0989ecb859875eca15989bcaf4933f8c23b69ddf87e2f92ddcf"
ANT_URL = "https://repo.maven.apache.org/maven2/org/apache/ant/ant/1.10.15/ant-1.10.15.jar"
ANT_SHA = "763acda4a69588c9ea8817a952851ff0c2fc4bffa1d081c2565dc407f29d5794"
WARNING = "potentiallyExpensiveTypeInference"
CONTROL = """import java.util.*;
import java.util.stream.*;
class Ordinary {
  record Item(String name, int quantity) {}
  static List<String> labels(List<Item> items) {
    return items.stream().filter(item -> item.quantity() > 0).map(Item::name).sorted().toList();
  }
  static Map<String, Integer> counts(List<Item> items) {
    return items.stream().collect(Collectors.toMap(Item::name, Item::quantity, Integer::sum));
  }
  static List<Map.Entry<String, String>> pairs() {
    return Arrays.asList(Map.entry("a","A"), Map.entry("b","B"));
  }
}
"""


def dependency(url, digest, path):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError(f"Unexpected SHA-256 for {path}")


def build_batch(repo, temp, javac, ant):
    src = repo / "org.eclipse.jdt.core.compiler.batch"
    classes = temp / "classes"
    classes.mkdir()
    files = sorted((src / "src").rglob("*.java"))
    if not files:
        raise ValueError(f"No batch compiler sources found in {src}")
    args = temp / "sources.args"
    args.write_text("".join(f'"{f}"\n' for f in files))
    subprocess.run([javac, "-J-XX:ActiveProcessorCount=3", "-J-Xmx1g",
                    "-source", "17", "-target", "17", "-Xlint:-options", "-nowarn",
                    "-proc:none", "-g:none", "-encoding", "UTF-8", "-cp", ant,
                    "-d", classes, "@" + str(args)], check=True)
    jar = temp / "batch.jar"
    with zipfile.ZipFile(jar, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write(src / "META-INF/MANIFEST.MF", "META-INF/MANIFEST.MF")
        for f in sorted(classes.rglob("*.class")):
            z.write(f, f.relative_to(classes))
        for f in sorted((src / "src").rglob("*")):
            if f.is_file() and f.suffix not in (".java", ".md", ".html"):
                z.write(f, f.relative_to(src / "src"))
        for f in sorted((src / "META-INF/services").rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(src))
    return jar


def cpu_seconds():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def compile_once(java, jar, filename, source, warning, timeout):
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        f = temp / (filename + ".java")
        f.write_text(source)
        out = temp / "out"
        out.mkdir()
        flags = ["-17", "-proc:none", "-g:none", "-warn:none"]
        if warning:
            flags.append("-warn:+" + WARNING)
        before = cpu_seconds()
        start = time.monotonic()
        r = subprocess.run([java, "-XX:ActiveProcessorCount=2", "-XX:+UseSerialGC",
                            "-Xmx512m", "-jar", jar, *flags, "-d", out, f],
                           text=True, capture_output=True, timeout=timeout)
        wall = time.monotonic() - start
        cpu = cpu_seconds() - before
        if r.returncode:
            raise RuntimeError(r.stdout + r.stderr)
        hashes = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(out.rglob("*.class"))}
        if not hashes:
            raise RuntimeError("Compiler returned without generating classes")
        return {"cpu_seconds": round(cpu, 3), "wall_seconds": round(wall, 3),
                "class_sha256": hashes, "messages": r.stdout + r.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--repo", type=Path, help="JDT Core source worktree to build")
    inputs.add_argument("--ecj-jar", type=Path, help="Use an already built batch jar")
    parser.add_argument("--jdk", type=Path, default=os.environ.get("JAVA_HOME") or None,
                        help="JDK 25 home (defaults to JAVA_HOME or executables on PATH)")
    parser.add_argument("--camel-source", type=Path, help="Cached, byte-exact Apache source file")
    parser.add_argument("--ant-jar", type=Path, help="Cached ant-1.10.15.jar")
    parser.add_argument("--warning", action="store_true", help="Enable and assert the proposed warning")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=90, help="Per-compiler-process seconds")
    args = parser.parse_args()
    if args.repetitions < 1 or args.timeout < 1:
        parser.error("The repetition count and timeout must be positive")
    java = args.jdk / "bin/java" if args.jdk else shutil.which("java")
    javac = args.jdk / "bin/javac" if args.jdk else shutil.which("javac")
    if not java or (args.repo and not javac):
        parser.error("Supply a JDK 25 installation with --jdk")
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        camel = args.camel_source or temp / "ArtifactUtils.java"
        dependency(CAMEL_URL, CAMEL_SHA, camel)
        if args.repo:
            ant = args.ant_jar or temp / "ant.jar"
            dependency(ANT_URL, ANT_SHA, ant)
            jar = build_batch(args.repo.resolve(), temp, javac, ant.resolve())
        else:
            jar = args.ecj_jar.resolve()
        actual = camel.read_text()
        inferred = actual.replace("Map.<String, String> entry(", "Map.entry(")
        outer = inferred.replace("Map.ofEntries(", "Map.<String, String>ofEntries(")
        outer = outer.replace("LANGUAGES = Map.<String, String>ofEntries(", "LANGUAGES = Map.ofEntries(")
        assert actual.count("Map.<String, String> entry(") == 563
        assert outer.count("Map.<String, String>ofEntries(") == 3
        cases = [("ordinary", "Ordinary", CONTROL), ("implicit", "ArtifactUtils", inferred),
                 ("outer3", "ArtifactUtils", outer), ("inner563", "ArtifactUtils", actual)]
        expected = None
        for index in range(args.repetitions):
            for name, cls, source in cases[::1 if index % 2 == 0 else -1]:
                result = compile_once(java, jar, cls, source, args.warning, args.timeout)
                print(json.dumps(dict(result, variant=name, repetition=index + 1)), flush=True)
                if cls == "ArtifactUtils":
                    expected = expected or result["class_sha256"]
                    if expected != result["class_sha256"]:
                        raise ValueError(f"Classfile mismatch for {name}")
                if args.warning:
                    count = result["messages"].count(". WARNING in ")
                    if count != (3 if name == "implicit" else 0):
                        raise ValueError(f"Unexpected warning count for {name}: {count}")


if __name__ == "__main__":
    main()
