# Parser
A parser is called through an exposed method
```python
def parse(data: list[SubParserOutput], metadata: dict[str, Any]) -> dict[str, Any]):
    ...
```
where `SubParserOutput` is a named tuple
```python
class SubParserOutput(NamedTuple):
    sub_parser: str # sub parser name
    data: Any       # sub parser output
```
where `data` is output from sub parser module method
```python
def parse(data: bytes, metadata: dict[str, Any]) -> Any:
    ...
```
securiCAD Enterprise will automatically run sub parsers, collect their output and pass it to the parser module.

# Packaging for securiCAD Enterprise
When packaging a parser for securiCAD Enterprise, `setup.cfg` must include information about sub parsers. It may also include a display name.
```ini
[enterprise_suite]
display_name = Example parser

[enterprise_suite.sub_parsers]
example-env-parser = example_parser.env_parser
example-vul-parser = example_parser.vul_parser
```

The `Dockerfile` should copy `setup.cfg` and the required files. As well as install every dependency.
```dockerfile
FROM foreseeti/securicad-parser

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY setup.cfg .
COPY example_parser example_parser
```

A parser image can now be built and packaged into a TAR archive
```bash
docker build --tag example-parser .
docker save example-parser | gzip > example_parser.tar.gz
```
and moved into the custom parser directory of a securiCAD Enterprise instance. The parser is available after restarting backend.

# Release
Change version number in `setup.cfg`, run `./tools/scripts/create_image.sh`, and publish with `docker push example-parser:1.0.0`.