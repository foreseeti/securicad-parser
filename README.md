# Parser
A parser is called through an exposed method
```python
def parse(data: list[SubParserOutput], metadata: dict[str, Any]) -> dict[str, Any]:
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
When packaging a parser for securiCAD Enterprise, `setup.cfg` must include information about sub parsers. It may also include a display name. You must also specify what package is included in the `packages` option.
```ini
[options]
packages=
  example_parser

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
RUN rm -f requirements.txt
COPY setup.cfg .
COPY example_parser example_parser
```
Alternatively, you can add a package tarball directly and install.
```dockerfile
FROM foreseeti/securicad-parser

ADD dist/example-parser-*.tar.gz .
RUN mv example-parser-*/* ./
RUN pip install --force-reinstall --ignore-installed --upgrade --no-index --no-deps wheels/*.whl
RUN rm -rf example-parser-*/
RUN rm -rf wheels/
```

A parser image can now be built and packaged into a TAR archive
```bash
podman build --squash-all --tag example-parser .
rm -f dist/image-example-parser.tar
podman save --output dist/image-example-parser.tar example-parser
cd dist/
tar -czf langpack-example-parser.tar.gz image-example-parser.tar
```
and moved into the custom parser directory of a securiCAD Enterprise instance. The parser is available after restarting backend.

# Release
Change version number in `setup.cfg`, run `./tools/scripts/create_image.sh`, and publish with `docker push example-parser:1.0.0`.

# Running
Environment variables containing the login for RabbitMQ must be provided. Together the host and its network. Additional files may be mounted to the container at runtime.
```bash
podman run \
  --env RABBIT_USERNAME=... \
  --env RABBIT_PASSWORD=... \
  --env RABBIT_HOST=localhost \
  --network host \
  --mount type=bind,source=/home/es/bin/enterprise_suite/backend/lib/memorymodel.py,destination=/lib/memorymodel.py,readonly \
  example-parser
```
