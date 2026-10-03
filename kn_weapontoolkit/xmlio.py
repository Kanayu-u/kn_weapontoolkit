"""meta(XML) の読み書き。コメントは残す。出力は UTF-8・CRLF・正しい XML 宣言。"""
from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from pathlib import Path


class MetaError(Exception):
    """meta ファイルが読めない・想定した構造でない。"""


def parse_bytes(data: bytes, source: str = '') -> ET.Element:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    try:
        parser.feed(data)
        root = parser.close()
    except ET.ParseError as e:
        raise MetaError(f'{source}: {e}') from e
    if not isinstance(root.tag, str):
        raise MetaError(f'{source}: no root element')
    return root


def parse_file(path: Path) -> ET.Element:
    try:
        data = path.read_bytes()
    except OSError as e:
        raise MetaError(f'{path}: {e.strerror or e}') from e
    return parse_bytes(data, str(path))


def dumps(root: ET.Element) -> bytes:
    root = copy.deepcopy(root)
    for el in root.iter():
        # 中身が空白だけの要素は <Tag /> にそろえる(インデント後に空行が残らないように)
        if isinstance(el.tag, str) and len(el) == 0 and el.text is not None and not el.text.strip():
            el.text = None
    ET.indent(root, space='  ')
    body = ET.tostring(root, encoding='unicode', short_empty_elements=True)
    text = '<?xml version="1.0" encoding="UTF-8"?>\n' + body + '\n'
    return text.replace('\r\n', '\n').replace('\n', '\r\n').encode('utf-8')


def elements(parent: ET.Element, tag: str | None = None) -> list[ET.Element]:
    """直下の要素(コメントは除く)。"""
    return [c for c in parent if isinstance(c.tag, str) and (tag is None or c.tag == tag)]


def text_of(el: ET.Element | None) -> str:
    return (el.text or '').strip() if el is not None else ''


def set_child_text(parent: ET.Element, tag: str, value: str) -> ET.Element:
    """直下の <tag> の文字列を書き換える。無ければ末尾に作る。"""
    el = parent.find(tag)
    if el is None:
        el = ET.SubElement(parent, tag)
    el.text = value
    return el
