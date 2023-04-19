# Copyright Enrico Zini
# Copied from https://www.enricozini.org/blog/2020/python/checking-sphinx-code-blocks/
# Extract code blocks from sphinx

from docutils.nodes import literal_block, Text
import json

found = []


def find_code(app, doctree, fromdocname):
    for node in doctree.traverse(literal_block):
        lang = node.attributes.get("language", "default")

        for subnode in node.traverse(Text):
            found.append({
                "src": fromdocname,
                "lang": lang,
                "code": subnode,
                "source": node.source,
                "line": node.line,
            })


def output(app, exception):
    if exception is not None:
        return

    dest = app.config.test_code_output
    if dest is None:
        return

    with open(dest, "wt") as fd:
        json.dump(found, fd)


def setup(app):
    app.add_config_value('test_code_output', None, '')

    app.connect('doctree-resolved', find_code)
    app.connect('build-finished', output)

    return {
        "version": '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
